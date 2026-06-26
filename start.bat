@echo off
chcp 65001 >nul 2>&1
title AI Customer Service System
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
    echo [INFO] Installing dependencies - first run...
    pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
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
echo   Mode      : Demo ^(no API key needed^)
echo.
echo   Close this window to stop the server.
echo ================================================
echo.
echo [INFO] Starting server, please wait...
echo.

cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Server stopped.
pause
