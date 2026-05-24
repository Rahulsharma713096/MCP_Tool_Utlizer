# AI Workspace Platform - Run My Code

> Complete setup guide for first-time users. Run this project from scratch on Windows, Linux, or macOS.

---

## 1. Prerequisites

| Requirement | Version | Check Command | Download |
|------------|---------|---------------|----------|
| **Python** | 3.11+ | `python --version` | [python.org](https://python.org) |
| **Node.js** | 18+ | `node --version` | [nodejs.org](https://nodejs.org) |
| **npm** | 9+ | `npm --version` | (comes with Node.js) |
| **Ollama** *(optional)* | latest | `ollama --version` | [ollama.com](https://ollama.com/download) |

### Optional but recommended:
- **NVIDIA GPU** with CUDA for GPU-accelerated model inference
- **Git** for version control

---

## 2. Quick Start (Windows)

Open **Command Prompt** or **PowerShell** and run:

```batch
# 1. Navigate to the project
cd ai-workspace

# 2. Run the platform (auto-installs dependencies & starts services)
run.bat
```

That's it! The script will:
- Validate your environment (Python, Node.js, ports)
- Install backend Python packages
- Install frontend Node.js packages
- Start the backend API server (port 8000)
- Start the frontend dev server (port 5173)

---

## 3. Quick Start (Linux / macOS)

Open **Terminal** and run:

```bash
# 1. Navigate to the project
cd ai-workspace

# 2. Make scripts executable (first time only)
chmod +x run.sh scripts/check_env.sh

# 3. Run the platform
./run.sh
```

---

## 4. Manual Step-by-Step Setup

If the automated scripts don't work, or you prefer manual control:

### 4.1 Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your settings (optional for development)
# Minimum: SECRET_KEY should be unique per deployment
```

### 4.2 Backend Setup

```bash
cd ai-workspace/apps/backend

# Create virtual environment (recommended)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server
python main.py
```

The backend starts at **http://localhost:8000** with auto-reload in development mode.

### 4.3 Frontend Setup

Open a **second terminal**:

```bash
cd ai-workspace/apps/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend starts at **http://localhost:5173** and auto-proxies `/api` requests to the backend.

---

## 5. Running Tests

### Backend Tests (98 test cases)

```bash
cd ai-workspace

# Run all tests
python -m pytest tests/backend/ -v

# Run specific test file
python -m pytest tests/backend/test_security.py -v

# Run with coverage report
python -m pytest tests/backend/ --cov=apps/backend --cov-report=term
```

### Deployment Checks (35 checks)

```bash
cd ai-workspace
python tests/deployment_checks.py
```

Expected result: **35 passed, 0 failed** — confirms the project is production-ready.

---

## 6. Accessing the Application

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend UI** | http://localhost:5173 | Web interface (Dashboard, Chat, MCP Studio, etc.) |
| **Backend API** | http://localhost:8000 | REST API endpoints |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive API documentation |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | Alternative API docs |

---

## 7. Project Architecture

```
ai-workspace/
├── apps/
│   ├── backend/          # FastAPI Python backend
│   │   ├── api/          # REST API routes
│   │   ├── config/       # Settings & configuration
│   │   ├── core/         # Security, logging
│   │   ├── models/       # Database schemas
│   │   └── services/     # Business logic (Ollama, MCP, Chat, etc.)
│   └── frontend/         # React + TypeScript frontend
│       ├── src/
│       │   ├── components/  # Reusable UI components
│       │   ├── pages/       # Page-level components
│       │   ├── store/       # State management (Zustand)
│       │   └── lib/         # Utilities
│       └── public/          # Static assets
├── configs/              # JSON configuration files
├── scripts/              # Environment validation scripts
├── tests/                # Test suite
│   ├── backend/          # 7 test files (98 tests total)
│   └── deployment_checks.py  # 35 deployment checks
├── logs/                 # Application logs (auto-created)
├── mcps/                 # MCP server directory
├── data/                 # SQLite database (auto-created)
├── run.bat               # Windows launcher
├── run.sh                # Linux/Mac launcher
└── .env.example          # Environment template
```

---

## 8. Configuration Reference

### `.env` File

```ini
# --- Application ---
APP_NAME=AI Workspace
APP_VERSION=1.0.0
DEBUG=true                     # Enable for development
ENV=development                # Switch to "production" for deployment

# --- Server ---
HOST=0.0.0.0                   # Listen on all interfaces
PORT=8000                      # Backend API port

# --- Database ---
# SQLite (default - no setup required):
DATABASE_URL=sqlite+aiosqlite:///./data/ai_workspace.db

# --- Security (CHANGE THESE IN PRODUCTION!) ---
SECRET_KEY=your-random-secret-key-here   # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# --- Ollama (Local LLMs) ---
OLLAMA_HOST=http://localhost:11434

# --- CORS ---
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# --- Rate Limiting ---
RATE_LIMIT=100/minute
```

### JSON Configs (`configs/`)

| File | Purpose |
|------|---------|
| `providers.json` | Online AI provider definitions (OpenRouter, OpenAI, Gemini) |
| `runtime.json` | Model runtime configuration |
| `ui.json` | UI theme & layout settings |
| `mcp_registry.json` | MCP server registry entries |

---

## 9. Using with Ollama (Local LLMs)

1. **Install Ollama** from [ollama.com/download](https://ollama.com/download)
2. **Pull a model** (in a terminal):
   ```bash
   ollama pull llama3.2
   ollama pull mistral
   ```
3. **Start Ollama** (it runs as a background service):
   ```bash
   ollama serve
   ```
4. **Verify** — Ollama is reachable at http://localhost:11434
5. **Use in the app** — Select "Ollama" as the provider and choose your model from the Chat page

---

## 10. Troubleshooting

### "Python not found"
- Install Python 3.11+ from [python.org](https://python.org)
- Ensure "Add Python to PATH" is checked during installation
- Restart your terminal

### "pip: command not found"
```bash
python -m pip install -r requirements.txt
```

### "ModuleNotFoundError"
```bash
cd ai-workspace/apps/backend
pip install -r requirements.txt
```

### "Port 8000 already in use"
```bash
# Find the process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :8000
kill -9 <PID>
```

### Frontend blank page / API errors
- Ensure the **backend** is running first (port 8000)
- Check the browser console for CORS errors
- The frontend dev server proxies `/api/*` to `http://localhost:8000`

### "sqlalchemy.exc.OperationalError"
```bash
# The data directory should be auto-created. If not:
mkdir -p ai-workspace/data
```

### "Ollama is not running"
- Start Ollama: `ollama serve`
- Or run it as a background service
- The app will still work — it just shows a warning when Ollama is unreachable

---

## 11. Quick Validation Commands

Run these to verify everything is working:

```bash
# 1. Check Python
python --version                    # Should be 3.11+

# 2. Check Node.js
node --version                      # Should be 18+

# 3. Install backend deps
cd ai-workspace/apps/backend
pip install -r requirements.txt

# 4. Install frontend deps
cd ai-workspace/apps/frontend
npm install

# 5. Run tests (should be 98 passed)
cd ai-workspace
python -m pytest tests/backend/ -v --tb=short

# 6. Run deployment checks (should be 35 passed)
python tests/deployment_checks.py

# 7. Start the app
# Windows: double-click run.bat
# Linux/Mac: ./run.sh
```

---

## 12. Stopping the Application

- **Windows:** Close the terminal windows or press `Ctrl+C`
- **Linux/Mac:** Press `Ctrl+C` in the terminal where you ran `run.sh`

---

## Support

For issues, check the [docs](http://localhost:8000/docs) when the app is running, or refer to `SRS.txt`, `test.txt`, and `c.txt` in the project root for the original specification and requirements.
