# Offline-Modus – Vollständige Dokumentation

Dieses Dokument beschreibt den Offline-Betrieb des SIA-Raspberry-Pi-Geräts im Detail.

---

## Inhaltsverzeichnis

1. [Betriebszustände im Überblick](#betriebszustände-im-überblick)
2. [Startup-Menü](#startup-menü)
3. [Offline-Modus: Was passiert intern?](#offline-modus-was-passiert-intern)
4. [Datenspeicherung](#datenspeicherung)
5. [Tageswechsel und Auto-Reset](#tageswechsel-und-auto-reset)
6. [Online-Modus ohne Serververbindung (Fallback)](#online-modus-ohne-serververbindung-fallback)
7. [Troubleshooting / FAQ](#troubleshooting--faq)

---

## Betriebszustände im Überblick

| Zustand | Server | Datenbasis | Beschreibung |
|---|---|---|---|
| **Online mit Server** | ✅ Verbunden | Server (autoritär) | Normalbetrieb; Server-Zähler sind maßgeblich |
| **Online ohne Server** | ❌ Getrennt | Lokal (Fallback) | Verbindungsversuche laufen weiter; Retry-Buffer aktiv |
| **Offline-Modus** | ⛔ Deaktiviert | Nur lokal | Keine Server-Kommunikation; ideal für Messen / Standalone |

---

## Startup-Menü

Beim Programmstart wird vor der Haupt-App ein Auswahlmenü angezeigt:

```
┌──────────────────────────────────────────────────────┐
│           SIA Stimmungs-bar-o-meter                  │
│         Bitte Betriebsmodus wählen:                  │
│                                                      │
│   ┌─────────────────┐   ┌─────────────────┐         │
│   │  Online-Modus   │   │  Offline-Modus  │         │
│   │  [GUT-Taste / O]│   │  [NEUTRAL/SCHL.]│         │
│   └─────────────────┘   └─────────────────┘         │
│                                                      │
│    [O] Online  [F] Offline  [ESC] Menü wiederholen   │
└──────────────────────────────────────────────────────┘
```

### Button-Belegung

| Taste / Button | Aktion |
|---|---|
| **GUT-Button** (GPIO 27) | Online-Modus wählen |
| **NEUTRAL-Button** (GPIO 22) | Offline-Modus wählen |
| **SCHLECHT-Button** (GPIO 17) | Offline-Modus wählen |
| Tastatur **O** oder **Enter** | Online-Modus wählen |
| Tastatur **F** | Offline-Modus wählen |
| Tastatur **ESC** / Fensterschließen | Im Menü bleiben (wiederholen) |

---

## Offline-Modus: Was passiert intern?

Im Offline-Modus (`operating_mode = "offline"`) gilt:

- **Keine Server-Kommunikation**: Upload-Service wird nicht aufgerufen.
- **Kein Retry-Buffer**: Es werden keine Uploads gepuffert.
- **Button-Druck** → lokale Zähler werden sofort inkrementiert und in `tagesgesamt.json` gespeichert.
- **Sensor-Werte** werden live angezeigt (nicht gespeichert, da zu grob für sinnvolle Auswertung).
- **Status-Bar** zeigt: `Modus: Offline (Lokal)`

---

## Datenspeicherung

### Datei: `device/tagesgesamt.json`

```json
{
  "date": "2026-07-08",
  "good": 5,
  "neutral": 3,
  "bad": 2,
  "last_updated": "2026-07-08T14:30:00+00:00"
}
```

| Feld | Typ | Beschreibung |
|---|---|---|
| `date` | ISO-8601 Datum | Heute (lokale Zeit) |
| `good` | Integer | Anzahl "Gut"-Drücke heute |
| `neutral` | Integer | Anzahl "Neutral"-Drücke heute |
| `bad` | Integer | Anzahl "Schlecht"-Drücke heute |
| `last_updated` | ISO-8601 Timestamp | Zeitpunkt des letzten Schreibvorgangs |

### Persistenz über App-Neustarts

Die Datei bleibt über App-Neustarts erhalten. Bei erneutem Start im Offline-Modus werden die Zähler des aktuellen Tages wiederhergestellt.

### Klasse: `OfflineStorage` (`device/offline_storage.py`)

| Methode | Beschreibung |
|---|---|
| `load_daily_counts()` | Lädt heutige Zähler; gibt `MoodCounts(0,0,0)` bei fehlendem/veraltetem File zurück |
| `save_daily_counts(counts)` | Schreibt aktuelle Zähler auf Disk |
| `reset_on_new_day(current)` | Prüft Datumswechsel; gibt `(True, MoodCounts())` zurück, wenn zurückgesetzt wurde |

---

## Tageswechsel und Auto-Reset

Der Offline-Modus prüft bei jedem Loop-Tick, ob das Datum seit dem letzten Schreibvorgang gewechselt hat:

1. `reset_on_new_day()` vergleicht das in `tagesgesamt.json` gespeicherte Datum mit `date.today()`.
2. Ist das Datum veraltet → Zähler werden auf `{good:0, neutral:0, bad:0}` zurückgesetzt und neu gespeichert.
3. Die In-Memory-Zähler der App werden ebenfalls zurückgesetzt.

Der Reset erfolgt automatisch beim nächsten Programmstart nach Mitternacht oder beim ersten Loop-Tick nach Mitternacht (wenn die App durchläuft).

---

## Online-Modus ohne Serververbindung (Fallback)

Wenn der Server im Online-Modus nicht erreichbar ist:

1. **Retry-Buffer** bleibt aktiv – alle Button-Drücke werden gepuffert und bei Wiederverbindung gesendet.
2. **Lokale Offline-Storage** dient als Fallback für die Anzeige der Zähler.
3. **Exponential Backoff** für den Health-Check:
   - Start: 30 Sekunden
   - Jede Fehler-Iteration: Intervall × 2 (max. 60 Sekunden)
   - Nach Wiederverbindung: Reset auf 30 Sekunden + sofortiger Zähler-Abgleich mit Server
4. **Status-Bar** zeigt: `Modus: Online | Server: offline (lokal gepuffert)`
5. Nach Wiederverbindung → `Modus: Online | Server: verbunden`

### Manuelle Umgebungsvariable (headless / automatisiert)

```bash
export SIA_OPERATING_MODE=offline   # erzwingt Offline-Modus ohne Startup-Menü
export SIA_OPERATING_MODE=online    # erzwingt Online-Modus (Standard)
```

---

## Troubleshooting / FAQ

### Die Zähler sind nach einem Neustart verschwunden

Prüfe, ob `device/tagesgesamt.json` existiert:

```bash
cat ~/Desktop/SIA_V2/device/tagesgesamt.json
```

Wenn die Datei fehlt oder das gespeicherte Datum nicht heute ist, beginnt der Offline-Modus bei Null.

### Die Anzeige zeigt weiterhin alte Zähler

Das Datum in `tagesgesamt.json` stimmt noch mit heute überein. Die Zähler werden erst beim nächsten Tageswechsel automatisch zurückgesetzt. Für manuellen Reset im laufenden Betrieb: **R-Taste** drücken (im Offline-Modus löscht das die lokalen Zähler).

### Ich möchte die Zähler manuell zurücksetzen

```bash
# App stoppen
pkill -f "python -m device.main"

# Datei zurücksetzen
printf '{"date":"'$(date +%Y-%m-%d)'","good":0,"neutral":0,"bad":0,"last_updated":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}\n' > ~/Desktop/SIA_V2/device/tagesgesamt.json

# App neu starten
cd ~/Desktop/SIA_V2 && ./restart
```

### Das Startup-Menü erscheint nicht

Das Startup-Menü wird nur beim Start über `python -m device.main` angezeigt.  
Prüfe, ob `SIA_OPERATING_MODE` als Umgebungsvariable gesetzt ist (überschreibt das Menü):

```bash
echo $SIA_OPERATING_MODE
# Leer = Menü wird angezeigt; "online" oder "offline" = Menü wird übersprungen
```

### GPIO-Buttons reagieren nicht im Startup-Menü

Prüfe die GPIO-Pin-Belegung und ob die Kabel korrekt angeschlossen sind:

```bash
raspi-gpio get 17   # SCHLECHT-Button
raspi-gpio get 22   # NEUTRAL-Button
raspi-gpio get 27   # GUT-Button
# Erwartetes Ergebnis im Ruhezustand: level=1 (Pull-up aktiv)
```

Tastatur-Alternative: **O** für Online, **F** für Offline.
