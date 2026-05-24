# AI Workspace Platform

> Enterprise AI Operations Workspace — manage local LLMs (Ollama), MCP servers, AI providers, and chat with models through a unified dashboard.

---

## Features

- **Ollama Runtime Manager** — Detect, list, start/stop local LLM models with automatic CLI fallback
- **MCP Studio** — Register and manage Model Context Protocol servers (Python, Node.js, npx-based tools)
- **AI Provider Hub** — Connect to OpenRouter, OpenAI, Gemini, and custom providers
- **Chat Interface** — WebSocket-powered streaming chat with session history
- **System Monitoring** — Real-time CPU, RAM, GPU metrics with history tracking
- **Dashboard** — Unified view of models, MCPs, providers, and system health
- **Security** — JWT authentication, rate limiting, command allow-listing, API key encryption

---

## Quick Start

### Prerequisites

| Requirement | Version | Check Command |
|------------|---------|---------------|
| **Python** | 3.11+ | `python --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | 9+ | `npm --version` |
| **Ollama** *(optional)* | latest | `ollama --version` |

### Windows

```batch
cd ai-workspace
run.bat
```

### Linux / macOS

```bash
cd ai-workspace
chmod +x run.sh scripts/check_env.sh
./run.sh
```

### Manual Setup

```bash
# Backend
cd ai-workspace/apps/backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py

# Frontend (second terminal)
cd ai-workspace/apps/frontend
npm install
npm run dev
```

---

## API Reference

All API endpoints are prefixed with `/api/v1`. Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

### Health & System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Comprehensive health check (Ollama, DB, MCPs, providers) |
| GET | `/health/runtime` | Runtime health metrics |
| GET | `/health/mcp` | MCP subsystem health |
| GET | `/health/providers` | Provider subsystem health |
| GET | `/system/info` | System information (CPU, RAM, disk, GPU) |
| GET | `/system/metrics` | Current system metrics |
| GET | `/system/metrics/history` | Metrics history (default: 5 min) |

### Ollama Models

| Method | Endpoint | Description |
|--------|----------|-------------|
| **GET** | **`/ollama/detect`** | **Detect Ollama installation** |
| GET | `/ollama/models` | List installed models |
| POST | `/ollama/models/start` | Start a model runtime |
| POST | `/ollama/models/stop` | Stop a model runtime |
| GET | `/ollama/models/{name}/runtime` | Model runtime info |
| POST | `/ollama/kill-all` | Kill all Ollama processes |

### MCP Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mcps` | Register a new MCP server |
| DELETE | `/mcps/{id}` | Delete an MCP server |
| POST | `/mcps/{id}/enable` | Enable (start) an MCP server |
| POST | `/mcps/{id}/disable` | Disable (stop) an MCP server |
| GET | `/mcps/{id}/test` | Test MCP connectivity |
| GET | `/mcps/{id}/logs` | Get MCP server logs |

### Providers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/providers` | List configured providers |
| POST | `/providers` | Add a provider |
| DELETE | `/providers/{name}` | Delete a provider |
| POST | `/providers/test` | Test provider connection |
| GET | `/providers/{name}/models` | List provider models |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/session` | Create a chat session |
| POST | `/chat/send` | Send a message |
| GET | `/chat/history/{session_id}` | Get session history |
| DELETE | `/chat/session/{session_id}` | Delete a session |
| WS | `/chat/ws` | WebSocket streaming chat |

### Runtime & Config

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/runtime/cleanup` | Clean up zombie processes |
| GET | `/runtime/resource-check` | Check resource limits |
| POST | `/runtime/monitoring/start` | Start background monitoring |
| POST | `/runtime/monitoring/stop` | Stop background monitoring |
| GET | `/config/ui` | Get UI configuration |
| POST | `/config/ui` | Update UI configuration |
| GET | `/config/runtime` | Get runtime configuration |
| POST | `/config/runtime` | Update runtime configuration |

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Authenticate and get token |
| POST | `/auth/verify` | Verify an access token |

---

## Running Tests

### Backend Tests (152 test cases)

```bash
cd ai-workspace
python -m pytest tests/backend/ -v --tb=short
```

Covers: sanity (10), security (9), database (10), providers (10), MCP (12), Ollama (12), chat (10), data flow (12), recovery (5), performance (9), API integration (3), deployment logic (50)

### Frontend Tests (20 test cases)

```bash
cd ai-workspace/apps/frontend
npx vitest run --reporter verbose
```

Covers: Dashboard, Chat, MCP Studio, Ollama Manager components

### TypeScript Check

```bash
cd ai-workspace/apps/frontend
npx tsc --noEmit
```

### Deployment Checks (37 checks)

```bash
cd ai-workspace
python tests/deployment_checks.py
```

Expected result: **37 passed, 0 failed** — confirms production readiness.

---

## Project Architecture

```
ai-workspace/
├── apps/
│   ├── backend/                    # FastAPI Python backend (port 8000)
│   │   ├── api/
│   │   │   └── routes.py           # All REST & WebSocket endpoints
│   │   ├── config/
│   │   │   └── settings.py         # Pydantic settings (env-based)
│   │   ├── core/
│   │   │   ├── logging.py          # Structured logging
│   │   │   └── security.py         # JWT, API key encryption
│   │   ├── models/
│   │   │   ├── database.py         # SQLAlchemy models
│   │   │   └── schemas.py          # Pydantic request/response schemas
│   │   └── services/
│   │       ├── ollama_service.py   # Ollama detection, model lifecycle, CLI fallback
│   │       ├── mcp_service.py      # MCP server registration & execution
│   │       ├── provider_service.py # AI provider management (OpenRouter, etc.)
│   │       ├── chat_service.py     # Chat sessions, streaming
│   │       └── runtime_service.py  # System metrics, process monitoring
│   └── frontend/                   # React + TypeScript + Vite (port 5173)
│       └── src/
│           ├── components/         # Reusable UI components
│           │   └── __tests__/      # Component tests (Vitest + jsdom)
│           ├── pages/              # Page components
│           │   ├── Dashboard.tsx
│           │   ├── Chat.tsx
│           │   ├── MCPStudio.tsx
│           │   └── OllamaManager.tsx
│           ├── store/              # Zustand state management
│           └── lib/                # Utilities (apiFetch, etc.)
├── tests/
│   ├── backend/                    # 14 test files — 152 total tests
│   └── deployment_checks.py        # 37 production readiness checks
├── configs/                        # JSON configuration files
├── scripts/                        # Environment validation scripts
├── data/                           # SQLite database (auto-created)
├── logs/                           # Application logs (auto-created)
├── mcps/                           # MCP server directory
├── run.bat                         # Windows launcher
├── run.sh                          # Linux/Mac launcher
└── .env.example                    # Environment template
```

---

## Ollama Configuration

The app auto-detects Ollama via:
1. **HTTP API** — `http://localhost:11434/api/tags` (default, quickest)
2. **CLI fallback** — `ollama list` command (used when API is unreachable)

Both require Ollama to be running. Start it with:

```bash
ollama serve          # Start Ollama background service
ollama pull llama3.2  # Download a model
ollama list           # Verify models are available
```

Configure the API host in `.env`:
```ini
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=300
```

---

## Troubleshooting

### Ollama not detected / 500 on `/api/v1/ollama/detect`

```bash
# 1. Verify Ollama is installed and in PATH
ollama --version

# 2. Verify Ollama API is running
curl http://localhost:11434/api/tags

# 3. Restart the backend
cd ai-workspace/apps/backend && python main.py

# 4. Check logs
cat logs/app.log | findstr ollama
```

### Port already in use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### Module not found

```bash
cd ai-workspace/apps/backend
pip install -r requirements.txt
```

---

## Environment Variables

```ini
APP_NAME=AI Workspace
APP_VERSION=1.0.0
DEBUG=true
ENV=development

HOST=0.0.0.0
PORT=8000

DATABASE_URL=sqlite+aiosqlite:///./data/ai_workspace.db

SECRET_KEY=generate-a-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=300

CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
RATE_LIMIT=100/minute
```

---

## Support

- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Specification:** See `SRS.txt`, `test.txt`, `c.txt` in project root
