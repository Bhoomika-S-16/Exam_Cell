@echo off
echo ============================================
echo   EXAM ATTENDANCE SYSTEM - Startup Script
echo ============================================
echo.

cd /d "%~dp0"

:: Check if virtual environment exists
if exist .venv\Scripts\activate.bat (
    echo Virtual environment found. Activating...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment (.venv) not found. Using system Python.
)

echo.
echo Installing dependencies...
python -m pip install -r backend/requirements.txt
echo.

echo Starting server...
echo   Admin:       http://localhost:8000/login.html
echo   Invigilator: http://localhost:8000/invigilator.html
echo.

python backend/main.py
pause
