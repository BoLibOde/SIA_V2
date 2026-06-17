<?php
require_once 'db.php';

header('Content-Type: application/json; charset=utf-8');

function respond_json(int $statusCode, array $payload): void
{
    http_response_code($statusCode);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

function normalize_mood_value(string $mood): string
{
    $normalized = strtolower(trim($mood));
    $map = [
        'positiv' => 'positiv',
        'positive' => 'positiv',
        'gut' => 'positiv',
        'good' => 'positiv',
        'neutral' => 'neutral',
        'negativ' => 'negativ',
        'negative' => 'negativ',
        'bad' => 'negativ',
        'schlecht' => 'negativ',
    ];

    return $map[$normalized] ?? '';
}

function derive_mood_from_counts(array $counts): string
{
    $good = max(0, (int)($counts['good'] ?? 0));
    $neutral = max(0, (int)($counts['neutral'] ?? 0));
    $bad = max(0, (int)($counts['bad'] ?? 0));

    $moods = [
        'positiv' => $good,
        'neutral' => $neutral,
        'negativ' => $bad,
    ];

    $maxValue = max($moods);
    if ($maxValue <= 0) {
        return 'neutral';
    }

    $topMoods = array_keys($moods, $maxValue, true);
    if (count($topMoods) !== 1) {
        return 'neutral';
    }

    return $topMoods[0];
}

function normalize_upload_type(array $payload): string
{
    $type = strtolower(trim((string)($payload['upload_type'] ?? '')));
    if ($type === 'sensor_hourly') {
        return 'sensor_hourly';
    }

    if ($type === 'mood_live') {
        return 'mood_live';
    }

    if (isset($payload['period_start']) || isset($payload['period_end'])) {
        return 'sensor_hourly';
    }

    return 'mood_live';
}

function extract_sensor_values(array $payload): array
{
    $co2 = $payload['co2'] ?? null;
    $humidity = $payload['humidity'] ?? null;
    $temperature = $payload['temperature'] ?? null;

    if (isset($payload['sensor_avg']) && is_array($payload['sensor_avg'])) {
        if ($co2 === null) {
            $co2 = $payload['sensor_avg']['co2_ppm'] ?? null;
        }
        if ($humidity === null) {
            $humidity = $payload['sensor_avg']['humidity_pct'] ?? null;
        }
        if ($temperature === null) {
            $temperature = $payload['sensor_avg']['temperature_c'] ?? null;
        }
    }

    if (!is_numeric($co2) || !is_numeric($humidity) || !is_numeric($temperature)) {
        respond_json(400, ['error' => 'Required sensor fields: co2, humidity, temperature.']);
    }

    $co2 = (int)$co2;
    $humidity = (float)$humidity;
    $temperature = (float)$temperature;

    if ($co2 <= 0) {
        respond_json(400, ['error' => 'co2 must be greater than 0.']);
    }

    return [
        'co2' => $co2,
        'humidity' => $humidity,
        'temperature' => $temperature,
    ];
}

function parse_timestamp(string $value, string $fieldName): string
{
    $timestamp = strtotime(trim($value));
    if ($timestamp === false) {
        respond_json(400, ['error' => "Invalid {$fieldName} timestamp."]);
    }

    return date('Y-m-d H:i:s', $timestamp);
}

function resolve_location_id(PDO $pdo, array $payload, string $referenceTimestamp): int
{
    $locationId = (int)($payload['location_id'] ?? 0);
    if ($locationId > 0) {
        return $locationId;
    }

    $stmt = $pdo->prepare("
        SELECT location_id
        FROM device_location_history
        WHERE valid_from <= :reference_timestamp
        ORDER BY valid_from DESC
        LIMIT 1
    ");
    $stmt->execute([':reference_timestamp' => $referenceTimestamp]);
    $locationHistory = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$locationHistory) {
        respond_json(422, ['error' => 'No device location configured for this timestamp.']);
    }

    return (int)$locationHistory['location_id'];
}

function is_duplicate_key_exception(PDOException $exception): bool
{
    return ($exception->errorInfo[1] ?? null) === 1062;
}

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    respond_json(200, [
        'status' => 'ok',
        'service' => 'php-device-ingest',
    ]);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: GET, POST');
    respond_json(405, ['error' => 'Only GET and POST are supported.']);
}

$body = file_get_contents('php://input');
if ($body === false || trim($body) === '') {
    respond_json(400, ['error' => 'Empty request body.']);
}

$payload = json_decode($body, true);
if (!is_array($payload)) {
    respond_json(400, ['error' => 'Invalid JSON payload.']);
}

$expectedToken = trim((string)($appConfig['device_ingest_token'] ?? ''));
if ($expectedToken !== '') {
    $providedToken = trim((string)($_SERVER['HTTP_X_DEVICE_TOKEN'] ?? ($payload['token'] ?? '')));
    if ($providedToken === '' || !hash_equals($expectedToken, $providedToken)) {
        respond_json(401, ['error' => 'Invalid device token.']);
    }
}

$uploadType = normalize_upload_type($payload);
$sensorValues = extract_sensor_values($payload);

try {
    if ($uploadType === 'sensor_hourly') {
        $periodStartInput = trim((string)($payload['period_start'] ?? ''));
        $periodEndInput = trim((string)($payload['period_end'] ?? ''));
        if ($periodStartInput === '' || $periodEndInput === '') {
            respond_json(400, ['error' => 'Required fields for sensor_hourly: period_start, period_end, sensor_avg/co2/humidity/temperature.']);
        }

        $periodStart = parse_timestamp($periodStartInput, 'period_start');
        $periodEnd = parse_timestamp($periodEndInput, 'period_end');
        if (strtotime($periodEnd) <= strtotime($periodStart)) {
            respond_json(400, ['error' => 'period_end must be later than period_start.']);
        }

        $locationId = resolve_location_id($pdo, $payload, $periodEnd);
        $deviceId = trim((string)($payload['device_id'] ?? ''));
        $sampleCount = max(0, (int)($payload['sample_count'] ?? 0));

        $stmt = $pdo->prepare("
            INSERT INTO sensor_hourly_aggregates (
                location_id,
                device_id,
                period_start,
                period_end,
                co2,
                humidity,
                temperature,
                sample_count
            )
            VALUES (
                :location_id,
                :device_id,
                :period_start,
                :period_end,
                :co2,
                :humidity,
                :temperature,
                :sample_count
            )
        ");
        $stmt->execute([
            ':location_id' => $locationId,
            ':device_id' => $deviceId,
            ':period_start' => $periodStart,
            ':period_end' => $periodEnd,
            ':co2' => $sensorValues['co2'],
            ':humidity' => $sensorValues['humidity'],
            ':temperature' => $sensorValues['temperature'],
            ':sample_count' => $sampleCount,
        ]);

        respond_json(201, [
            'status' => 'stored_sensor_hourly',
            'aggregate_id' => (int)$pdo->lastInsertId(),
            'location_id' => $locationId,
            'period_start' => $periodStart,
            'period_end' => $periodEnd,
        ]);
    }

    $mood = normalize_mood_value((string)($payload['mood'] ?? ''));
    if ($mood === '' && isset($payload['mood_counts']) && is_array($payload['mood_counts'])) {
        $mood = derive_mood_from_counts($payload['mood_counts']);
    }

    $createdAtInput = trim((string)($payload['created_at'] ?? ''));
    if ($mood === '' || $createdAtInput === '') {
        respond_json(400, ['error' => 'Required fields for mood_live: mood/mood_counts, created_at, co2, humidity, temperature.']);
    }

    $createdAt = parse_timestamp($createdAtInput, 'created_at');
    $locationId = resolve_location_id($pdo, $payload, $createdAt);

    $stmt = $pdo->prepare("
        INSERT INTO measurements (location_id, mood, co2, humidity, temperature, created_at)
        VALUES (:location_id, :mood, :co2, :humidity, :temperature, :created_at)
    ");
    $stmt->execute([
        ':location_id' => $locationId,
        ':mood' => $mood,
        ':co2' => $sensorValues['co2'],
        ':humidity' => $sensorValues['humidity'],
        ':temperature' => $sensorValues['temperature'],
        ':created_at' => $createdAt,
    ]);

    respond_json(201, [
        'status' => 'stored_mood_event',
        'measurement_id' => (int)$pdo->lastInsertId(),
        'location_id' => $locationId,
        'created_at' => $createdAt,
    ]);
} catch (PDOException $exception) {
    if ($uploadType === 'sensor_hourly' && is_duplicate_key_exception($exception)) {
        respond_json(409, ['status' => 'duplicate_sensor_hourly']);
    }

    error_log('device_ingest.php database error: ' . $exception->getMessage());
    respond_json(500, ['error' => 'Database error while storing upload.']);
}
