#!/usr/bin/env bash
set -euo pipefail

SERVICE_FILE="$HOME/.config/systemd/user/jarvis.service"

systemctl --user stop jarvis || true
systemctl --user disable jarvis || true
rm -f "$SERVICE_FILE"
systemctl --user daemon-reload

echo "Jarvis user service removed."
