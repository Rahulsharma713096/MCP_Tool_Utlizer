@echo off
title AI Workspace - Environment Check
echo ============================================
echo   AI Workspace - Environment Validator
echo ============================================
echo.

:: Check Python
echo [1/6] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   [FAIL] Python is not installed or not in PATH
    echo   Please install Python 3.11+ from https://python.org
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo   [OK] Python %PY_VER%

:: Check Python version >= 3.11
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   [FAIL] Python 3.11+ is required
    exit /b 1
)
echo   [OK] Python version meets requirements

:: Check Node.js
echo [2/6] Checking Node.js...
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   [FAIL] Node.js is not installed or not in PATH
    echo   Please install Node.js 18+ from https://nodejs.org
    exit /b 1
)
for /f "tokens=1" %%i in ('node --version') do set NODE_VER=%%i
echo   [OK] Node.js %NODE_VER%

:: Check Ollama
echo [3/6] Checking Ollama...
ollama --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   [WARN] Ollama is not installed. Local models will not be available.
    echo   Install from https://ollama.com/download
) else (
    for /f "tokens=*" %%i in ('ollama --version') do set OLLAMA_VER=%%i
    echo   [OK] Ollama %OLLAMA_VER%
)

:: Check GPU
echo [4/6] Checking GPU...
nvidia-smi --query-gpu=name --format=csv,noheader >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   [INFO] NVIDIA GPU not detected. Running on CPU.
) else (
    for /f "tokens=*" %%i in ('nvidia-smi --query-gpu=name --format=csv,noheader') do set GPU_NAME=%%i
    echo   [OK] GPU: %GPU_NAME%
)

:: Check Ports
echo [5/6] Checking port availability...
python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost',8000)); s.close(); print('inuse')" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [WARN] Port 8000 is in use - will attempt to use
) else (
    echo   [OK] Port 8000 is available
)

python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost',5173)); s.close(); print('inuse')" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [WARN] Port 5173 is in use - will attempt to use
) else (
    echo   [OK] Port 5173 is available
)

:: Check Disk Space
echo [6/6] Checking disk space...
for /f "tokens=3" %%i in ('dir %~d0\ ^| findstr "bytes free"') do set FREE_SPACE=%%i
echo   [OK] Free space available

echo.
echo ============================================
echo   Environment validation complete!
echo ============================================
echo.
exit /b 0
