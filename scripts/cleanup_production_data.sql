-- ============================================================
-- Produktionsdaten-Cleanup für stimmungsbarometer
-- Erstellt: 2026-06-17
-- Ausführung: NUR über scripts/cleanup_production_data.sh
--             (erstellt vorher ein Backup)
-- ============================================================

USE `stimmungsbarometer`;

-- ------------------------------------------------------------
-- Schritt 1: Backup-Tabelle anlegen (Fallback ohne Shell-Backup)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `measurements_backup_cleanup`
  SELECT * FROM `measurements`;

-- ------------------------------------------------------------
-- Schritt 2: Physikalisch unmögliche Sensorwerte löschen
--   humidity > 100 % ist physikalisch ausgeschlossen.
--   temperature > 80 °C / < -20 °C unrealistisch für Innenräume.
--   co2 > 10000 ppm weit jenseits jedes Innenraumwerts.
-- ------------------------------------------------------------
DELETE FROM `measurements`
WHERE  `humidity`    > 100.00
    OR `humidity`    < 0.00
    OR `temperature` > 80.00
    OR `temperature` < -20.00
    OR `co2`         > 10000
    OR `co2`         < 0;

-- ------------------------------------------------------------
-- Schritt 3: Messungen mit Zukunfts-Timestamp löschen
-- ------------------------------------------------------------
DELETE FROM `measurements`
WHERE `created_at` > NOW();

-- ------------------------------------------------------------
-- Schritt 4: Offensichtliche Dummy-/Testwerte löschen
--   Fingerabdruck: alle drei Sensorwerte identisch gerundet
--   (z. B. 1/1/1, 12/12/12, 20/20/20, 50/50/50, 100/100/100).
-- ------------------------------------------------------------
DELETE FROM `measurements`
WHERE ROUND(`co2`) = ROUND(`humidity`)
  AND ROUND(`co2`) = ROUND(`temperature`)
  AND ROUND(`co2`) IN (1, 12, 13, 20, 40, 50, 100);

-- ------------------------------------------------------------
-- Schritt 5: Messungen vor offiziellem Produktionsstart löschen
--   Gerät war laut device_location_history ab 2026-06-16 16:14
--   scharf – alles davor sind Testmessungen.
-- ------------------------------------------------------------
DELETE FROM `measurements`
WHERE `created_at` < '2026-06-16 16:14:19';

-- ------------------------------------------------------------
-- Schritt 6: Test-Locations deaktivieren (nicht löschen,
--            wegen referenzieller Integrität)
-- ------------------------------------------------------------
UPDATE `locations`
SET    `aktiv` = 0
WHERE  `name` IN ('test', 'aktivTest', 'Zeit', 'Neu')
    OR `id`   IN (5, 6, 7, 9);

-- ------------------------------------------------------------
-- Schritt 7: sensor_hourly_aggregates neu berechnen
-- ------------------------------------------------------------
TRUNCATE TABLE `sensor_hourly_aggregates`;

INSERT INTO `sensor_hourly_aggregates`
  (`location_id`, `device_id`, `period_start`, `period_end`,
   `co2`, `humidity`, `temperature`, `sample_count`)
SELECT
  `location_id`,
  '' AS `device_id`,
  DATE_FORMAT(`created_at`, '%Y-%m-%d %H:00:00')                          AS `period_start`,
  DATE_FORMAT(`created_at`, '%Y-%m-%d %H:00:00') + INTERVAL 1 HOUR       AS `period_end`,
  ROUND(AVG(`co2`))                                                        AS `co2`,
  ROUND(AVG(`humidity`),    2)                                             AS `humidity`,
  ROUND(AVG(`temperature`), 2)                                             AS `temperature`,
  COUNT(*)                                                                  AS `sample_count`
FROM `measurements`
GROUP BY `location_id`, DATE_FORMAT(`created_at`, '%Y-%m-%d %H:00:00');

-- ------------------------------------------------------------
-- Schritt 8: Abschlusskontrolle (gibt bereinigte Daten aus)
-- ------------------------------------------------------------
SELECT 'measurements nach Cleanup' AS `info`;
SELECT m.`id`, l.`name` AS `location`, m.`mood`,
       m.`co2`, m.`humidity`, m.`temperature`, m.`created_at`
FROM   `measurements`  m
JOIN   `locations`     l ON l.`id` = m.`location_id`
ORDER  BY m.`created_at`;

SELECT 'sensor_hourly_aggregates nach Neuberechnung' AS `info`;
SELECT sha.`location_id`, l.`name`, sha.`period_start`,
       sha.`co2`, sha.`humidity`, sha.`temperature`, sha.`sample_count`
FROM   `sensor_hourly_aggregates` sha
JOIN   `locations`                l ON l.`id` = sha.`location_id`
ORDER  BY sha.`period_start`;

SELECT 'aktive Locations' AS `info`;
SELECT `id`, `name`, `aktiv` FROM `locations` ORDER BY `id`;
