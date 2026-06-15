<?php
$host = 'localhost';
$dbname = 'stimmungsbarometer';
$user = 'root';
$pass = '';

$adminUsername = 'admin';
$adminPassword = 'admin1234';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $passwordHash = password_hash($adminPassword, PASSWORD_DEFAULT);

    $stmt = $pdo->prepare("INSERT INTO users (username, password_hash, role, active) VALUES (:username, :password_hash, :role, :active)");
    $stmt->execute([
        ':username' => $adminUsername,
        ':password_hash' => $passwordHash,
        ':role' => 'admin',
        ':active' => 1
    ]);

    echo "Admin-Benutzer wurde erfolgreich angelegt.";
} catch (PDOException $e) {
    echo "Fehler: " . $e->getMessage();
}
?>