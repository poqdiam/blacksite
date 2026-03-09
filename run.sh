#!/usr/bin/env bash
# BLACKSITE — Linux/macOS launcher
# Installs dependencies, downloads NIST controls if missing, starts the server.

set -uo pipefail
BLACKSITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BLACKSITE_DIR"

PORT="${BLACKSITE_PORT:-8100}"
HOST="${BLACKSITE_HOST:-127.0.0.1}"

# Check Python 3.11+
if ! python3 -c "import sys; assert sys.version_info >= (3,11)" 2>/dev/null; then
    echo "[BLACKSITE] Python 3.11+ required. Found: $(python3 --version 2>&1)"
    exit 1
fi

# Create venv if not present
if [[ ! -d ".venv" ]]; then
    echo "[BLACKSITE] Creating virtual environment…"
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install / upgrade dependencies
echo "[BLACKSITE] Checking dependencies…"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Ensure directories exist
mkdir -p uploads results controls static

echo "[BLACKSITE] Starting on http://localhost:${PORT}"
RELOAD_FLAG=""
if [[ "${BLACKSITE_DEV:-}" == "true" ]]; then
    RELOAD_FLAG="--reload"
fi
exec uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
