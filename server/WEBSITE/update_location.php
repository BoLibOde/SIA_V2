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
    $id = (int)($_POST['id'] ?? 0);
    $name = trim($_POST['name'] ?? '');
    $beschreibung = trim($_POST['beschreibung'] ?? '');
    $aktiv = isset($_POST['aktiv']) ? 1 : 0;

    if ($id > 0 && $name !== '') {
        $stmt = $pdo->prepare("
            UPDATE locations
            SET name = :name,
                beschreibung = :beschreibung,
                aktiv = :aktiv
            WHERE id = :id
        ");

        $stmt->execute([
            ':name' => $name,
            ':beschreibung' => $beschreibung,
            ':aktiv' => $aktiv,
            ':id' => $id
        ]);
    }
}

header('Location: admin.php');
exit;