<?php
session_start();
require_once 'db.php';

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

$selectedRange = $_GET['range'] ?? 'tag';
$allowedRanges = ['tag', 'woche', 'monat', 'jahr', 'gesamt'];
if (!in_array($selectedRange, $allowedRanges, true)) {
    $selectedRange = 'tag';
}

$selectedLocation = null;
foreach ($locations as $location) {
    if ((int)$location['id'] === $selectedLocationId) {
        $selectedLocation = $location;
        break;
    }
}

date_default_timezone_set('Europe/Berlin');

function getRangeBounds(string $range): array
{
    $now = new DateTime('now');

    switch ($range) {
        case 'tag':
            $start = new DateTime('today');
            $end = (clone $start)->modify('+1 day');
            break;

        case 'woche':
            $start = new DateTime('monday this week');
            $start->setTime(0, 0, 0);
            $end = (clone $start)->modify('+1 week');
            break;

        case 'monat':
            $start = new DateTime('first day of this month');
            $start->setTime(0, 0, 0);
            $end = (clone $start)->modify('+1 month');
            break;

        case 'jahr':
            $start = new DateTime(date('Y-01-01 00:00:00'));
            $end = new DateTime((date('Y') + 1) . '-01-01 00:00:00');
            break;

        case 'gesamt':
        default:
            $start = null;
            $end = null;
            break;
    }

    return [$start, $end];
}

function buildRangeSql(?DateTime $start, ?DateTime $end, array &$params): string
{
    $sql = '';
    if ($start !== null) {
        $sql .= " AND created_at >= :start_date";
        $params[':start_date'] = $start->format('Y-m-d H:i:s');
    }
    if ($end !== null) {
        $sql .= " AND created_at < :end_date";
        $params[':end_date'] = $end->format('Y-m-d H:i:s');
    }
    return $sql;
}

function getGroupLabelSql(string $range): string
{
    switch ($range) {
        case 'tag':
            return "DATE_FORMAT(created_at, '%H:00')";
        case 'woche':
        case 'monat':
            return "DATE_FORMAT(created_at, '%d.%m')";
        case 'jahr':
        case 'gesamt':
        default:
            return "DATE_FORMAT(created_at, '%m.%Y')";
    }
}

$moodData = [
    'labels' => ['Positiv', 'Neutral', 'Negativ'],
    'values' => [0, 0, 0]
];

$temperatureData = [
    'labels' => ['Keine Daten'],
    'values' => [0]
];

$currentCo2 = 0;
$currentHumidity = 0;
$averageTemperature = 0;
$co2BarWidth = 0;

[$rangeStart, $rangeEnd] = getRangeBounds($selectedRange);

if ($selectedLocationId > 0) {
    $baseParams = [':location_id' => $selectedLocationId];
    $rangeSql = buildRangeSql($rangeStart, $rangeEnd, $baseParams);

    $statsSql = "
        SELECT
            AVG(co2) AS avg_co2,
            AVG(humidity) AS avg_humidity,
            AVG(temperature) AS avg_temperature
        FROM measurements
        WHERE location_id = :location_id
        {$rangeSql}
    ";
    $stmt = $pdo->prepare($statsSql);
    $stmt->execute($baseParams);
    $stats = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($stats) {
        $currentCo2 = $stats['avg_co2'] !== null ? (int)round($stats['avg_co2']) : 0;
        $currentHumidity = $stats['avg_humidity'] !== null ? (float)$stats['avg_humidity'] : 0;
        $averageTemperature = $stats['avg_temperature'] !== null ? (float)$stats['avg_temperature'] : 0;
        $co2BarWidth = min(100, max(0, ($currentCo2 / 2000) * 100));
    }

    $moodParams = [':location_id' => $selectedLocationId];
    $moodRangeSql = buildRangeSql($rangeStart, $rangeEnd, $moodParams);

    $stmt = $pdo->prepare("
        SELECT mood, COUNT(*) AS total
        FROM measurements
        WHERE location_id = :location_id
        {$moodRangeSql}
        GROUP BY mood
    ");
    $stmt->execute($moodParams);
    $moodRows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $moodMap = [
        'positiv' => 0,
        'neutral' => 1,
        'negativ' => 2
    ];

    foreach ($moodRows as $row) {
        if (isset($moodMap[$row['mood']])) {
            $moodData['values'][$moodMap[$row['mood']]] = (int)$row['total'];
        }
    }

    $chartParams = [':location_id' => $selectedLocationId];
    $chartRangeSql = buildRangeSql($rangeStart, $rangeEnd, $chartParams);
    $groupLabelSql = getGroupLabelSql($selectedRange);

    $chartSql = "
        SELECT
            {$groupLabelSql} AS label,
            ROUND(AVG(temperature), 1) AS avg_temperature
        FROM measurements
        WHERE location_id = :location_id
        {$chartRangeSql}
        GROUP BY label
        ORDER BY MIN(created_at) ASC
    ";

    $stmt = $pdo->prepare($chartSql);
    $stmt->execute($chartParams);
    $chartRows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    if (!empty($chartRows)) {
        $temperatureData = ['labels' => [], 'values' => []];
        foreach ($chartRows as $row) {
            $temperatureData['labels'][] = $row['label'];
            $temperatureData['values'][] = (float)$row['avg_temperature'];
        }
    }
}
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
    <button class="time-box <?= $selectedRange === 'tag' ? 'active' : '' ?>" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=tag'">Tag</button>
    <button class="time-box <?= $selectedRange === 'woche' ? 'active' : '' ?>" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=woche'">Woche</button>
    <button class="time-box <?= $selectedRange === 'monat' ? 'active' : '' ?>" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=monat'">Monat</button>
    <button class="time-box <?= $selectedRange === 'jahr' ? 'active' : '' ?>" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=jahr'">Jahr</button>
    <button class="time-box <?= $selectedRange === 'gesamt' ? 'active' : '' ?>" type="button" onclick="window.location.href='?location_id=<?= $selectedLocationId ?>&range=gesamt'">Gesamt</button>
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
                <span class="mood-number"><?= (int)$moodData['values'][0] ?></span>
            </div>

            <div class="mood-row">
                <span class="mood-info"><span class="mood-dot neutral"></span>Neutral</span>
                <span class="mood-number"><?= (int)$moodData['values'][1] ?></span>
            </div>

            <div class="mood-row">
                <span class="mood-info"><span class="mood-dot negative"></span>Negativ</span>
                <span class="mood-number"><?= (int)$moodData['values'][2] ?></span>
            </div>
        </div>
    </div>

    <div class="module">
        <h2>CO2 Daten</h2>
        <div class="data-value"><?= (int)$currentCo2 ?> ppm</div>
        <div class="small-text">Durchschnitt im gewählten Zeitraum</div>

        <div class="progress-container" aria-hidden="true">
            <div class="progress-bar" style="width:<?= $co2BarWidth ?>%;"></div>
        </div>

        <div class="section-space">
            <h2>Luftfeuchtigkeit</h2>
            <div class="data-value"><?= rtrim(rtrim(number_format($currentHumidity, 2, '.', ''), '0'), '.') ?>%</div>
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
                <span class="temperature-number"><?= rtrim(rtrim(number_format($averageTemperature, 1, '.', ''), '0'), '.') ?>°C</span>
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
</script>
<script src="common/js/script.js"></script>
</body>
</html>