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
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin-Bereich</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 30px;
            background: #f7f7f7;
        }

        .box {
            max-width: 1000px;
            margin: 0 auto;
            background: #fff;
            padding: 24px;
            border-radius: 12px;
        }

        h1, h2 {
            margin-top: 0;
        }

        .toplinks {
            margin-bottom: 24px;
        }

        .toplinks a {
            display: inline-block;
            margin-right: 12px;
            margin-bottom: 8px;
            text-decoration: none;
            color: #111;
            font-weight: bold;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-top: 20px;
        }

        .card {
            display: block;
            padding: 18px;
            border: 1px solid #ddd;
            border-radius: 10px;
            background: #fafafa;
            text-decoration: none;
            color: #111;
        }

        .card h2 {
            font-size: 20px;
            margin-bottom: 8px;
        }

        .card p {
            margin: 0;
            color: #444;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Admin-Bereich</h1>
        <p>Hallo <?= htmlspecialchars($_SESSION['username']) ?>, du bist als Admin eingeloggt.</p>

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

        <div class="grid">
            <a class="card" href="admin_locations.php">
                <h2>Orte verwalten</h2>
                <p>Vorhandene Orte anzeigen, bearbeiten und löschen.</p>
            </a>

            <a class="card" href="add_location.php">
                <h2>Ort anlegen</h2>
                <p>Einen neuen Standort für das Gerät anlegen.</p>
            </a>

            <a class="card" href="add_measurement.php">
                <h2>Messwerte hinzufügen</h2>
                <p>Neue Messwerte manuell erfassen und speichern.</p>
            </a>

            <a class="card" href="device_location.php">
                <h2>Gerätestandort</h2>
                <p>Festlegen, ab wann das Gerät an welchem Ort steht.</p>
            </a>

            <a class="card" href="admin_users.php">
                <h2>Benutzerverwaltung</h2>
                <p>Benutzer und Administratoren verwalten.</p>
            </a>

            <a class="card" href="delete_measurements.php">
                <h2>Messdaten löschen</h2>
                <p>Messdaten gefiltert nach Ort, Zeitraum und Stimmung löschen.</p>
            </a>
        </div>
    </div>
</body>
</html>