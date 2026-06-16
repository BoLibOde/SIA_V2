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

$mood = normalize_mood_value((string)($payload['mood'] ?? ''));
if ($mood === '' && isset($payload['mood_counts']) && is_array($payload['mood_counts'])) {
    $mood = derive_mood_from_counts($payload['mood_counts']);
}

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

$createdAtInput = trim((string)($payload['created_at'] ?? ($payload['period_end'] ?? '')));
if ($mood === '' || !is_numeric($co2) || !is_numeric($humidity) || !is_numeric($temperature) || $createdAtInput === '') {
    respond_json(400, ['error' => 'Required fields: mood/mood_counts, co2, humidity, temperature, created_at/period_end.']);
}

$co2 = (int)$co2;
$humidity = (float)$humidity;
$temperature = (float)$temperature;
if ($co2 <= 0) {
    respond_json(400, ['error' => 'co2 must be greater than 0.']);
}

$createdAtTimestamp = strtotime($createdAtInput);
if ($createdAtTimestamp === false) {
    respond_json(400, ['error' => 'Invalid created_at or period_end timestamp.']);
}

$createdAt = date('Y-m-d H:i:s', $createdAtTimestamp);

try {
    $locationId = (int)($payload['location_id'] ?? 0);

    if ($locationId <= 0) {
        $stmt = $pdo->prepare("
            SELECT location_id
            FROM device_location_history
            WHERE valid_from <= :created_at
            ORDER BY valid_from DESC
            LIMIT 1
        ");
        $stmt->execute([':created_at' => $createdAt]);
        $locationHistory = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$locationHistory) {
            respond_json(422, ['error' => 'No device location configured for this timestamp.']);
        }

        $locationId = (int)$locationHistory['location_id'];
    }

    $stmt = $pdo->prepare("
        INSERT INTO measurements (location_id, mood, co2, humidity, temperature, created_at)
        VALUES (:location_id, :mood, :co2, :humidity, :temperature, :created_at)
    ");
    $stmt->execute([
        ':location_id' => $locationId,
        ':mood' => $mood,
        ':co2' => $co2,
        ':humidity' => $humidity,
        ':temperature' => $temperature,
        ':created_at' => $createdAt,
    ]);

    respond_json(201, [
        'status' => 'stored',
        'measurement_id' => (int)$pdo->lastInsertId(),
        'location_id' => $locationId,
        'created_at' => $createdAt,
    ]);
} catch (PDOException $exception) {
    error_log('device_ingest.php database error: ' . $exception->getMessage());
    respond_json(500, ['error' => 'Database error while storing measurement.']);
}
