#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="$(cd "$REPO_ROOT" && uv run python -c "from dance_bot.config import get_settings; print(get_settings().launchd_label)")"
DOMAIN="gui/$(id -u)"
SERVICE="$DOMAIN/$LABEL"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

if launchctl print "$SERVICE" &>/dev/null; then
	launchctl bootout "$SERVICE"
	echo "LaunchAgent stopped: $LABEL"
else
	echo "LaunchAgent was not loaded: $LABEL"
fi

if [[ -f "$PLIST_DEST" ]]; then
	rm "$PLIST_DEST"
	echo "Removed: $PLIST_DEST"
fi
