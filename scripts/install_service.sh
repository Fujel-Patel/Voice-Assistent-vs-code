#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
SERVICE_TEMPLATE="$BACKEND_DIR/jarvis.service"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/jarvis.service"
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
ENV_FILE="$PROJECT_ROOT/.env"

mkdir -p "$SERVICE_DIR"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing backend venv python at $VENV_PYTHON"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env file at $ENV_FILE"
  exit 1
fi

sed \
  -e "s|__JARVIS_BACKEND_DIR__|$BACKEND_DIR|g" \
  -e "s|__JARVIS_PYTHON__|$VENV_PYTHON|g" \
  -e "s|__JARVIS_ENV_FILE__|$ENV_FILE|g" \
  "$SERVICE_TEMPLATE" > "$SERVICE_FILE"

systemctl --user daemon-reload
systemctl --user enable jarvis
systemctl --user start jarvis

echo "Service installed."
systemctl --user status jarvis --no-pager
