#!/usr/bin/env bash
set -euo pipefail

PKG_NAME="jetson_stats"
APP_NAME="jtop"
SYSTEMD_UNIT="jtop.service"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--pipx|--uv|--help]
  --pipx   Install using pipx (default if no argument)
  --uv     Install using uv (uv must already be installed; this script will not install it)
  --help   Show this help
USAGE
}

if [[ ${1:-} == "--help" || ${1:-} == "-h" ]]; then
  usage
  exit 0
fi

MODE="pipx"
if [[ ${1:-} == "--uv" ]]; then
  MODE="uv"
elif [[ ${1:-} == "--pipx" || -z ${1:-} ]]; then
  MODE="pipx"
elif [[ $# -gt 0 ]]; then
  echo "Unknown option: $1"
  echo
  usage
  exit 2
fi

if [[ $EUID -eq 0 ]]; then
  echo "Please first run 'sudo -v'"
  echo "Then run this script by itself, NOT with sudo"
  exit 1
fi

if [[ "$MODE" == "pipx" ]]; then
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
else
  echo "Using uv to install ${APP_NAME}"

  # Do NOT auto-install uv; require it to be present
  if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' is not installed or not on PATH."
    echo "Please install uv first, for example:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Then re-run: $0 --uv"
    exit 1
  fi

  # Ensure required packages are available
  need_update=0
  to_install=()

  if ! command -v git >/dev/null 2>&1; then
    to_install+=("git")
    need_update=1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    to_install+=("python3")
    need_update=1
  fi

  if (( need_update )); then
    echo "Missing: ${to_install[*]} → installing via apt"
    sudo apt-get update
    sudo apt-get install -y "${to_install[@]}"
  fi

  # If ~/.local/bin is not in PATH, add a hint (comment) to existing rc files only
  add_path_hint_if_needed() {
    if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
      return
    fi
    local marker="### jtop PATH hint (uv)"
    local export_line='export PATH="$HOME/.local/bin:$PATH"'
    local files=("$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile")
    local updated_any=0
    for f in "${files[@]}"; do
      if [ -f "$f" ] && ! grep -Fq "$marker" "$f"; then
        {
          echo
          echo "$marker"
          echo "# jtop was installed with uv; to make it available in new shells add this line:"
          echo "# $export_line"
        } >> "$f"
        updated_any=1
        echo "Added PATH hint to $f"
      fi
    done
    if (( ! updated_any )); then
      echo "Note: ~/.local/bin is not in PATH. To use jtop in new shells, add:"
      echo "  $export_line"
    fi
  }
  add_path_hint_if_needed

  # Install jtop with uv (force overwrite if already present)
  uv tool install --force "git+https://github.com/rbonghi/jetson_stats.git"

  JTOP_BIN="$HOME/.local/bin/${APP_NAME}"
  if [ ! -x "$JTOP_BIN" ]; then
    echo "Error: expected ${JTOP_BIN} to exist after 'uv tool install', but it was not found."
    echo "Check your uv installation and PATH, then re-run: $0 --uv"
    exit 1
  fi
fi

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
echo "You can now run '${APP_NAME}' (sudo NOT needed)."
