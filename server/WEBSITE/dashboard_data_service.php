<?php

function dashboard_normalize_range(string $range): string
{
    $allowedRanges = ['tag', 'woche', 'monat', 'jahr', 'gesamt'];
    return in_array($range, $allowedRanges, true) ? $range : 'tag';
}

function dashboard_get_range_bounds(string $range): array
{
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

function dashboard_build_range_sql(?DateTime $start, ?DateTime $end, array &$params, string $column = 'created_at'): string
{
    $sql = '';
    if ($start !== null) {
        $sql .= " AND {$column} >= :start_date";
        $params[':start_date'] = $start->format('Y-m-d H:i:s');
    }
    if ($end !== null) {
        $sql .= " AND {$column} < :end_date";
        $params[':end_date'] = $end->format('Y-m-d H:i:s');
    }
    return $sql;
}

function dashboard_get_group_label_sql(string $range, string $column = 'created_at'): string
{
    switch ($range) {
        case 'tag':
            return "DATE_FORMAT({$column}, '%H:00')";
        case 'woche':
        case 'monat':
            return "DATE_FORMAT({$column}, '%d.%m')";
        case 'jahr':
        case 'gesamt':
        default:
            return "DATE_FORMAT({$column}, '%m.%Y')";
    }
}

function dashboard_fetch_data(PDO $pdo, int $selectedLocationId, string $selectedRange): array
{
    $moodData = [
        'labels' => ['Positiv', 'Neutral', 'Negativ'],
        'values' => [0, 0, 0]
    ];

    $temperatureData = [
        'labels' => ['Keine Daten'],
        'values' => [0]
    ];

    $summary = [
        'currentCo2' => 0,
        'currentHumidity' => 0.0,
        'averageTemperature' => 0.0,
        'co2BarWidth' => 0.0
    ];

    if ($selectedLocationId <= 0) {
        return [
            'moodData' => $moodData,
            'temperatureData' => $temperatureData,
            'summary' => $summary
        ];
    }

    [$rangeStart, $rangeEnd] = dashboard_get_range_bounds($selectedRange);
    $baseParams = [':location_id' => $selectedLocationId];
    $rangeSql = dashboard_build_range_sql($rangeStart, $rangeEnd, $baseParams, 'period_start');

    $statsSql = "
        SELECT
            AVG(co2) AS avg_co2,
            AVG(humidity) AS avg_humidity,
            AVG(temperature) AS avg_temperature
        FROM sensor_hourly_aggregates
        WHERE location_id = :location_id
        {$rangeSql}
    ";
    $stmt = $pdo->prepare($statsSql);
    $stmt->execute($baseParams);
    $stats = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($stats) {
        $summary['currentCo2'] = $stats['avg_co2'] !== null ? (int)round($stats['avg_co2']) : 0;
        $summary['currentHumidity'] = $stats['avg_humidity'] !== null ? (float)$stats['avg_humidity'] : 0.0;
        $summary['averageTemperature'] = $stats['avg_temperature'] !== null ? (float)$stats['avg_temperature'] : 0.0;
        $summary['co2BarWidth'] = min(100, max(0, ($summary['currentCo2'] / 2000) * 100));
    }

    $moodParams = [':location_id' => $selectedLocationId];
    $moodRangeSql = dashboard_build_range_sql($rangeStart, $rangeEnd, $moodParams);

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
    $chartRangeSql = dashboard_build_range_sql($rangeStart, $rangeEnd, $chartParams, 'period_start');
    $groupLabelSql = dashboard_get_group_label_sql($selectedRange, 'period_start');

    $chartSql = "
        SELECT
            {$groupLabelSql} AS label,
            ROUND(AVG(temperature), 1) AS avg_temperature
        FROM sensor_hourly_aggregates
        WHERE location_id = :location_id
        {$chartRangeSql}
        GROUP BY label
        ORDER BY MIN(period_start) ASC
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

    return [
        'moodData' => $moodData,
        'temperatureData' => $temperatureData,
        'summary' => $summary
    ];
}
