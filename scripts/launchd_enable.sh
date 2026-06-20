#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$REPO_ROOT/scripts/com.user.dance-bot.plist"

read -r LABEL START_INTERVAL <<EOF
$(cd "$REPO_ROOT" && uv run python -c "
from dance_bot.config import get_settings
s = get_settings()
print(s.launchd_label)
print(s.run_interval_seconds)
")
EOF

DOMAIN="gui/$(id -u)"
SERVICE="$DOMAIN/$LABEL"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$REPO_ROOT/data" "$HOME/Library/LaunchAgents"
chmod +x "$REPO_ROOT/scripts/run_dance_bot.sh"

sed \
	-e "s|__REPO_ROOT__|$REPO_ROOT|g" \
	-e "s|__HOME__|$HOME|g" \
	-e "s|__START_INTERVAL__|$START_INTERVAL|g" \
	"$PLIST_SRC" > "$PLIST_DEST"

launchctl bootout "$SERVICE" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_DEST"
launchctl enable "$SERVICE"

echo "LaunchAgent enabled: $LABEL"
echo "  plist:    $PLIST_DEST"
echo "  interval: ${START_INTERVAL}s"
echo "  log:      $REPO_ROOT/data/launchd.log"
echo ""
echo "Force run: launchctl kickstart -k $SERVICE"
echo ""
echo "Status:"
launchctl print "$SERVICE" | head -20
