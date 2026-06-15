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

$stmt = $pdo->query("SELECT id, name, beschreibung, aktiv, created_at FROM locations ORDER BY id DESC");
$locations = $stmt->fetchAll(PDO::FETCH_ASSOC);
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Admin</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 30px; background: #f7f7f7; }
        .box { max-width: 1000px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        form { margin-top: 20px; }
        input[type="text"], textarea { width: 100%; padding: 10px; margin-bottom: 12px; box-sizing: border-box; }
        button { padding: 10px 16px; cursor: pointer; }
        .toplinks a { margin-right: 12px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>Admin-Bereich</h1>
        <p>Hallo <?= htmlspecialchars($_SESSION['username']) ?>, du bist als Admin eingeloggt.</p>

        <div class="toplinks">
            <a href="dashboard.php">Zum Dashboard</a>
            <a href="logout.php">Logout</a>
			<a href="add_measurement.php">Messwert hinzufügen</a>
        </div>

        <h2>Neuen Ort hinzufügen</h2>
        <form method="post" action="add_location.php">
            <label>Name</label>
            <input type="text" name="name" required>

            <label>Beschreibung</label>
            <textarea name="beschreibung" rows="4"></textarea>

            <label>
                <input type="checkbox" name="aktiv" checked> Aktiv
            </label>
            <br><br>

            <button type="submit">Ort speichern</button>
        </form>

        <h2>Vorhandene Orte</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Beschreibung</th>
                    <th>Aktiv</th>
                    <th>Aktion</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($locations as $location): ?>
                    <tr>
                        <td><?= (int)$location['id'] ?></td>
                        <td><?= htmlspecialchars($location['name']) ?></td>
                        <td><?= htmlspecialchars($location['beschreibung']) ?></td>
                        <td><?= (int)$location['aktiv'] === 1 ? 'Ja' : 'Nein' ?></td>
                       <td>
    <a href="edit_location.php?id=<?= (int)$location['id'] ?>">Bearbeiten</a>
    |
    <a href="delete_location.php?id=<?= (int)$location['id'] ?>" onclick="return confirm('Diesen Ort wirklich löschen?')">Löschen</a>
						</td>
                    </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</body>
</html>