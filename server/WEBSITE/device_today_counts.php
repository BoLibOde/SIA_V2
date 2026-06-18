<?php
require_once 'db.php';

header('Content-Type: application/json; charset=utf-8');

function today_counts_respond_json(int $statusCode, array $payload): void
{
    http_response_code($statusCode);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

function today_counts_require_device_token(array $appConfig): void
{
    $expectedToken = trim((string)($appConfig['device_ingest_token'] ?? ''));
    if ($expectedToken === '') {
        return;
    }

    $providedToken = trim((string)($_SERVER['HTTP_X_DEVICE_TOKEN'] ?? ($_GET['token'] ?? '')));
    if ($providedToken === '' || !hash_equals($expectedToken, $providedToken)) {
        today_counts_respond_json(401, ['error' => 'Invalid device token.']);
    }
}

function today_counts_resolve_location_id(PDO $pdo, int $locationId, string $referenceTimestamp): int
{
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
    $row = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$row) {
        today_counts_respond_json(422, ['error' => 'No device location configured for today.']);
    }

    return (int)$row['location_id'];
}

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    header('Allow: GET');
    today_counts_respond_json(405, ['error' => 'Only GET is supported.']);
}

today_counts_require_device_token($appConfig);

$deviceId = trim((string)($_GET['device_id'] ?? ''));
$locationId = (int)($_GET['location_id'] ?? 0);
if ($deviceId === '' && $locationId <= 0) {
    today_counts_respond_json(400, ['error' => 'device_id or location_id is required.']);
}

$todayStart = new DateTime('today');
$todayEnd = (clone $todayStart)->modify('+1 day');
$resolvedLocationId = today_counts_resolve_location_id($pdo, $locationId, (new DateTime())->format('Y-m-d H:i:s'));

try {
    $stmt = $pdo->prepare("
        SELECT mood, COUNT(*) AS total
        FROM measurements
        WHERE location_id = :location_id
          AND created_at >= :start_date
          AND created_at < :end_date
        GROUP BY mood
    ");
    $stmt->execute([
        ':location_id' => $resolvedLocationId,
        ':start_date' => $todayStart->format('Y-m-d H:i:s'),
        ':end_date' => $todayEnd->format('Y-m-d H:i:s'),
    ]);
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $exception) {
    error_log('device_today_counts.php database error: ' . $exception->getMessage());
    today_counts_respond_json(500, ['error' => 'Database error while reading today counts.']);
}

$counts = [
    'good' => 0,
    'neutral' => 0,
    'bad' => 0,
];
$moodMap = [
    'positiv' => 'good',
    'neutral' => 'neutral',
    'negativ' => 'bad',
];

foreach ($rows as $row) {
    $key = $moodMap[$row['mood']] ?? null;
    if ($key !== null) {
        $counts[$key] = (int)$row['total'];
    }
}

today_counts_respond_json(200, [
    'status' => 'ok',
    'date' => $todayStart->format('Y-m-d'),
    'timezone' => (string)($appConfig['timezone'] ?? date_default_timezone_get()),
    'location_id' => $resolvedLocationId,
    'device_id' => $deviceId,
    'counts' => $counts,
    'total' => $counts['good'] + $counts['neutral'] + $counts['bad'],
]);
