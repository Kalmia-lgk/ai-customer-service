@echo off
chcp 65001 >nul 2>&1
title AI Customer Service Launcher
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo ================================================
echo   AI Customer Service System v2.0
echo ================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.12+ first.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python detected.

pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies - first run, ~1-2 minutes...
    pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install. Check your network.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
)

echo.
echo ================================================
echo   Customer  : http://localhost:8000
echo   Admin     : http://localhost:8000/admin
echo   Login     : admin@aicc.com / admin123
echo   Mode      : Demo (no API key needed)
echo ================================================
echo.

:: Start server in a separate window so we can open browser
cd /d "%~dp0backend"
start "AI-Server" cmd /k "cd /d \"%~dp0backend\" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Wait for server to be ready
echo Waiting for server to start...
timeout /t 6 /nobreak >nul

:: Open browser
start http://localhost:8000
start http://localhost:8000/admin/

echo.
echo Server is starting in another window.
echo Close the AI-Server window to stop.
echo.
pause
