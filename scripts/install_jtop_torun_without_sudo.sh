#!/usr/bin/env bash
# This script installs jtop into a user's uv venv but sets up
# a system-wide symlink and a root-level systemd service.
set -Eeuo pipefail

# Configuration
APP_NAME="jtop"
PKG_NAME="jetson_stats"
VENV_DIR="$HOME/.local/share/$APP_NAME"
JTOP_BIN="$VENV_DIR/bin/$APP_NAME"
SYMLINK_PATH="/usr/local/bin/$APP_NAME"
SYSTEMD_UNIT="/etc/systemd/system/${APP_NAME}.service"
JTOP_REF="${JTOP_REF:-git+https://github.com/rbonghi/jetson_stats.git}"

# Error Handling
cleanup() {
  echo "Error on line $BASH_LINENO. Exit code: $?" >&2
}
trap cleanup ERR

if [[ $EUID -eq 0 ]]; then
  echo "Please first run 'sudo -v'"
  echo "This script must be run as a regular user.  NOT with sudo."
  exit 1
fi

# Installation 
echo "Installing prerequisites (curl, ca-certificates)..."
sudo apt update -y
sudo apt install -y --no-install-recommends curl ca-certificates python3-pip

# Ensure uv is installed
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing 'uv' (an exceptionally fast Python package installer)"
  curl -fsSL https://astral.sh/uv/install.sh | sh
else
  echo "'uv' is already installed."
fi

export PATH="$HOME/.local/bin:$PATH"

echo "Creating Python virtual environment in $VENV_DIR..."
uv venv "$VENV_DIR" -p python3.12 --seed

echo "Installing/upgrading $PKG_NAME from: $JTOP_REF"
uv pip install --python "$VENV_DIR/bin/python" --upgrade "$JTOP_REF"
# Optional: make proprietary pylibjetsonpower visible inside the venv (Thor).
# This is NOT required for upstream jetson_stats; it is a local convenience so
# the service (running from this venv) can import pylibjetsonpower if present.
echo "Checking for NVIDIA pylibjetsonpower (optional)..."
SYS_PYLIBJETSONPOWER=""
for p in \
  /usr/lib/python3/dist-packages/pylibjetsonpower \
  /usr/local/lib/python*/dist-packages/pylibjetsonpower \
  /usr/lib/python*/dist-packages/pylibjetsonpower
do
  if [[ -d "$p" ]]; then
    SYS_PYLIBJETSONPOWER="$p"
    break
  fi
done

if [[ -n "$SYS_PYLIBJETSONPOWER" && -f "$SYS_PYLIBJETSONPOWER/__init__.py" ]]; then
  VENV_SITE="$("$VENV_DIR/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  echo "  Found: $SYS_PYLIBJETSONPOWER"
  echo "  Linking into venv: $VENV_SITE/pylibjetsonpower"
  # Remove any previous link/dir so the link is deterministic
  rm -rf "$VENV_SITE/pylibjetsonpower" 2>/dev/null || true
  ln -s "$SYS_PYLIBJETSONPOWER" "$VENV_SITE/pylibjetsonpower"
else
  echo "  pylibjetsonpower not found (skipping)."
fi

# Verify binary exists (run as user)
if ! test -x "$JTOP_BIN"; then
  echo " Installation failed: '$JTOP_BIN' binary not found."
  exit 1
fi

# This makes 'jtop' (user) and 'sudo jtop' (root) work correctly
sudo ln -sf "$JTOP_BIN" "$SYMLINK_PATH"
echo "Symlink created: $SYMLINK_PATH"

if [ -f "$SYSTEMD_UNIT" ]; then
  echo "Found existing jtop service. It will be overwritten."
fi

echo "Creating systemd service: $SYSTEMD_UNIT"
sudo tee "$SYSTEMD_UNIT" >/dev/null <<EOF
[Unit]
Description=Jetson Stats (jtop service)
After=network.target

[Service]
Environment="JTOP_SERVICE=True"
ExecStart=${SYMLINK_PATH} --force
Restart=on-failure
RestartSec=10s
TimeoutStartSec=30s
TimeoutStopSec=30s

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling and starting $APP_NAME system service"
sudo systemctl daemon-reload
sudo systemctl enable "${APP_NAME}.service"
sudo systemctl restart "${APP_NAME}.service"
sudo systemctl status "${APP_NAME}.service" --no-pager

echo
echo "Installation Complete! "
echo
echo "You can now run '$APP_NAME' or 'sudo $APP_NAME' (privileged)."

