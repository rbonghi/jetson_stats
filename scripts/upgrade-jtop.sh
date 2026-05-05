#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="jtop"
PKG_NAME="jetson_stats"
VENV_DIR="$HOME/.local/share/$APP_NAME"
JTOP_BIN="$VENV_DIR/bin/$APP_NAME"
JTOP_PYTHON="$VENV_DIR/bin/python"
SYMLINK_PATH="/usr/local/bin/$APP_NAME"
SYSTEMD_SERVICE="${APP_NAME}.service"
JTOP_REF="${JTOP_REF:-git+https://github.com/rbonghi/jetson_stats.git}"

cleanup() {
  local exit_code=$?
  local line_no=${BASH_LINENO[0]:-unknown}
  local command=${BASH_COMMAND:-unknown}

  # Do not print a trap error for intentional exits that already printed a clear message.
  if [[ "$command" == "exit 1" || "$command" == "exit 0" ]]; then
    return "$exit_code"
  fi

  echo "Error on line ${line_no}: command '${command}' exited with status ${exit_code}" >&2
}
trap cleanup ERR

if [[ $EUID -eq 0 ]]; then
  echo "Please first run:    sudo -v"
  echo ""
  echo "That will allow this script to use sudo."
  echo ""
  echo "Then run this script again without sudo."
  exit 1
fi

# ── Remove legacy system-wide jtop installs ────────────────────────────────
remove_legacy_jtop() {
  echo "Checking for legacy system jtop installs outside the uv venv..."

  local legacy_dirs=()
  while IFS= read -r path; do
    case "$path" in
      "$VENV_DIR"/*) continue ;;
    esac
    legacy_dirs+=("$path")
  done < <(
    sudo find /usr/lib /usr/local/lib \
      -type d \
      -name 'jtop' \
      -path '*/python3*/*-packages/*' \
      -prune \
      -print
  )

  if (( ${#legacy_dirs[@]} == 0 )); then
    echo "No legacy jtop installs found."
    return 0
  fi

  echo "Found legacy jtop directories:"
  printf '  %s\n' "${legacy_dirs[@]}"

  echo "Attempting to uninstall legacy system jtop with system Python tools..."
  for py in /usr/bin/python3 /usr/bin/python3.[0-9]* \
            /usr/local/bin/python3 /usr/local/bin/python3.[0-9]*; do
    if [[ -x "$py" ]]; then
      echo "Trying: sudo $py -m pip uninstall -y jetson-stats jetson_stats"
      sudo "$py" -m pip uninstall -y jetson-stats jetson_stats || true
    fi
  done

  echo "Rechecking for leftover legacy jtop directories..."
  local leftover_dirs=()
  while IFS= read -r path; do
    case "$path" in
      "$VENV_DIR"/*) continue ;;
    esac
    leftover_dirs+=("$path")
  done < <(
    sudo find /usr/lib /usr/local/lib \
      -type d \
      -name 'jtop' \
      -path '*/python3*/*-packages/*' \
      -prune \
      -print
  )

  if (( ${#leftover_dirs[@]} > 0 )); then
    echo "Force-removing leftover directories:"
    printf '  %s\n' "${leftover_dirs[@]}"
    sudo rm -rf "${leftover_dirs[@]}"
  else
    echo "All legacy jtop directories removed."
  fi
}

remove_legacy_jtop

# ── Ensure uv and venv exist ───────────────────────────────────────────────
export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1 || [[ ! -d "$VENV_DIR" ]]; then
  echo "uv or jtop venv not found — running full installer..."
  sudo -v
  curl -LsSf https://raw.githubusercontent.com/rbonghi/jetson_stats/master/scripts/install_jtop_torun_without_sudo.sh | bash
  exit 0
fi

if [[ ! -x "$JTOP_PYTHON" ]]; then
  echo "Existing jtop venv Python not found:"
  echo "  $JTOP_PYTHON"
  echo "Run the full installer first."
  exit 1
fi

# ── Resolve site-packages path dynamically ────────────────────────────────
SITE_PACKAGES="$("$JTOP_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
if [[ -z "$SITE_PACKAGES" ]]; then
  echo "Cannot locate site-packages for $JTOP_PYTHON"
  exit 1
fi

# ── Stop service, clean pycache, upgrade ──────────────────────────────────
jtop_service_exists() {
  systemctl list-unit-files "$SYSTEMD_SERVICE" --no-legend | grep -q "^$SYSTEMD_SERVICE"
}

if jtop_service_exists; then
  echo "Stopping $SYSTEMD_SERVICE before upgrade..."
  sudo systemctl stop "$SYSTEMD_SERVICE" || true
else
  echo "$SYSTEMD_SERVICE not found; continuing without stopping service."
fi

if [[ -d "$SITE_PACKAGES" ]]; then
  echo "Removing stale __pycache__ directories under:"
  echo "  $SITE_PACKAGES"
  sudo find "$SITE_PACKAGES" \
    -type d \
    -name '__pycache__' \
    -prune \
    -exec rm -rf {} +
else
  echo "site-packages directory not found:"
  echo "  $SITE_PACKAGES"
  exit 1
fi

echo "Upgrading $PKG_NAME from:"
echo "  $JTOP_REF"

uv pip install \
  --python "$JTOP_PYTHON" \
  --upgrade \
  --force-reinstall \
  "$JTOP_REF"

if [[ ! -x "$JTOP_BIN" ]]; then
  echo "Upgrade failed: jtop binary not found:"
  echo "  $JTOP_BIN"
  exit 1
fi

echo "Refreshing symlink:"
echo "  $SYMLINK_PATH -> $JTOP_BIN"
sudo ln -sf "$JTOP_BIN" "$SYMLINK_PATH"

if jtop_service_exists; then
  echo "Reloading systemd and restarting $SYSTEMD_SERVICE..."
  sudo systemctl daemon-reload || true
  sudo systemctl restart "$SYSTEMD_SERVICE" || {
    echo "WARNING: upgraded jtop, but failed to restart $SYSTEMD_SERVICE." >&2
    echo "You can try manually with: sudo systemctl restart $SYSTEMD_SERVICE" >&2
  }
else
  echo "$SYSTEMD_SERVICE not found; skipping systemd reload/restart."
fi

echo
echo "Upgrade complete."
echo "jtop executable: $SYMLINK_PATH -> $JTOP_BIN"
"$JTOP_BIN" --version || true
