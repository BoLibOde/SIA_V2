<?php
session_start();
require_once 'db.php';
require_once 'dashboard_data_service.php';

header('Content-Type: application/json; charset=utf-8');

if (!isset($_SESSION['user_id'])) {
    http_response_code(401);
    echo json_encode(['error' => 'Unauthorized'], JSON_UNESCAPED_UNICODE);
    exit;
}

$selectedLocationId = isset($_GET['location_id']) ? (int)$_GET['location_id'] : 0;
$selectedRange = dashboard_normalize_range($_GET['range'] ?? 'tag');

$payload = dashboard_fetch_data($pdo, $selectedLocationId, $selectedRange);
echo json_encode($payload, JSON_UNESCAPED_UNICODE);
