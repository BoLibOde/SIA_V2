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

$message = '';
$error = '';

function isValidRole(string $role): bool
{
    return in_array($role, ['user', 'admin'], true);
}

function isValidActiveValue($value): bool
{
    return in_array((string)$value, ['0', '1'], true);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'create_user') {
        $username = trim($_POST['username'] ?? '');
        $password = $_POST['password'] ?? '';
        $role = trim($_POST['role'] ?? 'user');
        $active = $_POST['active'] ?? '1';

        if ($username === '' || $password === '') {
            $error = 'Bitte Benutzername und Passwort eingeben.';
        } elseif (!isValidRole($role)) {
            $error = 'Ungültige Rolle.';
        } elseif (!isValidActiveValue($active)) {
            $error = 'Ungültiger Aktiv-Status.';
        } else {
            $stmt = $pdo->prepare("SELECT id FROM users WHERE username = :username LIMIT 1");
            $stmt->execute([':username' => $username]);
            $existingUser = $stmt->fetch(PDO::FETCH_ASSOC);

            if ($existingUser) {
                $error = 'Der Benutzername existiert bereits.';
            } else {
                $passwordHash = password_hash($password, PASSWORD_DEFAULT);

                $stmt = $pdo->prepare("
                    INSERT INTO users (username, password_hash, role, active)
                    VALUES (:username, :password_hash, :role, :active)
                ");
                $stmt->execute([
                    ':username' => $username,
                    ':password_hash' => $passwordHash,
                    ':role' => $role,
                    ':active' => (int)$active
                ]);

                $message = 'Benutzer wurde erfolgreich angelegt.';
            }
        }
    }

    if ($action === 'update_user') {
        $userId = (int)($_POST['user_id'] ?? 0);
        $username = trim($_POST['username'] ?? '');
        $role = trim($_POST['role'] ?? 'user');
        $active = $_POST['active'] ?? '1';
        $newPassword = $_POST['new_password'] ?? '';

        if ($userId <= 0 || $username === '') {
            $error = 'Ungültige Benutzerdaten.';
        } elseif (!isValidRole($role)) {
            $error = 'Ungültige Rolle.';
        } elseif (!isValidActiveValue($active)) {
            $error = 'Ungültiger Aktiv-Status.';
        } else {
            $stmt = $pdo->prepare("
                SELECT id
                FROM users
                WHERE username = :username AND id != :id
                LIMIT 1
            ");
            $stmt->execute([
                ':username' => $username,
                ':id' => $userId
            ]);
            $existingUser = $stmt->fetch(PDO::FETCH_ASSOC);

            if ($existingUser) {
                $error = 'Der Benutzername ist bereits vergeben.';
            } else {
                $stmt = $pdo->prepare("
                    SELECT id, role, active
                    FROM users
                    WHERE id = :id
                    LIMIT 1
                ");
                $stmt->execute([':id' => $userId]);
                $currentUser = $stmt->fetch(PDO::FETCH_ASSOC);

                if (!$currentUser) {
                    $error = 'Benutzer wurde nicht gefunden.';
                } else {
                    if ((int)$userId === (int)$_SESSION['user_id'] && $role !== 'admin') {
                        $error = 'Du kannst dir selbst die Admin-Rolle nicht entziehen.';
                    } elseif ((int)$userId === (int)$_SESSION['user_id'] && (int)$active === 0) {
                        $error = 'Du kannst deinen eigenen Benutzer nicht deaktivieren.';
                    } else {
                        if ($currentUser['role'] === 'admin' && ((string)$role !== 'admin' || (int)$active === 0)) {
                            $stmt = $pdo->query("
                                SELECT COUNT(*) AS admin_count
                                FROM users
                                WHERE role = 'admin' AND active = 1
                            ");
                            $adminCount = (int)$stmt->fetch(PDO::FETCH_ASSOC)['admin_count'];

                            if ($adminCount <= 1) {
                                $error = 'Der letzte aktive Admin kann nicht geändert oder deaktiviert werden.';
                            }
                        }

                        if ($error === '') {
                            if ($newPassword !== '') {
                                $passwordHash = password_hash($newPassword, PASSWORD_DEFAULT);

                                $stmt = $pdo->prepare("
                                    UPDATE users
                                    SET username = :username,
                                        role = :role,
                                        active = :active,
                                        password_hash = :password_hash
                                    WHERE id = :id
                                ");
                                $stmt->execute([
                                    ':username' => $username,
                                    ':role' => $role,
                                    ':active' => (int)$active,
                                    ':password_hash' => $passwordHash,
                                    ':id' => $userId
                                ]);
                            } else {
                                $stmt = $pdo->prepare("
                                    UPDATE users
                                    SET username = :username,
                                        role = :role,
                                        active = :active
                                    WHERE id = :id
                                ");
                                $stmt->execute([
                                    ':username' => $username,
                                    ':role' => $role,
                                    ':active' => (int)$active,
                                    ':id' => $userId
                                ]);
                            }

                            $message = 'Benutzer wurde erfolgreich aktualisiert.';
                        }
                    }
                }
            }
        }
    }

    if ($action === 'delete_user') {
        $userId = (int)($_POST['user_id'] ?? 0);

        if ($userId <= 0) {
            $error = 'Ungültige Benutzer-ID.';
        } elseif ($userId === (int)$_SESSION['user_id']) {
            $error = 'Du kannst deinen eigenen Benutzer nicht löschen.';
        } else {
            $stmt = $pdo->prepare("
                SELECT id, role, active
                FROM users
                WHERE id = :id
                LIMIT 1
            ");
            $stmt->execute([':id' => $userId]);
            $userToDelete = $stmt->fetch(PDO::FETCH_ASSOC);

            if (!$userToDelete) {
                $error = 'Benutzer wurde nicht gefunden.';
            } else {
                if ($userToDelete['role'] === 'admin' && (int)$userToDelete['active'] === 1) {
                    $stmt = $pdo->query("
                        SELECT COUNT(*) AS admin_count
                        FROM users
                        WHERE role = 'admin' AND active = 1
                    ");
                    $adminCount = (int)$stmt->fetch(PDO::FETCH_ASSOC)['admin_count'];

                    if ($adminCount <= 1) {
                        $error = 'Der letzte aktive Admin kann nicht gelöscht werden.';
                    }
                }

                if ($error === '') {
                    $stmt = $pdo->prepare("DELETE FROM users WHERE id = :id");
                    $stmt->execute([':id' => $userId]);

                    $message = 'Benutzer wurde erfolgreich gelöscht.';
                }
            }
        }
    }
}

$stmt = $pdo->query("
    SELECT id, username, role, active
    FROM users
    ORDER BY username ASC
");
$users = $stmt->fetchAll(PDO::FETCH_ASSOC);
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Benutzerverwaltung</title>
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
            margin-bottom: 16px;
            background: #fafafa;
        }

        .form-grid {
            display: grid;
            gap: 12px;
        }

        input[type="text"],
        input[type="password"],
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
        }

        .user-list {
            margin-top: 30px;
        }

        .small-note {
            color: #666;
            font-size: 14px;
            margin-top: 6px;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Benutzerverwaltung</h1>

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

        <?php if ($message !== ''): ?>
            <div class="message"><?= htmlspecialchars($message) ?></div>
        <?php endif; ?>

        <?php if ($error !== ''): ?>
            <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <h2>Neuen Benutzer anlegen</h2>
        <div class="card">
            <form method="post" class="form-grid">
                <input type="hidden" name="action" value="create_user">

                <div>
                    <label for="username">Benutzername</label>
                    <input type="text" id="username" name="username" required>
                </div>

                <div>
                    <label for="password">Passwort</label>
                    <input type="password" id="password" name="password" required>
                </div>

                <div>
                    <label for="role">Rolle</label>
                    <select id="role" name="role">
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>

                <div>
                    <label for="active">Status</label>
                    <select id="active" name="active">
                        <option value="1">Aktiv</option>
                        <option value="0">Inaktiv</option>
                    </select>
                </div>

                <div>
                    <button type="submit">Benutzer anlegen</button>
                </div>
            </form>
        </div>

        <div class="user-list">
            <h2>Vorhandene Benutzer bearbeiten</h2>

            <?php foreach ($users as $user): ?>
                <div class="card">
                    <form method="post" class="form-grid">
                        <input type="hidden" name="action" value="update_user">
                        <input type="hidden" name="user_id" value="<?= (int)$user['id'] ?>">

                        <div>
                            <label>Benutzername</label>
                            <input type="text" name="username" value="<?= htmlspecialchars($user['username']) ?>" required>
                        </div>

                        <div>
                            <label>Rolle</label>
                            <select name="role">
                                <option value="user" <?= $user['role'] === 'user' ? 'selected' : '' ?>>User</option>
                                <option value="admin" <?= $user['role'] === 'admin' ? 'selected' : '' ?>>Admin</option>
                            </select>
                        </div>

                        <div>
                            <label>Status</label>
                            <select name="active">
                                <option value="1" <?= (int)$user['active'] === 1 ? 'selected' : '' ?>>Aktiv</option>
                                <option value="0" <?= (int)$user['active'] === 0 ? 'selected' : '' ?>>Inaktiv</option>
                            </select>
                        </div>

                        <div>
                            <label>Neues Passwort</label>
                            <input type="password" name="new_password">
                            <div class="small-note">Leer lassen, wenn das Passwort unverändert bleiben soll.</div>
                        </div>

                        <div>
                            <button type="submit">Änderungen speichern</button>
                        </div>
                    </form>

                    <?php if ((int)$user['id'] !== (int)$_SESSION['user_id']): ?>
                        <form method="post" onsubmit="return confirm('Diesen Benutzer wirklich löschen?');" style="margin-top: 10px;">
                            <input type="hidden" name="action" value="delete_user">
                            <input type="hidden" name="user_id" value="<?= (int)$user['id'] ?>">
                            <button type="submit" class="danger-button">Benutzer löschen</button>
                        </form>
                    <?php endif; ?>
                </div>
            <?php endforeach; ?>
        </div>
    </div>
</body>
</html>