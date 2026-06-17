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

$error = '';
$success = '';
$editLocation = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'update_location') {
        $locationId = (int)($_POST['location_id'] ?? 0);
        $name = trim($_POST['name'] ?? '');
        $beschreibung = trim($_POST['beschreibung'] ?? '');
        $aktiv = isset($_POST['aktiv']) ? 1 : 0;

        if ($locationId <= 0 || $name === '') {
            $error = 'Ungültige Ortsdaten.';
        } else {
            $stmt = $pdo->prepare("
                SELECT id
                FROM locations
                WHERE name = :name AND id != :id
                LIMIT 1
            ");
            $stmt->execute([
                ':name' => $name,
                ':id' => $locationId
            ]);
            $existingLocation = $stmt->fetch(PDO::FETCH_ASSOC);

            if ($existingLocation) {
                $error = 'Ein anderer Ort mit diesem Namen existiert bereits.';
            } else {
                $stmt = $pdo->prepare("
                    UPDATE locations
                    SET name = :name,
                        beschreibung = :beschreibung,
                        aktiv = :aktiv
                    WHERE id = :id
                ");
                $stmt->execute([
                    ':name' => $name,
                    ':beschreibung' => $beschreibung,
                    ':aktiv' => $aktiv,
                    ':id' => $locationId
                ]);

                $success = 'Ort wurde erfolgreich aktualisiert.';
            }
        }
    }

    if ($action === 'delete_location') {
        $locationId = (int)($_POST['location_id'] ?? 0);

        if ($locationId <= 0) {
            $error = 'Ungültige Orts-ID.';
        } else {
            $stmt = $pdo->prepare("
                SELECT COUNT(*) AS total
                FROM measurements
                WHERE location_id = :location_id
            ");
            $stmt->execute([':location_id' => $locationId]);
            $measurementCount = (int)$stmt->fetch(PDO::FETCH_ASSOC)['total'];

            if ($measurementCount > 0) {
                $error = 'Dieser Ort kann nicht gelöscht werden, da bereits Messdaten vorhanden sind.';
            } else {
                $stmt = $pdo->prepare("DELETE FROM locations WHERE id = :id");
                $stmt->execute([':id' => $locationId]);

                $success = 'Ort wurde erfolgreich gelöscht.';
            }
        }
    }
}

if (isset($_GET['edit_id'])) {
    $editId = (int)($_GET['edit_id']);

    if ($editId > 0) {
        $stmt = $pdo->prepare("
            SELECT id, name, beschreibung, aktiv
            FROM locations
            WHERE id = :id
            LIMIT 1
        ");
        $stmt->execute([':id' => $editId]);
        $editLocation = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$editLocation) {
            $error = 'Ort wurde nicht gefunden.';
        }
    }
}

$stmt = $pdo->query("
    SELECT id, name, beschreibung, aktiv, created_at
    FROM locations
    ORDER BY id DESC
");
$locations = $stmt->fetchAll(PDO::FETCH_ASSOC);
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orte verwalten</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 30px;
            background: #f7f7f7;
        }

        .box {
            max-width: 1100px;
            margin: 0 auto;
            background: #fff;
            padding: 24px;
            border-radius: 12px;
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

        .form-grid {
            display: grid;
            gap: 12px;
        }

        input[type="text"],
        textarea {
            width: 100%;
            padding: 10px;
            box-sizing: border-box;
        }

        textarea {
            min-height: 100px;
            resize: vertical;
        }

        button {
            padding: 10px 16px;
            cursor: pointer;
        }

        .danger-button {
            background: #b00020;
            color: #fff;
            border: none;
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
            vertical-align: top;
        }

        th {
            background: #f0f0f0;
        }

        .action-links a,
        .action-links form {
            display: inline-block;
            margin-right: 8px;
        }

        .action-links form {
            margin: 0;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Orte verwalten</h1>

        <div class="toplinks">
            <a href="dashboard.php">Dashboard</a>
            <a href="admin.php">Admin-Startseite</a>
            <a href="admin_locations.php">Orte verwalten</a>
            <a href="add_location.php">Ort anlegen</a>
            <a href="add_measurement.php">Messwerte hinzufügen</a>
            <a href="device_location.php">Gerätestandort</a>
            <a href="admin_users.php">Benutzerverwaltung</a>
            <a href="delete_measurements.php">Messdaten löschen</a>
            <a href="logout.php">Logout</a>
        </div>

        <?php if ($success !== ''): ?>
            <div class="message"><?= htmlspecialchars($success) ?></div>
        <?php endif; ?>

        <?php if ($error !== ''): ?>
            <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <?php if ($editLocation): ?>
            <div class="card">
                <h2>Ort bearbeiten</h2>
                <form method="post" class="form-grid">
                    <input type="hidden" name="action" value="update_location">
                    <input type="hidden" name="location_id" value="<?= (int)$editLocation['id'] ?>">

                    <div>
                        <label for="edit_name">Name</label>
                        <input type="text" id="edit_name" name="name" value="<?= htmlspecialchars($editLocation['name']) ?>" required>
                    </div>

                    <div>
                        <label for="edit_beschreibung">Beschreibung</label>
                        <textarea id="edit_beschreibung" name="beschreibung"><?= htmlspecialchars($editLocation['beschreibung']) ?></textarea>
                    </div>

                    <div>
                        <label>
                            <input type="checkbox" name="aktiv" value="1" <?= (int)$editLocation['aktiv'] === 1 ? 'checked' : '' ?>>
                            Ort aktiv
                        </label>
                    </div>

                    <div>
                        <button type="submit">Änderungen speichern</button>
                        <a href="admin_locations.php">Bearbeitung abbrechen</a>
                    </div>
                </form>
            </div>
        <?php endif; ?>

        <div class="card">
            <h2>Vorhandene Orte</h2>

            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Beschreibung</th>
                        <th>Aktiv</th>
                        <th>Erstellt am</th>
                        <th>Aktion</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (!empty($locations)): ?>
                        <?php foreach ($locations as $location): ?>
                            <tr>
                                <td><?= (int)$location['id'] ?></td>
                                <td><?= htmlspecialchars($location['name']) ?></td>
                                <td><?= nl2br(htmlspecialchars($location['beschreibung'])) ?></td>
                                <td><?= (int)$location['aktiv'] === 1 ? 'Ja' : 'Nein' ?></td>
                                <td><?= htmlspecialchars($location['created_at']) ?></td>
                                <td class="action-links">
                                    <a href="admin_locations.php?edit_id=<?= (int)$location['id'] ?>">Bearbeiten</a>

                                    <form method="post" onsubmit="return confirm('Diesen Ort wirklich löschen?');">
                                        <input type="hidden" name="action" value="delete_location">
                                        <input type="hidden" name="location_id" value="<?= (int)$location['id'] ?>">
                                        <button type="submit" class="danger-button">Löschen</button>
                                    </form>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else: ?>
                        <tr>
                            <td colspan="6">Noch keine Orte vorhanden.</td>
                        </tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>