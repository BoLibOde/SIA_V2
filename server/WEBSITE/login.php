<?php
session_start();
require_once 'db.php';

if (isset($_SESSION['user_id'])) {
    if ($_SESSION['role'] === 'admin') {
        header('Location: admin.php');
        exit;
    } else {
        header('Location: dashboard.php');
        exit;
    }
}

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    $stmt = $pdo->prepare("SELECT id, username, password_hash, role, active FROM users WHERE username = :username LIMIT 1");
    $stmt->execute([':username' => $username]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($user && (int)$user['active'] === 1 && password_verify($password, $user['password_hash'])) {
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['username'] = $user['username'];
        $_SESSION['role'] = $user['role'];

        if ($user['role'] === 'admin') {
            header('Location: admin.php');
            exit;
        } else {
            header('Location: dashboard.php');
            exit;
        }
    } else {
        $error = 'Benutzername oder Passwort ist falsch.';
    }
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Login</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; background: #f4f4f4; }
        .box { max-width: 400px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 10px; }
        input { width: 100%; padding: 10px; margin: 8px 0 16px; box-sizing: border-box; }
        button { padding: 10px 16px; cursor: pointer; }
        .error { color: #b00020; margin-bottom: 12px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>Login</h1>
        <?php if ($error): ?>
            <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <form method="post">
            <label>Benutzername</label>
            <input type="text" name="username" required>

            <label>Passwort</label>
            <input type="password" name="password" required>

            <button type="submit">Anmelden</button>
        </form>
    </div>
</body>
</html>