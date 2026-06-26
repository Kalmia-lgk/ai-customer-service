@echo off
chcp 65001 >nul 2>&1
title AI Customer Service System
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
setlocal enabledelayedexpansion

echo.
echo ================================================
echo   AI Customer Service System v2.0
echo ================================================
echo.

:: ---- 1. Check Python ----
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.12+ first.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python detected.

:: ---- 2. Install dependencies if needed ----
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies - first run, ~1-2 minutes...
    pip install -r "%~dp0requirements.txt" -q
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install. Check your network and retry.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
)

:: ---- 3. Detect Demo mode ----
set DEMO_MODE=false
findstr /C:"sk-your-" "%~dp0.env" >nul 2>&1
if %errorlevel% equ 0 set DEMO_MODE=true
findstr /C:"gsk_your-" "%~dp0.env" >nul 2>&1
if %errorlevel% equ 0 set DEMO_MODE=true

:: ---- 4. Kill any existing server on port 8000 ----
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING" 2^>nul') do (
    echo [INFO] Stopping old server on port 8000 (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

:: ---- 5. Start server in background ----
cd /d "%~dp0backend"
echo [INFO] Starting server...
start "" /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >nul 2>&1

:: ---- 6. Wait for server to be ready (poll health endpoint) ----
echo [INFO] Waiting for server to be ready...
set TRY=0
:wait_loop
set /a TRY+=1
timeout /t 1 /nobreak >nul

:: Use PowerShell to check if server responds
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto server_ready

if %TRY% lss 30 goto wait_loop

:: Timeout
echo [ERROR] Server failed to start after 30 seconds.
echo.
echo Please check for errors:
echo   1. Is port 8000 already in use?
echo   2. Try running manually: cd backend ^&^& python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
exit /b 1

:server_ready
echo [OK] Server is ready! (took %TRY%s)

:: ---- 7. Show info & open browser ----
echo.
echo ================================================
echo   Customer UI : http://localhost:8000
echo   Admin UI    : http://localhost:8000/admin
echo   Login       : admin@aicc.com / admin123
echo   Mode        : Demo (no API key needed)
echo.
echo   To add real AI: edit .env, replace OPENAI_API_KEY
echo   To stop: close this window
echo ================================================
echo.

start http://localhost:8000
start http://localhost:8000/admin/

echo Server is running. Keep this window open.
echo.
pause
