<?php
date_default_timezone_set('Europe/Berlin');

$host = 'localhost';
$dbname = 'stimmungsbarometer';
$user = 'root';
$pass = '';

$pdo = new PDO(
    "mysql:host=$host;dbname=$dbname;charset=utf8mb4",
    $user,
    $pass,
    [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]
);

$pdo->exec("SET time_zone = '+02:00'");