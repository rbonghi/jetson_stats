#!/usr/bin/env bash
set -euo pipefail

PKG_NAME="jetson_stats"
APP_NAME="jtop"
SYSTEMD_UNIT="jtop.service"

if [[ $EUID -eq 0 ]]; then
  echo "Please first run 'sudo -v'"
  echo "Then run this script by itself, NOT with sudo"
  exit 1
fi

echo "Ensuring pip3 & pipx exist"

need_update=0
to_install=()

if ! command -v pip3 >/dev/null 2>&1; then
  to_install+=("python3-pip")
  need_update=1
fi

if ! command -v pipx >/dev/null 2>&1; then
  to_install+=("pipx")
  need_update=1
fi

if (( need_update )); then
  echo "Missing: ${to_install[*]} → installing via apt"
  sudo apt-get update
  sudo apt-get install -y "${to_install[@]}"
else
  echo "pip3 and pipx already installed."
fi

# Make sure future shells have ~/.local/bin in PATH (no-op if already set)
pipx ensurepath || true

echo "Installing ${APP_NAME} with pipx"
  pipx install "git+https://github.com/rbonghi/jetson_stats.git"

JTOP_BIN="$HOME/.local/bin/${APP_NAME}"
[ -x "$JTOP_BIN" ] || JTOP_BIN="$HOME/.local/share/pipx/venvs/${PKG_NAME}/bin/${APP_NAME}"

echo "Ensuring a systemd unit exists and points to ${JTOP_BIN}"
UNIT_FILE="/etc/systemd/system/${SYSTEMD_UNIT}"
if [ ! -f "${UNIT_FILE}" ]; then
  # Create a minimal unit if repo didn't install one
  echo "Creating ${UNIT_FILE}…"
  sudo tee "${UNIT_FILE}" >/dev/null <<EOF
[Unit]
Description=Jetson Stats (jtop)
After=network.target

[Service]
Environment="JTOP_SERVICE=True"
ExecStart=${JTOP_BIN} --force
Restart=on-failure
RestartSec=10s
TimeoutStartSec=30s
TimeoutStopSec=30s

[Install]
WantedBy=multi-user.target
EOF
fi

echo "Enabling and starting ${SYSTEMD_UNIT}…"
sudo systemctl daemon-reload
sudo systemctl enable "${SYSTEMD_UNIT}"
sudo systemctl restart "${SYSTEMD_UNIT}"

echo
echo "You can now run '${APP_NAME}'  sudo NOT  needed)."
