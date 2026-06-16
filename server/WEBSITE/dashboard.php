<?php
session_start();
require_once 'db.php';
require_once 'dashboard_data_service.php';

if (!isset($_SESSION['user_id'])) {
    header('Location: login.php');
    exit;
}

$stmt = $pdo->query("SELECT id, name, beschreibung FROM locations WHERE aktiv = 1 ORDER BY name ASC");
$locations = $stmt->fetchAll(PDO::FETCH_ASSOC);

$selectedLocationId = isset($_GET['location_id']) ? (int)$_GET['location_id'] : 0;
if ($selectedLocationId <= 0 && !empty($locations)) {
    $selectedLocationId = (int)$locations[0]['id'];
}

$selectedRange = dashboard_normalize_range($_GET['range'] ?? 'tag');

$selectedLocation = null;
foreach ($locations as $location) {
    if ((int)$location['id'] === $selectedLocationId) {
        $selectedLocation = $location;
        break;
    }
}

$dashboardData = dashboard_fetch_data($pdo, $selectedLocationId, $selectedRange);
$moodData = $dashboardData['moodData'];
$temperatureData = $dashboardData['temperatureData'];
$currentCo2 = $dashboardData['summary']['currentCo2'];
$currentHumidity = $dashboardData['summary']['currentHumidity'];
$averageTemperature = $dashboardData['summary']['averageTemperature'];
$co2BarWidth = $dashboardData['summary']['co2BarWidth'];
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stimmungsbarometer</title>
    <link rel="stylesheet" href="common/css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>

<div class="top-bar">
    <div>
        <h1>Stimmungsbarometer bei ebmpapst</h1>
        <p style="margin-top:8px; color:#666;">
            Hallo <?= htmlspecialchars($_SESSION['username']) ?>
        </p>
    </div>

    <button class="logout-button" type="button" onclick="window.location.href='logout.php'">
        Logout
    </button>
</div>

<form method="get" style="margin-bottom:25px;">
    <label for="location_id" style="display:block; margin-bottom:8px; font-weight:700;">Ort auswählen</label>
    <select name="location_id" id="location_id" onchange="this.form.submit()" style="width:100%; max-width:420px; padding:12px; border-radius:12px; border:1px solid #ccc; font-size:16px;">
        <?php foreach ($locations as $location): ?>
            <option value="<?= (int)$location['id'] ?>" <?= (int)$location['id'] === $selectedLocationId ? 'selected' : '' ?>>
                <?= htmlspecialchars($location['name']) ?>
            </option>
        <?php endforeach; ?>
    </select>

    <input type="hidden" name="range" value="<?= htmlspecialchars($selectedRange) ?>">
</form>

<div class="time-selector" aria-label="Zeitraum auswählen">
    <button class="time-box <?= $selectedRange === 'tag' ? 'active' : '' ?>" data-range="tag" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=tag'">Tag</button>
    <button class="time-box <?= $selectedRange === 'woche' ? 'active' : '' ?>" data-range="woche" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=woche'">Woche</button>
    <button class="time-box <?= $selectedRange === 'monat' ? 'active' : '' ?>" data-range="monat" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=monat'">Monat</button>
    <button class="time-box <?= $selectedRange === 'jahr' ? 'active' : '' ?>" data-range="jahr" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=jahr'">Jahr</button>
    <button class="time-box <?= $selectedRange === 'gesamt' ? 'active' : '' ?>" data-range="gesamt" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=gesamt'">Gesamt</button>
</div>

<div class="dashboard">

    <div class="module">
        <h2>Stimmung der Mitarbeiter</h2>

        <div class="chart-wrapper">
            <canvas id="moodChart" aria-label="Diagramm zur Stimmung der Mitarbeiter" role="img"></canvas>
        </div>

        <div class="mood-summary">
            <div class="mood-row">
                <span class="mood-info"><span class="mood-dot positive"></span>Positiv</span>
                <span class="mood-number" id="mood-positive-value"><?= (int)$moodData['values'][0] ?></span>
            </div>

            <div class="mood-row">
                <span class="mood-info"><span class="mood-dot neutral"></span>Neutral</span>
                <span class="mood-number" id="mood-neutral-value"><?= (int)$moodData['values'][1] ?></span>
            </div>

            <div class="mood-row">
                <span class="mood-info"><span class="mood-dot negative"></span>Negativ</span>
                <span class="mood-number" id="mood-negative-value"><?= (int)$moodData['values'][2] ?></span>
            </div>
        </div>
    </div>

    <div class="module">
        <h2>CO2 Daten</h2>
        <div class="data-value" id="co2-value"><?= (int)$currentCo2 ?> ppm</div>
        <div class="small-text">Durchschnitt im gewählten Zeitraum</div>

        <div class="progress-container" aria-hidden="true">
            <div class="progress-bar" id="co2-progress-bar" style="width:<?= $co2BarWidth ?>%;"></div>
        </div>

        <div class="section-space">
            <h2>Luftfeuchtigkeit</h2>
            <div class="data-value" id="humidity-value"><?= rtrim(rtrim(number_format($currentHumidity, 2, '.', ''), '0'), '.') ?>%</div>
            <div class="small-text">Durchschnitt im gewählten Zeitraum</div>
        </div>
    </div>

    <div class="module">
        <h2>Temperatur</h2>

        <div class="chart-wrapper">
            <canvas id="temperatureChart" aria-label="Diagramm zur Temperaturentwicklung" role="img"></canvas>
        </div>

        <div class="temperature-summary">
            <div class="temperature-row">
                <span class="temperature-label">Durchschnittliche Temperatur</span>
                <span class="temperature-number" id="average-temperature-value"><?= rtrim(rtrim(number_format($averageTemperature, 1, '.', ''), '0'), '.') ?>°C</span>
            </div>
        </div>
    </div>

</div>

<script>
    const moodChartData = <?= json_encode($moodData, JSON_UNESCAPED_UNICODE) ?>;
    const temperatureChartData = {
        tag: <?= json_encode($temperatureData, JSON_UNESCAPED_UNICODE) ?>,
        woche: <?= json_encode($temperatureData, JSON_UNESCAPED_UNICODE) ?>,
        monat: <?= json_encode($temperatureData, JSON_UNESCAPED_UNICODE) ?>,
        jahr: <?= json_encode($temperatureData, JSON_UNESCAPED_UNICODE) ?>,
        gesamt: <?= json_encode($temperatureData, JSON_UNESCAPED_UNICODE) ?>
    };
    const dashboardConfig = {
        locationId: <?= (int)$selectedLocationId ?>,
        range: <?= json_encode($selectedRange, JSON_UNESCAPED_UNICODE) ?>,
        refreshIntervalMs: 15000,
        dataUrl: 'dashboard_data.php'
    };
</script>
<script src="common/js/script.js?v=<?= filemtime(__DIR__ . '/common/js/script.js') ?: time() ?>"></script>
<script>
    if (typeof refreshDashboardData === 'undefined' || typeof applyDashboardData === 'undefined') {
        console.warn('Dashboard auto-refresh is not available. The loaded script.js may be stale or incomplete.');
    }
</script>
</body>
</html>