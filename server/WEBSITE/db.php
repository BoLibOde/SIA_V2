db.php<?php
date_default_timezone_set('Europe/Berlin');

$defaults = [
    'host' => 'localhost',
    'dbname' => 'stimmungsbarometer',
    'user' => 'sia_web',
    'pass' => '',
    'timezone' => '+02:00',
];

$configFile = __DIR__ . '/db.local.php';
if (file_exists($configFile)) {
    $localConfig = require $configFile;
    if (is_array($localConfig)) {
        $defaults = array_merge($defaults, $localConfig);
    }
}

$pdo = new PDO(
    sprintf(
        'mysql:host=%s;dbname=%s;charset=utf8mb4',
        $defaults['host'],
        $defaults['dbname']
    ),
    $defaults['user'],
    $defaults['pass'],
    [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    ]
);

$pdo->exec("SET time_zone = '" . $defaults['timezone'] . "'");
