<?php
require_once 'db.php';

$username = 'user1';
$password = 'user1234';
$role = 'user';
$active = 1;

$passwordHash = password_hash($password, PASSWORD_DEFAULT);

$stmt = $pdo->prepare("SELECT id FROM users WHERE username = :username LIMIT 1");
$stmt->execute([':username' => $username]);
$existingUser = $stmt->fetch(PDO::FETCH_ASSOC);

if ($existingUser) {
    die("Benutzer existiert bereits.");
}

$stmt = $pdo->prepare("
    INSERT INTO users (username, password_hash, role, active)
    VALUES (:username, :password_hash, :role, :active)
");

$stmt->execute([
    ':username' => $username,
    ':password_hash' => $passwordHash,
    ':role' => $role,
    ':active' => $active
]);

echo "Normaler Benutzer wurde angelegt.";