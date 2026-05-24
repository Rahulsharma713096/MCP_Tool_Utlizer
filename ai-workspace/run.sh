#!/bin/bash
set -e

echo "============================================"
echo "    AI Workspace Platform - Launching..."
echo "============================================"
echo ""

# Set working directory to script location
cd "$(dirname "$0")"

# Environment Validation
echo "[STEP 1/4] Validating environment..."
bash scripts/check_env.sh
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Environment validation failed."
    exit 1
fi
echo ""

# Install Python Dependencies
echo "[STEP 2/4] Installing backend dependencies..."
cd apps/backend
pip install -r requirements.txt -q 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARN] Some packages may not have installed correctly."
else
    echo "[OK] Backend dependencies installed"
fi
cd ../..

# Install Node Dependencies
echo "[STEP 3/4] Installing frontend dependencies..."
cd apps/frontend
if [ ! -d "node_modules" ]; then
    npm install --silent 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "[WARN] Frontend install had issues"
    else
        echo "[OK] Frontend dependencies installed"
    fi
else
    echo "[OK] Frontend dependencies already installed"
fi
cd ../..

# Start Services
echo "[STEP 4/4] Starting services..."
echo ""

# Start Backend
echo "Starting Backend (FastAPI) on port 8000..."
cd apps/backend && python main.py &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 5

# Start Frontend
echo "Starting Frontend (Vite) on port 5173..."
cd apps/frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================"
echo "  AI Workspace Platform is starting up!"
echo ""
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "============================================"
echo ""

# Handle shutdown
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Keep running
wait
