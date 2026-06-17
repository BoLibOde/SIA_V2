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

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name = trim($_POST['name'] ?? '');
    $beschreibung = trim($_POST['beschreibung'] ?? '');
    $aktiv = isset($_POST['aktiv']) ? 1 : 0;

    if ($name === '') {
        $error = 'Bitte einen Ortsnamen eingeben.';
    } else {
        $stmt = $pdo->prepare("SELECT id FROM locations WHERE name = :name LIMIT 1");
        $stmt->execute([':name' => $name]);
        $existingLocation = $stmt->fetch(PDO::FETCH_ASSOC);

        if ($existingLocation) {
            $error = 'Ein Ort mit diesem Namen existiert bereits.';
        } else {
            $stmt = $pdo->prepare("
                INSERT INTO locations (name, beschreibung, aktiv, created_at)
                VALUES (:name, :beschreibung, :aktiv, NOW())
            ");
            $stmt->execute([
                ':name' => $name,
                ':beschreibung' => $beschreibung,
                ':aktiv' => $aktiv
            ]);

            $success = 'Ort wurde erfolgreich angelegt.';
        }
    }
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ort anlegen</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 30px;
            background: #f7f7f7;
        }

        .box {
            max-width: 800px;
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
    </style>
</head>
<body>
    <div class="box">
        <h1>Ort anlegen</h1>

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

        <form method="post" class="form-grid">
            <div>
                <label for="name">Name</label>
                <input type="text" id="name" name="name" required>
            </div>

            <div>
                <label for="beschreibung">Beschreibung</label>
                <textarea id="beschreibung" name="beschreibung"></textarea>
            </div>

            <div>
                <label>
                    <input type="checkbox" name="aktiv" value="1" checked>
                    Ort aktiv
                </label>
            </div>

            <div>
                <button type="submit">Ort speichern</button>
            </div>
        </form>
    </div>
</body>
</html>