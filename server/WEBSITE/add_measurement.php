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

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mood = trim($_POST['mood'] ?? '');
    $co2 = (int)($_POST['co2'] ?? 0);
    $humidity = (float)($_POST['humidity'] ?? 0);
    $temperature = (float)($_POST['temperature'] ?? 0);
    $createdAtInput = trim($_POST['created_at'] ?? '');

    $allowedMoods = ['positiv', 'neutral', 'negativ'];

    if (!in_array($mood, $allowedMoods, true) || $co2 <= 0 || $createdAtInput === '') {
        $error = 'Bitte alle Felder korrekt ausfüllen.';
    } else {
        $createdAtTimestamp = strtotime($createdAtInput);

        if ($createdAtTimestamp === false) {
            $error = 'Ungültiges Datum oder ungültige Uhrzeit.';
        } else {
            $createdAt = date('Y-m-d H:i:s', $createdAtTimestamp);

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
                $error = 'Für diesen Zeitpunkt ist kein Gerätestandort hinterlegt.';
            } else {
                $locationId = (int)$locationHistory['location_id'];

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
                    ':created_at' => $createdAt
                ]);

                $success = 'Messwert wurde gespeichert.';
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Messwerte hinzufügen</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f7f7f7;
            padding: 30px;
        }

        .box {
            max-width: 700px;
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

        input, select, button {
            width: 100%;
            padding: 10px;
            box-sizing: border-box;
        }

        button {
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Messwerte hinzufügen</h1>

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
                <label for="mood">Stimmung</label>
                <select name="mood" id="mood" required>
                    <option value="">Bitte wählen</option>
                    <option value="positiv">Positiv</option>
                    <option value="neutral">Neutral</option>
                    <option value="negativ">Negativ</option>
                </select>
            </div>

            <div>
                <label for="co2">CO₂</label>
                <input type="number" name="co2" id="co2" required>
            </div>

            <div>
                <label for="humidity">Luftfeuchtigkeit</label>
                <input type="number" step="0.1" name="humidity" id="humidity" required>
            </div>

            <div>
                <label for="temperature">Temperatur</label>
                <input type="number" step="0.1" name="temperature" id="temperature" required>
            </div>

            <div>
                <label for="created_at">Zeitpunkt der Messung</label>
                <input type="datetime-local" name="created_at" id="created_at" required>
            </div>

            <div>
                <button type="submit">Messwert speichern</button>
            </div>
        </form>
    </div>
</body>
</html>