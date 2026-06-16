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

$stmt = $pdo->query("SELECT id, name FROM locations WHERE aktiv = 1 ORDER BY name ASC");
$locations = $stmt->fetchAll(PDO::FETCH_ASSOC);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $locationId = (int)($_POST['location_id'] ?? 0);
    $validFromInput = trim($_POST['valid_from'] ?? '');
    $note = trim($_POST['note'] ?? '');

    if ($locationId <= 0 || $validFromInput === '') {
        $error = 'Bitte Ort und Startzeitpunkt angeben.';
    } else {
        $validFrom = date('Y-m-d H:i:s', strtotime($validFromInput));

        if ($validFrom === false || $validFrom === '1970-01-01 00:00:00') {
            $error = 'Ungültiges Datum oder ungültige Uhrzeit.';
        } else {
            $stmt = $pdo->prepare("
                INSERT INTO device_location_history (location_id, valid_from, changed_by, note)
                VALUES (:location_id, :valid_from, :changed_by, :note)
            ");
            $stmt->execute([
                ':location_id' => $locationId,
                ':valid_from' => $validFrom,
                ':changed_by' => $_SESSION['user_id'],
                ':note' => $note !== '' ? $note : null
            ]);

            $success = 'Standortwechsel wurde gespeichert.';
        }
    }
}

$stmt = $pdo->query("
    SELECT dlh.id, dlh.valid_from, dlh.note, dlh.created_at, l.name AS location_name, u.username AS changed_by_name
    FROM device_location_history dlh
    INNER JOIN locations l ON l.id = dlh.location_id
    LEFT JOIN users u ON u.id = dlh.changed_by
    ORDER BY dlh.valid_from DESC
");
$history = $stmt->fetchAll(PDO::FETCH_ASSOC);

$currentLocation = null;
if (!empty($history)) {
    $currentLocation = $history[0];
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerätestandort verwalten</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f7f7f7;
            padding: 30px;
        }

        .box {
            max-width: 1000px;
            margin: 0 auto;
            background: #fff;
            padding: 24px;
            border-radius: 12px;
        }

        h1, h2 {
            margin-top: 0;
        }

        .toplinks {
            margin-bottom: 20px;
        }

        .toplinks a {
            display: inline-block;
            margin-right: 12px;
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

        .form-grid {
            display: grid;
            gap: 12px;
        }

        input[type="datetime-local"],
        input[type="text"],
        select,
        textarea {
            width: 100%;
            padding: 10px;
            box-sizing: border-box;
        }

        button {
            padding: 10px 16px;
            cursor: pointer;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: #fff;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }

        th {
            background: #f0f0f0;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Gerätestandort verwalten</h1>

        <div class="toplinks">
    <a href="dashboard.php">Dashboard</a>
    <a href="admin.php">Admin-Startseite</a>
    <a href="admin_locations.php">Orte verwalten</a>
    <a href="add_location.php">Ort anlegen</a>
    <a href="add_measurement.php">Messwerte hinzufügen</a>
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
            <h2>Aktueller Standort</h2>
            <?php if ($currentLocation): ?>
                <p><strong>Ort:</strong> <?= htmlspecialchars($currentLocation['location_name']) ?></p>
                <p><strong>Gültig ab:</strong> <?= htmlspecialchars($currentLocation['valid_from']) ?></p>
            <?php else: ?>
                <p>Es wurde noch kein Standort für das Gerät hinterlegt.</p>
            <?php endif; ?>
        </div>

        <div class="card">
            <h2>Standortwechsel eintragen</h2>
            <form method="post" class="form-grid">
                <div>
                    <label for="location_id">Neuer Ort</label>
                    <select name="location_id" id="location_id" required>
                        <option value="">Bitte wählen</option>
                        <?php foreach ($locations as $location): ?>
                            <option value="<?= (int)$location['id'] ?>">
                                <?= htmlspecialchars($location['name']) ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div>
                    <label for="valid_from">Gültig ab</label>
                    <input type="datetime-local" name="valid_from" id="valid_from" required>
                </div>

                <div>
                    <label for="note">Notiz (optional)</label>
                    <input type="text" name="note" id="note">
                </div>

                <div>
                    <button type="submit">Standortwechsel speichern</button>
                </div>
            </form>
        </div>

        <div class="card">
            <h2>Standortverlauf</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ort</th>
                        <th>Gültig ab</th>
                        <th>Geändert von</th>
                        <th>Notiz</th>
                        <th>Eingetragen am</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (!empty($history)): ?>
                        <?php foreach ($history as $entry): ?>
                            <tr>
                                <td><?= htmlspecialchars($entry['location_name']) ?></td>
                                <td><?= htmlspecialchars($entry['valid_from']) ?></td>
                                <td><?= htmlspecialchars($entry['changed_by_name'] ?? '-') ?></td>
                                <td><?= htmlspecialchars($entry['note'] ?? '-') ?></td>
                                <td><?= htmlspecialchars($entry['created_at']) ?></td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else: ?>
                        <tr>
                            <td colspan="5">Noch keine Standortwechsel vorhanden.</td>
                        </tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>