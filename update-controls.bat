@echo off
REM BLACKSITE — Windows NIST controls updater
REM Schedule via Task Scheduler: daily at midnight
REM   Action: Program/script = C:\path\to\blacksite\update-controls.bat
REM   Start in: C:\path\to\blacksite

setlocal
set BLACKSITE_DIR=%~dp0
cd /d "%BLACKSITE_DIR%"

echo [%date% %time%] Checking NIST 800-53r5 controls...

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python -c "import sys; sys.path.insert(0,'.'); from app.updater import update_if_needed, load_catalog; cfg={'nist':{'controls_dir':'controls'}}; ok=update_if_needed(cfg); cat=load_catalog(cfg) if ok else {}; print(f'Controls: {len(cat)} loaded') if ok else print('WARNING: Update failed')"

echo [%date% %time%] Done.
