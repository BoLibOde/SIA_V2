# Raspberry-Pi-UI-Runtime + Umgang mit Device-Secrets

Die Raspberry-Pi-UI sollte als **Desktop-Anwendung** über den Desktop-Autostart laufen, damit das
Pygame-Fenster auf dem Pi-Display sichtbar ist. Für eine sichtbare UI ist dieser Desktop-Autostart-Pfad
das einzig unterstützte Runtime-Modell.

Verwende die Hilfsskripte im Repository-Root.

## 1) Lokale Device-Env-Datei anlegen

```bash
cd ~/Desktop/SIA_V2
cp .env.device.example .env.device
```

`.env.device` ist **nur lokal** und enthält Secrets (`SIA_DEVICE_TOKEN`).
Nicht committen.

Aktuelle Beispiel-Defaults:

- `SIA_SERVER_URL=http://100.74.7.35` (Platzhalter, umgebungsspezifisch; auf die Server-Adresse setzen, die dein Pi erreichen kann, z. B. Tailscale-IP, LAN-IP oder DNS-Name)
- `SIA_UPLOAD_ENDPOINT=/device_ingest.php`
- `SIA_HEALTH_ENDPOINT=/device_ingest.php`

## 2) Manueller Upload-Test

```bash
cd ~/Desktop/SIA_V2
chmod +x manual_upload_test.sh
./manual_upload_test.sh
```

Das sendet eine POST-Anfrage an `${SIA_SERVER_URL}${SIA_UPLOAD_ENDPOINT}` mit `X-Device-Token` und einem aktuellen Zeitstempel.

## 3) UI-Runtime-Skript starten

```bash
cd ~/Desktop/SIA_V2
chmod +x start_ui.sh
./start_ui.sh
```

`start_ui.sh`:

- aktiviert `.venv`
- lädt `.env.device`
- exportiert `SIA_SERVER_URL`, `SIA_UPLOAD_ENDPOINT`, `SIA_HEALTH_ENDPOINT`, `SIA_DEVICE_TOKEN`, `SIA_DEVICE_ID`
- startet `python -m device.main`
- schreibt die App-Ausgabe in `ui-autostart.log`
- enthält Schutz vor Doppelstarts (wenn bereits ein `device.main`-Prozess existiert, wird der Start übersprungen und protokolliert)

## 4) Desktop-Autostart

Den Desktop-Autostart-Eintrag auf dieses Skript zeigen lassen:

```ini
Exec=/home/<user>/Desktop/SIA_V2/start_ui.sh
Path=/home/<user>/Desktop/SIA_V2
```

So bleibt die UI an die eingeloggte Desktop-Sitzung (Wayland/X-Session) gekoppelt, was für den Start der Pygame-Anzeige erforderlich ist.

## 5) Empfohlener Update-Ablauf auf dem Pi

`git pull` für routinemäßige Pi-Updates vermeiden, wenn das lokale Branch-Tracking unsicher ist
oder wenn der lokale Merge-Status unklar ist. `git pull` kann unerwartet fehlschlagen oder lokale Merges erzeugen.
`update_pi.sh` verwendet ein Update nur per Fast-Forward (`git merge --ff-only origin/main`) und beendet sich mit
klaren Hinweisen, wenn das Update nicht sicher durchgeführt werden kann.
Verwende die Hilfsskripte im Repository-Root:

```bash
cd ~/Desktop/SIA_V2
chmod +x restart_ui.sh update_pi.sh
./update_pi.sh
```

`update_pi.sh` wird:

- `origin/main` holen und per Fast-Forward in vorhersagbarer Weise aktualisieren
- die lokale `.env.device` beibehalten
- die Python-Abhängigkeiten des Devices aktualisieren
- die laufende UI-Instanz beenden und die aktualisierte Version über `restart_ui.sh` starten

> **Wichtig:** Nach jeder Codeänderung (manuelles `git pull`, Dateikopie usw.) übernimmt der laufende
> Python-Prozess neuen Code **nicht automatisch** — er muss neu gestartet werden.
> `update_pi.sh` übernimmt das automatisch. Wenn du auf anderem Weg deployst, starte
> die UI anschließend manuell neu.

## 6) Single-Instance-Regel

Es darf genau **ein** Prozess `python -m device.main` laufen.

Keinen parallelen `systemd`-Service für `device.main` zusammen mit Desktop-Autostart betreiben.
Diese Kombination kann doppelte Uploads und aufgeblähte Dashboard-Zähler verursachen.

Empfohlenes Setup für eine sichtbare Pi-UI:

```bash
sudo systemctl disable --now sia-device
```

Danach soll der Desktop-Autostart-Eintrag die App beim Login starten.

Die Anzahl laufender Prozesse prüfen mit:

```bash
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

Erwartetes Ergebnis:

- genau eine Prozesszeile
- Anzahl = `1`

Erwartetes Upload-Verhalten bei dieser Runtime:

- Live-Uploads sind die einzige Quelle für Stimmungsereignisse / Stimmungszähler.
- Periodische Uploads sind ausschließlich 15-Minuten-Sensoraggregate.
- Periodische Aggregat-Uploads dürfen die Stimmungszähler nicht verändern.

## 7) Sauberer Neustart

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

## 8) Retry-Puffer / Bereinigung veralteter Uploads

Fehlgeschlagene Uploads werden lokal gepuffert in:

```text
device/pending_uploads.json
```

Prüfen mit:

```bash
cat ~/Desktop/SIA_V2/device/pending_uploads.json
```

Normalzustand:

```json
[]
```

Wenn die Datei alte gepufferte Ereignisse enthält, die du **bewusst verwerfen** willst, bevor die App das nächste Mal startet:

```bash
pkill -f "python -m device.main"
printf '[]
' > ~/Desktop/SIA_V2/device/pending_uploads.json
cd ~/Desktop/SIA_V2
./restart_ui.sh
```

Das nur tun, wenn alte gepufferte Uploads ausdrücklich verworfen statt erneut versucht werden sollen.

## 9) Nur manueller Neustart (kein Update)

Wenn du die App nur neu starten musst, ohne neuen Code zu ziehen:

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
```

Nach dem Neustart prüfen mit:

```bash
pgrep -af "python -m device.main"
tail -n 40 ~/Desktop/SIA_V2/ui-autostart.log
```
