@echo off
title AI Workspace Platform
mode con: cols=100 lines=30

echo ============================================
echo     AI Workspace Platform - Launching...
echo ============================================
echo.

:: Set working directory to script location
cd /d "%~dp0"

:: Environment Validation
echo [STEP 1/4] Validating environment...
call scripts\check_env.bat
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Environment validation failed.
    echo Please fix the issues above and try again.
    pause
    exit /b 1
)
echo.

:: Install Python Dependencies
echo [STEP 2/4] Installing backend dependencies...
cd apps\backend
pip install -r requirements.txt >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARN] Some packages may not have installed correctly.
) else (
    echo [OK] Backend dependencies installed
)
cd ..\..

:: Install Node Dependencies
echo [STEP 3/4] Installing frontend dependencies...
cd apps\frontend
if not exist "node_modules" (
    npm install >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [WARN] Frontend install had issues
    ) else (
        echo [OK] Frontend dependencies installed
    )
) else (
    echo [OK] Frontend dependencies already installed
)
cd ..\..

:: Start Services
echo [STEP 4/4] Starting services...
echo.

:: Start Backend
echo Starting Backend (FastAPI) on port 8000...
start "AI-Workspace-Backend" cmd /k "cd apps\backend && python main.py"

:: Wait for backend to start
timeout /t 5 /nobreak >nul

:: Start Frontend
echo Starting Frontend (Vite) on port 5173...
start "AI-Workspace-Frontend" cmd /k "cd apps\frontend && npm run dev"

echo.
echo ============================================
echo   AI Workspace Platform is starting up!
echo.
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Close this window to shut down all services.
echo.

:: Keep window open
pause
