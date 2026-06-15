<?php
date_default_timezone_set('Europe/Berlin');

$host = 'localhost';
$dbname = 'stimmungsbarometer';
$user = 'sia_web';
$pass = 'Iuu3#z1404';

$pdo = new PDO(
    "mysql:host=$host;dbname=$dbname;charset=utf8mb4",
    $user,
    $pass,
    [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]
);

$pdo->exec("SET time_zone = '+02:00'");
