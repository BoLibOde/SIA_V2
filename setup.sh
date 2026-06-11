#!/bin/bash
# setup.sh -- sync SIA_V2 to ~/Desktop/SIA_V2 and install all dependencies.
# Run on the Raspberry Pi. Safe to re-run: updates only changed files.

set -eo pipefail

REPO_URL="https://github.com/BoLibOde/SIA_V2.git"
BRANCH="main"
TARGET_DIR="$HOME/Desktop/SIA_V2"
VENV_DIR="$TARGET_DIR/.venv"

echo "=== SIA V2 Setup ==="

# 1. System packages
echo "[1/4] Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y -q \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-pygame \
    libopenblas-dev \
    i2c-tools

# 2. Clone or update the repo
echo "[2/4] Syncing repository to $TARGET_DIR..."
if [ -d "$TARGET_DIR/.git" ]; then
    cd "$TARGET_DIR"
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
    echo "  Repository updated."
else
    mkdir -p "$HOME/Desktop"
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
    echo "  Repository cloned."
fi

# 3. Virtual environment + Python dependencies
echo "[3/4] Installing Python dependencies..."
if [ ! -d "$VENV_DIR" ]; then
    # inherit system-site-packages so pygame is available
    python3 -m venv --system-site-packages "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet --upgrade -r "$TARGET_DIR/requirements-device.txt"
"$VENV_DIR/bin/pip" install --quiet --upgrade -r "$TARGET_DIR/requirements-server.txt" || \
    echo "  (server dependencies skipped -- not needed for device-only setup)"

# 4. Verify key files are present
echo "[4/4] Verifying repository state..."
cd "$TARGET_DIR"
echo "  Branch : $(git rev-parse --abbrev-ref HEAD)"
echo "  Commit : $(git rev-parse --short HEAD)"

MISSING=0
for FILE in \
    device/main.py device/ui.py device/config.py \
    device/assets/good.png device/assets/meh.png device/assets/bad.png; do
    if [ ! -f "$TARGET_DIR/$FILE" ]; then
        echo "  MISSING: $FILE"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 0 ]; then
    echo ""
    echo "=== Setup complete! ==="
    echo "Run the device app with:"
    echo "  cd $TARGET_DIR && $VENV_DIR/bin/python -m device.main"
else
    echo ""
    echo "=== Setup finished with warnings -- some files are missing. ==="
    exit 1
fi
