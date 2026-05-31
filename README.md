# SIA V2

Clean rebuild of the SIA mood bar-o-meter project.

## Repository file structure

```text
SIA_V2/
├── README.md
├── setup.sh
├── requirements-device.txt
├── requirements-server.txt
├── device/
│   ├── __init__.py
│   ├── aggregation_service.py
│   ├── config.py
│   ├── gpio_handler.py
│   ├── main.py
│   ├── models.py
│   ├── sensor_service.py
│   ├── ui.py
│   ├── upload_service.py
│   └── assets/
│       ├── bad.png
│       ├── bad.svg
│       ├── empty.txt
│       ├── good.png
│       ├── good.svg
│       ├── meh.png
│       └── meh.svg
└── server/
    ├── __init__.py
    ├── db.py
    ├── main.py
    ├── models.py
    ├── schemas.py
    └── routes/
        ├── __init__.py
        ├── ingest.py
        └── summary.py
```

## Quick setup (Raspberry Pi / target machine)

Run `setup.sh` once to clone the repo into `~/Desktop/SIA_V2` and install everything.  
Run it again at any time to update only changed files.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/BoLibOde/SIA_V2/main/setup.sh)
```

Or, if you already have the file locally:

```bash
chmod +x setup.sh
./setup.sh
```

The script will:
1. Install required system packages (`git`, `python3`, `pygame`, etc.)
2. Clone `BoLibOde/SIA_V2` into `~/Desktop/SIA_V2` (or pull the latest changes if already cloned)
3. Install all Python dependencies from `requirements-device.txt` and `requirements-server.txt`
4. Verify the repo state and report success or any missing files

After setup, start the device app with:

```bash
cd ~/Desktop/SIA_V2
.venv/bin/python -m device.main
```

## Server run

1. Create a virtual environment
2. Install dependencies from `requirements-server.txt`
3. Set `DATABASE_URL`
4. Run:

```bash
uvicorn server.main:app --reload
```
