<?php
session_start();
require_once 'db.php';

if (!isset($_SESSION['user_id'])) {
    header('Location: login.php');
    exit;
}

if (($_SESSION['role'] ?? '') !== 'admin') {
    header('Location: dashboard.php');
    exit;
}

date_default_timezone_set('Europe/Berlin');

$error = '';
$success = '';
$previewCount = null;
$previewDone = false;

$allowedMoods = ['positiv', 'neutral', 'negativ'];

$stmt = $pdo->query("SELECT id, name FROM locations ORDER BY name ASC");
$locations = $stmt->fetchAll(PDO::FETCH_ASSOC);

function buildWhereClause(array $params): array
{
    $conditions = [];
    $bindings = [];

    if (!empty($params['location_id'])) {
        $conditions[] = 'location_id = :location_id';
        $bindings[':location_id'] = (int)$params['location_id'];
    }

    if (!empty($params['date_from'])) {
        $conditions[] = 'created_at >= :date_from';
        $bindings[':date_from'] = $params['date_from'];
    }

    if (!empty($params['date_to'])) {
        $conditions[] = 'created_at <= :date_to';
        $bindings[':date_to'] = $params['date_to'];
    }

    if (!empty($params['mood'])) {
        $conditions[] = 'mood = :mood';
        $bindings[':mood'] = $params['mood'];
    }

    $where = $conditions ? 'WHERE ' . implode(' AND ', $conditions) : '';

    return [$where, $bindings];
}

$locationId = (int)($_POST['location_id'] ?? $_GET['location_id'] ?? 0);
$dateFrom   = trim($_POST['date_from']   ?? $_GET['date_from']   ?? '');
$dateTo     = trim($_POST['date_to']     ?? $_GET['date_to']     ?? '');
$mood       = trim($_POST['mood']        ?? $_GET['mood']        ?? '');

if ($mood !== '' && !in_array($mood, $allowedMoods, true)) {
    $mood = '';
}

$dateFromTs = $dateFrom !== '' ? strtotime($dateFrom) : false;
$dateToTs   = $dateTo   !== '' ? strtotime($dateTo . ' 23:59:59') : false;

if ($dateFrom !== '' && $dateFromTs === false) {
    $error = 'Ungültiges Datum im Feld „Von".';
    $dateFrom = '';
}

if ($dateTo !== '' && $dateToTs === false) {
    $error = 'Ungültiges Datum im Feld „Bis".';
    $dateTo = '';
}

$filterParams = [
    'location_id' => $locationId > 0 ? $locationId : null,
    'date_from'   => $dateFromTs !== false ? date('Y-m-d H:i:s', $dateFromTs) : null,
    'date_to'     => $dateToTs   !== false ? date('Y-m-d H:i:s', $dateToTs)   : null,
    'mood'        => $mood !== '' ? $mood : null,
];

$previewToken = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'preview') {
        [$where, $bindings] = buildWhereClause($filterParams);

        if ($where === '') {
            $error = 'Bitte mindestens einen Filter setzen, um keine versehentliche Komplettlöschung auszulösen.';
        } else {
            $stmt = $pdo->prepare("SELECT COUNT(*) AS total FROM measurements $where");
            $stmt->execute($bindings);
            $previewCount = (int)$stmt->fetch(PDO::FETCH_ASSOC)['total'];
            $previewDone  = true;

            // Store a one-time token so the delete step can only be reached after a preview.
            $previewToken = bin2hex(random_bytes(16));
            $_SESSION['delete_preview'] = [
                'token'   => $previewToken,
                'filters' => $filterParams,
                'count'   => $previewCount,
            ];
        }
    } elseif ($action === 'delete') {
        $confirmed    = ($_POST['confirm'] ?? '') === 'yes';
        $submittedTok = $_POST['preview_token'] ?? '';
        $stored       = $_SESSION['delete_preview'] ?? null;

        // Enforce server-side that a valid preview was performed in this session.
        if ($stored === null || $submittedTok === '' || !hash_equals($stored['token'], $submittedTok)) {
            $error = 'Ungültige Sitzung: Bitte zuerst die Vorschau anzeigen, bevor gelöscht wird.';
        } elseif ($stored['filters'] !== $filterParams) {
            // Filter values changed between preview and delete – refuse to proceed.
            $error = 'Die Filterparameter haben sich verändert. Bitte Vorschau erneut ausführen.';
            unset($_SESSION['delete_preview']);
        } elseif (!$confirmed) {
            $error = 'Bitte bestätige das Löschen durch Aktivieren der Sicherheitscheckbox.';
        } else {
            [$where, $bindings] = buildWhereClause($filterParams);

            if ($where === '') {
                $error = 'Bitte mindestens einen Filter setzen.';
            } else {
                // One-time use: clear the preview token immediately before executing DELETE.
                unset($_SESSION['delete_preview']);

                $stmt = $pdo->prepare("DELETE FROM measurements $where");
                $stmt->execute($bindings);
                $deleted = $stmt->rowCount();
                $success = $deleted . ' Messdatensatz/-sätze wurden erfolgreich gelöscht.';

                $locationId = 0;
                $dateFrom   = '';
                $dateTo     = '';
                $mood       = '';
                $filterParams = [];
            }
        }
    }
} elseif (isset($_SESSION['delete_preview'])) {
    // Clear any stale preview token when the page is loaded via GET (e.g. direct visit or
    // browser refresh). The token is only valid for the POST round-trip it was created in.
    unset($_SESSION['delete_preview']);
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Messdaten löschen</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f7f7f7;
            padding: 30px;
        }

        .box {
            max-width: 800px;
            margin: 0 auto;
            background: #fff;
            padding: 24px;
            border-radius: 12px;
        }

        h1 {
            margin-top: 0;
        }

        .toplinks {
            margin-bottom: 20px;
        }

        .toplinks a {
            display: inline-block;
            margin-right: 12px;
            margin-bottom: 8px;
            text-decoration: none;
            color: #111;
            font-weight: bold;
        }

        .message {
            color: green;
            margin-bottom: 16px;
        }

        .error {
            color: #b00020;
            margin-bottom: 16px;
        }

        .card {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
            background: #fafafa;
        }

        .card h2 {
            margin-top: 0;
        }

        .form-grid {
            display: grid;
            gap: 12px;
        }

        label {
            display: block;
            margin-bottom: 4px;
            font-weight: bold;
        }

        input[type="date"],
        select {
            width: 100%;
            padding: 10px;
            box-sizing: border-box;
        }

        button {
            padding: 10px 16px;
            cursor: pointer;
        }

        .danger-button {
            background: #b00020;
            color: #fff;
            border: none;
            border-radius: 4px;
        }

        .preview-box {
            background: #fff8e1;
            border: 1px solid #f0c040;
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
        }

        .preview-box strong {
            font-size: 1.2em;
        }

        .confirm-check {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 12px;
        }

        .confirm-check input[type="checkbox"] {
            width: 18px;
            height: 18px;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Messdaten löschen</h1>

        <div class="toplinks">
            <a href="dashboard.php">Dashboard</a>
            <a href="admin.php">Admin-Startseite</a>
            <a href="admin_locations.php">Orte verwalten</a>
            <a href="add_location.php">Ort anlegen</a>
            <a href="add_measurement.php">Messwerte hinzufügen</a>
            <a href="delete_measurements.php">Messdaten löschen</a>
            <a href="device_location.php">Gerätestandort</a>
            <a href="admin_users.php">Benutzerverwaltung</a>
            <a href="logout.php">Logout</a>
        </div>

        <?php if ($success !== ''): ?>
            <div class="message"><?= htmlspecialchars($success) ?></div>
        <?php endif; ?>

        <?php if ($error !== ''): ?>
            <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <div class="card">
            <h2>Filter für zu löschende Messdaten</h2>
            <p>Setze mindestens einen Filter, dann klicke zuerst auf <strong>Vorschau</strong>, um die Anzahl der betroffenen Datensätze zu sehen. Das Löschen selbst erfolgt erst nach zusätzlicher Bestätigung.</p>

            <form method="post" class="form-grid" id="filter-form">
                <div>
                    <label for="location_id">Ort (optional)</label>
                    <select name="location_id" id="location_id">
                        <option value="">— Alle Orte —</option>
                        <?php foreach ($locations as $loc): ?>
                            <option value="<?= (int)$loc['id'] ?>" <?= (int)($locationId ?? 0) === (int)$loc['id'] ? 'selected' : '' ?>>
                                <?= htmlspecialchars($loc['name']) ?> (ID <?= (int)$loc['id'] ?>)
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div>
                    <label for="date_from">Zeitraum von (Datum)</label>
                    <input type="date" name="date_from" id="date_from" value="<?= htmlspecialchars($dateFrom) ?>">
                </div>

                <div>
                    <label for="date_to">Zeitraum bis (Datum)</label>
                    <input type="date" name="date_to" id="date_to" value="<?= htmlspecialchars($dateTo) ?>">
                </div>

                <div>
                    <label for="mood">Stimmung (optional)</label>
                    <select name="mood" id="mood">
                        <option value="">— Alle Stimmungen —</option>
                        <option value="positiv"  <?= $mood === 'positiv'  ? 'selected' : '' ?>>Positiv</option>
                        <option value="neutral"  <?= $mood === 'neutral'  ? 'selected' : '' ?>>Neutral</option>
                        <option value="negativ"  <?= $mood === 'negativ'  ? 'selected' : '' ?>>Negativ</option>
                    </select>
                </div>

                <div>
                    <button type="submit" name="action" value="preview">Vorschau anzeigen</button>
                </div>
            </form>

            <?php if ($previewDone): ?>
                <div class="preview-box">
                    <p>Mit den gewählten Filtern würden <strong><?= $previewCount ?> Datensatz/-sätze</strong> gelöscht.</p>

                    <?php if ($previewCount > 0): ?>
                        <form method="post" class="form-grid" onsubmit="return confirm('Wirklich <?= (int)$previewCount ?> Datensatz/-sätze unwiderruflich löschen?');">
                            <input type="hidden" name="location_id"    value="<?= (int)$locationId ?>">
                            <input type="hidden" name="date_from"      value="<?= htmlspecialchars($dateFrom) ?>">
                            <input type="hidden" name="date_to"        value="<?= htmlspecialchars($dateTo) ?>">
                            <input type="hidden" name="mood"           value="<?= htmlspecialchars($mood) ?>">
                            <input type="hidden" name="preview_token"  value="<?= htmlspecialchars($previewToken) ?>">

                            <div class="confirm-check">
                                <input type="checkbox" name="confirm" id="confirm" value="yes" required>
                                <label for="confirm" style="font-weight: normal;">Ich bestätige, dass ich diese <?= $previewCount ?> Datensatz/-sätze unwiderruflich löschen möchte.</label>
                            </div>

                            <div>
                                <button type="submit" name="action" value="delete" class="danger-button">Jetzt unwiderruflich löschen</button>
                            </div>
                        </form>
                    <?php else: ?>
                        <p>Keine Datensätze gefunden – es wird nichts gelöscht.</p>
                    <?php endif; ?>
                </div>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
