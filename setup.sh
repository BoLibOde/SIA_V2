#!/bin/bash
# setup.sh -- sync SIA_V2 to ~/Desktop/SIA_V2 and install all dependencies.
# Run this script on the Raspberry Pi (or any Debian/Ubuntu machine).
# Safe to run repeatedly: it updates only changed files on subsequent runs.

set -e

REPO_URL="https://github.com/BoLibOde/SIA_V2.git"
BRANCH="main"
TARGET_DIR="$HOME/Desktop/SIA_V2"
VENV_DIR="$TARGET_DIR/.venv"

echo "=== SIA V2 Setup ==="

# --- Install system packages ---
echo "[1/4] Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y -q \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-pygame \
    libatlas-base-dev \
    i2c-tools

# --- Clone or update the repo ---
echo "[2/4] Syncing repository to $TARGET_DIR..."

if [ -d "$TARGET_DIR/.git" ]; then
    # Repo already exists -- fetch and update only changed files
    cd "$TARGET_DIR"
    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
    git reset --hard "origin/$BRANCH"
    echo "Repository updated."
else
    # First run -- clone fresh
    mkdir -p "$HOME/Desktop"
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
    echo "Repository cloned."
fi

# --- Install Python dependencies into a virtual environment ---
echo "[3/4] Installing Python dependencies..."

# Create venv if it does not exist yet (inherit system-site-packages for pygame)
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi

# Device dependencies
"$VENV_DIR/bin/pip" install --quiet -r "$TARGET_DIR/requirements-device.txt"

# Server dependencies (optional -- skip on error so device-only setups still work)
"$VENV_DIR/bin/pip" install --quiet -r "$TARGET_DIR/requirements-server.txt" || \
    echo "  (Server dependencies skipped -- not required on device-only setup)"

# --- Verify repo state ---
echo "[4/4] Verifying repository state..."
cd "$TARGET_DIR"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "  Branch : $CURRENT_BRANCH"
echo "  Commit : $CURRENT_COMMIT"

# Quick check that key files are present
MISSING=0
for FILE in device/main.py device/ui.py device/config.py device/assets/good.png device/assets/meh.png device/assets/bad.png; do
    if [ ! -f "$TARGET_DIR/$FILE" ]; then
        echo "  MISSING: $FILE"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 0 ]; then
    echo ""
    echo "=== Setup complete! ==="
    echo "Run the device app with:"
    echo "  cd $TARGET_DIR && .venv/bin/python -m device.main"
else
    echo ""
    echo "=== Setup finished with warnings -- some files are missing. ==="
    exit 1
fi
