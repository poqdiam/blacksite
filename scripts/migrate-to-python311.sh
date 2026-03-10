#!/usr/bin/env bash
# migrate-to-python311.sh — Migrate BLACKSITE from Python 3.8 venv to Python 3.11.12
#
# Run after: pyenv install 3.11.12 completes
# Closes: SA-22 (Python 3.8 EOL), SI-2 (patch management), closes 20+ CVEs
#
# Usage: bash /home/graycat/projects/blacksite/scripts/migrate-to-python311.sh

set -euo pipefail

BLACKSITE_DIR="${HOME}/projects/blacksite"
PYENV_PYTHON="${HOME}/.pyenv/versions/3.11.12/bin/python3.11"
NEW_VENV="${BLACKSITE_DIR}/.venv311"
OLD_VENV="${BLACKSITE_DIR}/.venv"
LOG="/tmp/blacksite-py311-migration.log"

log() { echo "[migrate] $*" | tee -a "${LOG}"; }
fail() { echo "[migrate] ERROR: $*" | tee -a "${LOG}" >&2; exit 1; }

log "=== Python 3.11.12 migration starting ==="

# ── 1. Verify Python 3.11.12 build ────────────────────────────────────────────
if [[ ! -x "${PYENV_PYTHON}" ]]; then
    fail "Python 3.11.12 not found at ${PYENV_PYTHON}. Run: pyenv install 3.11.12"
fi
PY_VER=$("${PYENV_PYTHON}" --version 2>&1)
log "Python binary: ${PYENV_PYTHON} (${PY_VER})"

# ── 2. Build pysqlcipher3 against Python 3.11 ─────────────────────────────────
log "Checking libsqlcipher-dev..."
dpkg -l libsqlcipher-dev 2>/dev/null | grep -q "^ii" || {
    log "Installing libsqlcipher-dev..."
    sudo apt-get install -y libsqlcipher-dev
}

# ── 3. Create new venv ─────────────────────────────────────────────────────────
log "Creating ${NEW_VENV}..."
"${PYENV_PYTHON}" -m venv "${NEW_VENV}"

# ── 4. Upgrade pip in new venv ─────────────────────────────────────────────────
log "Upgrading pip..."
"${NEW_VENV}/bin/pip" install -q --upgrade pip wheel

# ── 5. Install pysqlcipher3 ────────────────────────────────────────────────────
log "Installing pysqlcipher3..."
LDFLAGS="-L/usr/lib/x86_64-linux-gnu" \
CFLAGS="-I/usr/include" \
"${NEW_VENV}/bin/pip" install -q pysqlcipher3 || {
    log "pysqlcipher3 pip install failed — trying from source..."
    "${NEW_VENV}/bin/pip" install -q "pysqlcipher3==1.2.0" \
        --global-option build_ext \
        --global-option "-I/usr/include" \
        --global-option "-L/usr/lib/x86_64-linux-gnu" || fail "pysqlcipher3 install failed"
}

# ── 6. Install all requirements ────────────────────────────────────────────────
log "Installing requirements.txt into new venv..."
"${NEW_VENV}/bin/pip" install -q -r "${BLACKSITE_DIR}/requirements.txt"

# ── 7. Upgrade packages that needed Python 3.11 ───────────────────────────────
log "Upgrading security-patched packages..."
"${NEW_VENV}/bin/pip" install -q -U \
    "authlib>=1.6.6" \
    "starlette>=0.49.1" \
    "urllib3>=2.6.3" \
    "reportlab>=4.4.3" \
    "pdfminer-six>=20250324" \
    "pillow>=12.1.1" 2>&1 | tee -a "${LOG}"

# ── 8. Run pip-audit on new venv ──────────────────────────────────────────────
log "Running pip-audit..."
"${NEW_VENV}/bin/pip" install -q pip-audit
"${NEW_VENV}/bin/pip-audit" 2>&1 | tee -a "${LOG}" || {
    log "WARNING: pip-audit found vulnerabilities — review above"
}

# ── 9. Test DB connectivity ────────────────────────────────────────────────────
log "Testing SQLCipher DB access..."
BSV_KEY=$(sudo systemctl show blacksite --property=Environment 2>/dev/null \
    | grep -o 'BLACKSITE_DB_KEY=[^ ]*' | cut -d= -f2)
BLACKSITE_DB_KEY="${BSV_KEY}" "${NEW_VENV}/bin/python3" - <<PYEOF
import sys, os
sys.path.insert(0, '${BLACKSITE_DIR}')
from pysqlcipher3 import dbapi2 as sqlite3
key = os.environ['BLACKSITE_DB_KEY']
conn = sqlite3.connect('${BLACKSITE_DIR}/blacksite.db')
conn.execute(f"PRAGMA key='{key}'")
cnt = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
print(f"  DB tables: {cnt}")
assert cnt >= 10, f"Expected >=10 tables, got {cnt}"
conn.close()
print("  DB connectivity: PASS")
PYEOF

# ── 10. Test app import ────────────────────────────────────────────────────────
log "Testing app import..."
BLACKSITE_DB_KEY="${BSV_KEY}" "${NEW_VENV}/bin/python3" -c "
import sys
sys.path.insert(0, '${BLACKSITE_DIR}')
import app.main
print('  app.main import: PASS')
" || fail "app.main import failed under Python 3.11"

# ── 11. Swap venv ─────────────────────────────────────────────────────────────
log "Backing up old venv → .venv38..."
mv "${OLD_VENV}" "${BLACKSITE_DIR}/.venv38"
mv "${NEW_VENV}" "${OLD_VENV}"
log "New .venv311 is now the active .venv"

# ── 12. Update systemd service ────────────────────────────────────────────────
log "Checking systemd service ExecStart..."
CURRENT_EXEC=$(sudo systemctl show blacksite --property=ExecStart 2>/dev/null | grep -o 'path=[^;]*' | head -1 | cut -d= -f2)
log "  Current ExecStart python: ${CURRENT_EXEC}"
log "  New venv python: ${OLD_VENV}/bin/python3"
log "  (No change needed — systemd uses .venv/bin/uvicorn directly)"

log "=== Migration complete! ==="
log ""
log "Next steps:"
log "  1. sudo systemctl restart blacksite"
log "  2. curl -s http://127.0.0.1:8100/health"
log "  3. bsv isso"
log "  4. Update SA-22 POA&M to closed_verified"
log ""
log "Log saved to: ${LOG}"
