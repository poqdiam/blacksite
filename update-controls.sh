#!/usr/bin/env bash
# BLACKSITE — NIST 800-53r5 controls updater (cron script)
# Run nightly at 00:00:
#   0 0 * * * /home/graycat/projects/blacksite/update-controls.sh >> /var/log/blacksite-update.log 2>&1
#
# For Windows Task Scheduler, use update-controls.bat instead.

set -uo pipefail
BLACKSITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BLACKSITE_DIR"

LOGFILE="/var/log/blacksite-update.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $*"; }

# Activate venv if it exists
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
fi

log "Checking NIST 800-53r5 controls for updates…"

python3 -c "
import sys, json
sys.path.insert(0, '.')
from app.updater import update_if_needed, load_catalog
cfg = {'nist': {'controls_dir': 'controls'}}
ok = update_if_needed(cfg)
if ok:
    cat = load_catalog(cfg)
    print(f'OK — {len(cat)} controls available.')
    sys.exit(0)
else:
    print('WARN — Update failed. Using cached version if available.')
    sys.exit(1)
" && log "Controls update complete." || log "Controls update failed — cached version retained."

# Notify via Telegram if update fails and blacksite is running
if [[ $? -ne 0 ]] && command -v curl >/dev/null 2>&1; then
    NOTIFY_SCRIPT="/home/graycat/scripts/notify-telegram.sh"
    if [[ -x "$NOTIFY_SCRIPT" ]]; then
        bash "$NOTIFY_SCRIPT" "⚠️ *BLACKSITE* NIST controls update failed at $TIMESTAMP" "Markdown" 2>/dev/null || true
    fi
fi
