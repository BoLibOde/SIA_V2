-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Erstellungszeit: 15. Jun 2026 um 20:14
-- Server-Version: 10.4.32-MariaDB
-- PHP-Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Datenbank: `stimmungsbarometer`
--

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `locations`
--

CREATE TABLE `locations` (
  `id` int(11) NOT NULL,
  `name` varchar(150) NOT NULL,
  `beschreibung` text DEFAULT NULL,
  `aktiv` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Daten für Tabelle `locations`
--

INSERT INTO `locations` (`id`, `name`, `beschreibung`, `aktiv`, `created_at`) VALUES
(1, 'Lehrwerkstatt', 'Am Eingang', 1, '2026-06-11 17:18:46'),
(4, 'Küche_02', 'am Waschbecken', 1, '2026-06-12 09:17:34'),
(5, 'test', 'test text', 1, '2026-06-12 09:45:09'),
(6, 'aktivTest', 'mal sehen', 0, '2026-06-12 10:18:20'),
(7, 'Zeit', 'zeit text', 1, '2026-06-12 10:28:30'),
(8, 'Moritz', '15.06 test', 1, '2026-06-15 16:40:30');

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `measurements`
--

CREATE TABLE `measurements` (
  `id` int(11) NOT NULL,
  `location_id` int(11) NOT NULL,
  `mood` enum('positiv','neutral','negativ') NOT NULL,
  `co2` int(11) NOT NULL,
  `humidity` decimal(5,2) NOT NULL,
  `temperature` decimal(5,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Daten für Tabelle `measurements`
--

INSERT INTO `measurements` (`id`, `location_id`, `mood`, `co2`, `humidity`, `temperature`, `created_at`) VALUES
(1, 5, 'positiv', 21, 22.00, 23.00, '2026-06-12 10:02:14'),
(2, 5, 'neutral', 41, 42.00, 43.00, '2026-06-12 10:02:26'),
(3, 4, 'negativ', 12, 23.00, 34.00, '2026-06-12 10:10:35'),
(4, 1, 'positiv', 1, 1.00, 1.00, '2026-06-12 10:26:21'),
(5, 1, 'positiv', 2, 3.00, 4.00, '2026-06-24 08:00:00'),
(7, 7, 'neutral', 12, 12.00, 12.00, '2026-06-12 10:29:33'),
(8, 7, 'negativ', 13, 13.00, 13.00, '2026-06-08 08:00:00'),
(9, 7, 'negativ', 100, 60.00, 50.00, '2026-06-13 09:36:11'),
(10, 7, 'neutral', 20, 20.00, 20.00, '2026-06-20 10:00:00'),
(11, 7, 'negativ', 40, 40.00, 40.00, '2026-06-13 09:38:53'),
(15, 8, 'positiv', 20, 20.00, 20.00, '2026-06-15 16:46:24'),
(16, 8, 'neutral', 50, 50.00, 50.00, '2026-06-14 10:00:00'),
(17, 8, 'negativ', 100, 100.00, 100.00, '2026-06-16 10:00:00');

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('admin','user') NOT NULL DEFAULT 'user',
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Daten für Tabelle `users`
--

INSERT INTO `users` (`id`, `username`, `password_hash`, `role`, `active`, `created_at`) VALUES
(1, 'admin', '$2y$10$zeKcenoQPioA37iPaJddzu8C2kumYGv1VkRtDJLwtmJx3.aMVxiRW', 'admin', 1, '2026-06-12 09:00:17'),
(7, 'user1', '$2y$10$Vk7OPRaSxSnZv3CX8Lwep.pC.kQn2HBTKsSoxjiQGSuekw5nMYyJK', 'user', 1, '2026-06-12 09:43:04'),
(9, 'kirill', '$2y$10$ZP6lCDGMDdd5W.dsBTgn9uXHujmwCXb6/ZSisZycUd5SyECrCEy6m', 'admin', 1, '2026-06-15 17:38:07');

--
-- Indizes der exportierten Tabellen
--

--
-- Indizes für die Tabelle `locations`
--
ALTER TABLE `locations`
  ADD PRIMARY KEY (`id`);

--
-- Indizes für die Tabelle `measurements`
--
ALTER TABLE `measurements`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_measurements_location` (`location_id`);

--
-- Indizes für die Tabelle `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- AUTO_INCREMENT für exportierte Tabellen
--

--
-- AUTO_INCREMENT für Tabelle `locations`
--
ALTER TABLE `locations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT für Tabelle `measurements`
--
ALTER TABLE `measurements`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- AUTO_INCREMENT für Tabelle `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- Constraints der exportierten Tabellen
--

--
-- Constraints der Tabelle `measurements`
--
ALTER TABLE `measurements`
  ADD CONSTRAINT `fk_measurements_location` FOREIGN KEY (`location_id`) REFERENCES `locations` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
