@echo off
REM BLACKSITE — Windows launcher
REM Requires Python 3.11+ in PATH.

setlocal
set BLACKSITE_DIR=%~dp0
cd /d "%BLACKSITE_DIR%"

set PORT=8100
set HOST=0.0.0.0

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [BLACKSITE] Python not found in PATH. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

REM Create venv if needed
if not exist ".venv\" (
    echo [BLACKSITE] Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [BLACKSITE] Checking dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Ensure directories exist
if not exist uploads\ mkdir uploads
if not exist results\ mkdir results
if not exist controls\ mkdir controls
if not exist static\ mkdir static

echo [BLACKSITE] Starting on http://localhost:%PORT%
echo [BLACKSITE] Open your browser to http://localhost:%PORT%
echo.
uvicorn app.main:app --host %HOST% --port %PORT% --reload

pause
