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

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name = trim($_POST['name'] ?? '');
    $beschreibung = trim($_POST['beschreibung'] ?? '');
    $aktiv = isset($_POST['aktiv']) ? 1 : 0;

    if ($name !== '') {
        $stmt = $pdo->prepare("INSERT INTO locations (name, beschreibung, aktiv) VALUES (:name, :beschreibung, :aktiv)");
        $stmt->execute([
            ':name' => $name,
            ':beschreibung' => $beschreibung,
            ':aktiv' => $aktiv
        ]);
    }
}

header('Location: admin.php');
exit;