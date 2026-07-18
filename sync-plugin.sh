#!/usr/bin/env bash
# Push local repo edits into the installed backlot plugin cache so /ugc-* skills
# and their scripts run the current code. Re-run after editing skills/ or scripts/.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude/plugins/cache/backlot/backlot/0.3.0"

[ -d "$DEST" ] || { echo "plugin cache not found: $DEST (is backlot installed?)"; exit 1; }

rsync -a --delete "$REPO/skills/"  "$DEST/skills/"
rsync -a --delete "$REPO/scripts/" "$DEST/scripts/"

echo "synced -> $DEST"
