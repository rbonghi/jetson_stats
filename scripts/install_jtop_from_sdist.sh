#!/usr/bin/env bash
# This script installs jtop from a locally built jetson_stats sdist
# into a user's uv-managed virtualenv, but sets up:
#   - a system-wide symlink at /usr/local/bin/jtop
#   - a root-owned systemd service (jtop.service)
#
# It assumes it is located inside a cloned jetson_stats repo under scripts/,
# and that an sdist exists at dist/jetson_stats-*.tar.gz OR can be built with:
#   uv build --sdist
set -Eeuo pipefail

##############################################
# Configuration
##############################################
APP_NAME="jtop"
PKG_NAME="jetson_stats"
VENV_DIR="$HOME/.local/share/$APP_NAME"
JTOP_BIN="$VENV_DIR/bin/$APP_NAME"
SYMLINK_PATH="/usr/local/bin/$APP_NAME"
SYSTEMD_UNIT="/etc/systemd/system/${APP_NAME}.service"

# Optional overrides:
#   JTOP_SDIST=/path/to/jetson_stats-1.0.0.tar.gz  ./install_jtop_from_sdist.sh
#   or: ./install_jtop_from_sdist.sh /path/to/jetson_stats-*.tar.gz
JTOP_SDIST_ENV="${JTOP_SDIST:-}"

##############################################
# Error handling
##############################################
cleanup() {
  local exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    echo
    echo "ERROR: Installation failed (exit code $exit_code)."
    echo "Some steps may have partially completed."
    echo "You can safely re-run this script after addressing the error."
    echo
  fi
}
trap cleanup ERR

##############################################
# Helpers
##############################################
die() {
  echo "FATAL: $*" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

##############################################
# Sanity checks
##############################################
if [[ $EUID -eq 0 ]]; then
  echo "Please first run 'sudo -v' (to cache your password),"
  echo "then run this script as a regular user (WITHOUT sudo)."
  echo
  echo "Example:"
  echo "  sudo -v"
  echo "  ./scripts/install_jtop_from_sdist.sh"
  exit 1
fi

if ! sudo -n true 2>/dev/null; then
  echo "This script will need sudo for system-wide steps (symlink + systemd)."
  echo "You may be prompted for your password during the run."
  echo
fi

##############################################
# Locate repo root & sdist
##############################################
# Determine the repo root from the script location: scripts/ -> repo root
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Script directory : $SCRIPT_DIR"
echo "Assumed repo root: $REPO_ROOT"
echo

# Resolve sdist path, in priority order:
# 1. First positional argument
# 2. JTOP_SDIST environment variable
# 3. Latest dist/jetson_stats-*.tar.gz in the repo (build if missing)
SDIST_PATH="${1:-}"

if [[ -z "$SDIST_PATH" && -n "$JTOP_SDIST_ENV" ]]; then
  SDIST_PATH="$JTOP_SDIST_ENV"
fi

if [[ -z "$SDIST_PATH" ]]; then
  # No explicit path provided; use dist/ inside repo
  if ! compgen -G "$REPO_ROOT/dist/${PKG_NAME}-"*"tar.gz" >/dev/null 2>&1; then
    echo "No existing sdist found under: $REPO_ROOT/dist"
    echo "Building sdist with 'uv build --sdist'..."
    (
      cd "$REPO_ROOT"
      if ! command_exists uv; then
        echo "'uv' not found; installing uv (an exceptionally fast Python package manager)..."
        curl -fsSL https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
      fi
      uv build --sdist
    )
  fi

  # Pick the newest sdist (version-sort)
  SDIST_PATH="$(ls -1 "$REPO_ROOT"/dist/${PKG_NAME}-*.tar.gz | sort -V | tail -n 1)"
fi

# Normalize to absolute path
SDIST_PATH="$(cd "$(dirname "$SDIST_PATH")" && pwd)/$(basename "$SDIST_PATH")"

[[ -f "$SDIST_PATH" ]] || die "sdist not found: $SDIST_PATH"

echo "Using sdist: $SDIST_PATH"
echo

##############################################
# System prerequisites
##############################################
echo "Installing prerequisites (curl, ca-certificates, python3-pip)..."
sudo apt update -y
sudo apt install -y --no-install-recommends curl ca-certificates python3-pip

# Ensure uv is installed
if ! command_exists uv; then
  echo "Installing 'uv' (an exceptionally fast Python package manager)..."
  curl -fsSL https://astral.sh/uv/install.sh | sh
else
  echo "'uv' is already installed."
fi

export PATH="$HOME/.local/bin:$PATH"

##############################################
# Create venv and install package from sdist
##############################################
echo "Creating Python virtual environment in: $VENV_DIR"
uv venv "$VENV_DIR" -p python3 --seed

echo "Installing/upgrading $PKG_NAME from local sdist:"
echo "  $SDIST_PATH"
uv pip install --python "$VENV_DIR/bin/python" --upgrade "$SDIST_PATH"

##############################################
# Verify jtop binary exists
##############################################
if [[ ! -x "$JTOP_BIN" ]]; then
  die "jtop binary not found or not executable at: $JTOP_BIN"
fi

echo "Verified jtop binary at: $JTOP_BIN"
echo

##############################################
# Create system-wide symlink
##############################################
echo "Creating system-wide symlink: $SYMLINK_PATH -> $JTOP_BIN"
if [[ -L "$SYMLINK_PATH" || -e "$SYMLINK_PATH" ]]; then
  echo "Existing $SYMLINK_PATH detected; replacing it."
  sudo rm -f "$SYMLINK_PATH"
fi
sudo ln -s "$JTOP_BIN" "$SYMLINK_PATH"

##############################################
# Create / update systemd unit
##############################################
echo "Creating / updating systemd service: $SYSTEMD_UNIT"
if [[ -f "$SYSTEMD_UNIT" ]]; then
  echo "Existing $SYSTEMD_UNIT found; it will be overwritten."
fi

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

echo "Reloading systemd, enabling and starting ${APP_NAME}.service"
sudo systemctl daemon-reload
sudo systemctl enable "${APP_NAME}.service"
sudo systemctl restart "${APP_NAME}.service"
sudo systemctl status "${APP_NAME}.service" --no-pager || true

echo
echo "Installation Complete!"
echo
echo "You can now run '$APP_NAME' as your user, or 'sudo $APP_NAME' (privileged)."
echo "Service name: ${APP_NAME}.service"
echo
