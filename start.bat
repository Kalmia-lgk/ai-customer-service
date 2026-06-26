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
    echo [INFO] Installing dependencies - first run, ~1-2 minutes...
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install. Check your network and retry.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
)

findstr /C:"sk-your-" .env >nul 2>&1
if %errorlevel% equ 0 set DEMO_MODE=true
findstr /C:"gsk_your-" .env >nul 2>&1
if %errorlevel% equ 0 set DEMO_MODE=true

echo.
echo ================================================
echo   Customer  : http://localhost:8000
echo   Admin     : http://localhost:8000/admin
echo   Login     : admin@aicc.com / admin123
echo.
echo   Mode: Demo (no API key needed)
echo   Add real AI: edit .env, replace OPENAI_API_KEY
echo   Stop: close this window
echo ================================================
echo.

cd /d "%~dp0backend"

:: Start server in a new window
start "AI-Server" cmd /c "cd /d \"%~dp0backend\" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 && pause"

:: Wait for server to start
echo Waiting for server to be ready...
timeout /t 8 /nobreak >nul

:: Open browser
start http://localhost:8000
start http://localhost:8000/admin/

echo.
echo Server is running. Keep this window open.
echo To stop: close this window.
echo.
pause
