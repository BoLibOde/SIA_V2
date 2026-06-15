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

$id = (int)($_GET['id'] ?? 0);

if ($id <= 0) {
    header('Location: admin.php');
    exit;
}

$stmt = $pdo->prepare("SELECT id, name, beschreibung, aktiv FROM locations WHERE id = :id LIMIT 1");
$stmt->execute([':id' => $id]);
$location = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$location) {
    header('Location: admin.php');
    exit;
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Ort bearbeiten</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 30px; background: #f7f7f7; }
        .box { max-width: 700px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 10px; }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            margin-bottom: 12px;
            box-sizing: border-box;
        }
        button { padding: 10px 16px; cursor: pointer; }
        a { text-decoration: none; }
    </style>
</head>
<body>
    <div class="box">
        <h1>Ort bearbeiten</h1>

        <form method="post" action="update_location.php">
            <input type="hidden" name="id" value="<?= (int)$location['id'] ?>">

            <label>Name</label>
            <input type="text" name="name" required value="<?= htmlspecialchars($location['name']) ?>">

            <label>Beschreibung</label>
            <textarea name="beschreibung" rows="5"><?= htmlspecialchars($location['beschreibung']) ?></textarea>

            <label>
                <input type="checkbox" name="aktiv" <?= (int)$location['aktiv'] === 1 ? 'checked' : '' ?>>
                Aktiv
            </label>

            <br><br>

            <button type="submit">Änderungen speichern</button>
            <a href="admin.php">Abbrechen</a>
        </form>
    </div>
</body>
</html>