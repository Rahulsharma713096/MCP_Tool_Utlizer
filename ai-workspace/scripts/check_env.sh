#!/bin/bash
set -e

echo "============================================"
echo "  AI Workspace - Environment Validator"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check() {
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}[OK]${NC} $1"
    else
        echo -e "  ${RED}[FAIL]${NC} $1"
    fi
}

# Check Python
echo "[1/6] Checking Python..."
if command -v python3 &> /dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}[OK]${NC} Python $PY_VER"
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
    if [ $? -ne 0 ]; then
        echo -e "  ${RED}[FAIL]${NC} Python 3.11+ required"
        exit 1
    fi
else
    echo -e "  ${RED}[FAIL]${NC} Python is not installed"
    exit 1
fi

# Check Node.js
echo "[2/6] Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VER=$(node --version)
    echo -e "  ${GREEN}[OK]${NC} Node.js $NODE_VER"
else
    echo -e "  ${RED}[FAIL]${NC} Node.js is not installed"
    exit 1
fi

# Check Ollama
echo "[3/6] Checking Ollama..."
if command -v ollama &> /dev/null; then
    OLLAMA_VER=$(ollama --version)
    echo -e "  ${GREEN}[OK]${NC} $OLLAMA_VER"
else
    echo -e "  ${YELLOW}[WARN]${NC} Ollama not installed"
fi

# Check GPU
echo "[4/6] Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>&1 | head -1)
    echo -e "  ${GREEN}[OK]${NC} GPU: $GPU_NAME"
else
    echo -e "  ${YELLOW}[INFO]${NC} No NVIDIA GPU detected"
fi

# Check Ports
echo "[5/6] Checking port availability..."
python3 -c "
import socket
for port in [8000, 5173]:
    with socket.socket() as s:
        if s.connect_ex(('localhost', port)) == 0:
            print(f'WARN: Port {port} in use')
        else:
            print(f'OK: Port {port} available')
"

# Check Disk Space
echo "[6/6] Checking disk space..."
FREE_SPACE=$(df -h / | awk 'NR==2 {print $4}')
echo -e "  ${GREEN}[OK]${NC} Free space: $FREE_SPACE"

echo ""
echo "============================================"
echo "  Environment validation complete!"
echo "============================================"
