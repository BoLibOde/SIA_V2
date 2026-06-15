<?php
session_start();
require_once 'db.php';

if (!isset($_SESSION['user_id'])) {
    header('Location: login.php');
    exit;
}

if ($_SESSION['role'] !== 'admin') {
    header('Location: dashboard.php');
    exit;
}

$stmt = $pdo->query("SELECT id, name FROM locations WHERE aktiv = 1 ORDER BY name ASC");
$locations = $stmt->fetchAll(PDO::FETCH_ASSOC);

$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $locationId = (int)($_POST['location_id'] ?? 0);
    $mood = trim($_POST['mood'] ?? '');
    $co2 = (int)($_POST['co2'] ?? 0);
    $humidity = (float)($_POST['humidity'] ?? 0);
    $temperature = (float)($_POST['temperature'] ?? 0);
    $createdAtInput = trim($_POST['created_at'] ?? '');

    $allowedMoods = ['positiv', 'neutral', 'negativ'];

    if ($locationId <= 0 || !in_array($mood, $allowedMoods, true) || $co2 <= 0) {
        $error = 'Bitte alle Felder korrekt ausfüllen.';
    } else {
        if ($createdAtInput !== '') {
            $createdAt = date('Y-m-d H:i:s', strtotime($createdAtInput));
        } else {
            $createdAt = date('Y-m-d H:i:s');
        }

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
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Messwert hinzufügen</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 30px;
            background: #f7f7f7;
        }
        .box {
            max-width: 700px;
            margin: 0 auto;
            background: #fff;
            padding: 24px;
            border-radius: 10px;
        }
        select, input {
            width: 100%;
            padding: 10px;
            margin-bottom: 12px;
            box-sizing: border-box;
        }
        button {
            padding: 10px 16px;
            cursor: pointer;
        }
        .error {
            color: #b00020;
            margin-bottom: 12px;
        }
        .success {
            color: green;
            margin-bottom: 12px;
        }
        .hint {
            font-size: 14px;
            color: #666;
            margin-top: -6px;
            margin-bottom: 12px;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Messwert hinzufügen</h1>

        <?php if ($error): ?>
            <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <?php if ($success): ?>
            <div class="success"><?= htmlspecialchars($success) ?></div>
        <?php endif; ?>

        <form method="post">
            <label>Ort</label>
            <select name="location_id" required>
                <option value="">Bitte wählen</option>
                <?php foreach ($locations as $location): ?>
                    <option value="<?= (int)$location['id'] ?>">
                        <?= htmlspecialchars($location['name']) ?>
                    </option>
                <?php endforeach; ?>
            </select>

            <label>Stimmung</label>
            <select name="mood" required>
                <option value="">Bitte wählen</option>
                <option value="positiv">Positiv</option>
                <option value="neutral">Neutral</option>
                <option value="negativ">Negativ</option>
            </select>

            <label>CO2 (ppm)</label>
            <input type="number" name="co2" required>

            <label>Luftfeuchtigkeit (%)</label>
            <input type="number" name="humidity" step="0.01" required>

            <label>Temperatur (°C)</label>
            <input type="number" name="temperature" step="0.01" required>

            <label>Messdatum und Uhrzeit</label>
            <input type="datetime-local" name="created_at">
            <div class="hint">Leer lassen = aktuelles Datum und aktuelle Uhrzeit</div>

            <button type="submit">Messwert speichern</button>
        </form>

        <p style="margin-top:16px;"><a href="admin.php">Zurück zum Admin-Bereich</a></p>
    </div>
</body>
</html>