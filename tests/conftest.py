"""Pytest configuration and fixtures for backend API testing."""

import sys
import os
import json
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient

# ── Add backend source to path ──
BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'ai-workspace', 'apps', 'backend')
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

# ── Override settings BEFORE any app imports ──
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_data/test.db")


# ══════════════════════════════════════════
# Mock Factory Helpers
# ══════════════════════════════════════════

def make_mock_ollama_service():
    """Create a fully mocked OllamaService instance."""
    mock = MagicMock()
    
    mock.detect_ollama = AsyncMock(return_value=True)
    mock.get_ollama_version = AsyncMock(return_value="0.3.0")
    mock.list_models = AsyncMock(return_value=[
        {"name": "llama3:latest", "size": 4700000000, "quantization": "Q4_K_M", "modified_at": "2024-01-01T00:00:00Z"},
        {"name": "mistral:latest", "size": 4100000000, "quantization": "Q4_K_M", "modified_at": "2024-01-01T00:00:00Z"},
    ])
    mock.start_model = AsyncMock(return_value={"status": "started", "model": "llama3:latest", "pid": 12345})
    mock.stop_model = AsyncMock(return_value={"status": "stopped", "model": "llama3:latest"})
    mock.get_model_runtime_info = AsyncMock(return_value={
        "name": "llama3:latest", "running": True, "cpu_percent": 5.0, "ram_mb": 256.0, "pid": 12345
    })
    mock.kill_all_processes = AsyncMock(return_value={"status": "cleaned", "killed_count": 0})
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    mock.running_processes = {}
    
    return mock


def make_mock_mcp_service():
    """Create a fully mocked MCPService instance."""
    mock = MagicMock()
    
    mock.register_mcp = AsyncMock(return_value={"status": "registered", "mcp": {"name": "test-mcp"}})
    mock.delete_mcp = AsyncMock(return_value={"status": "deleted", "id": 1})
    mock.enable_mcp = AsyncMock(return_value={"status": "started", "id": 1, "pid": 54321})
    mock.disable_mcp = AsyncMock(return_value={"status": "stopped", "id": 1})
    mock.stop_mcp = AsyncMock(return_value={"status": "stopped", "id": 1})
    mock.test_mcp = AsyncMock(return_value={"status": "healthy"})
    mock.get_mcp_logs = AsyncMock(return_value=["MCP running", "Tool loaded"])
    mock.list_tools = AsyncMock(return_value=[])
    mock.get_all_enabled_tools = AsyncMock(return_value=[])
    mock.execute_tool = AsyncMock(return_value={"status": "success", "result": "done"})
    mock.cleanup_all = AsyncMock(return_value=None)
    
    mock.running_mcps = {}
    mock._mcp_info = {}
    mock._tool_cache = {}
    
    return mock


def make_mock_provider_service():
    """Create a fully mocked ProviderService instance."""
    mock = MagicMock()
    
    mock.get_provider = MagicMock(return_value=MagicMock())
    mock.remove_provider = MagicMock(return_value=None)
    mock.test_connection = AsyncMock(return_value={"status": "healthy", "latency_ms": 42.0})
    mock.instances = {}
    
    return mock


def make_mock_chat_service():
    """Create a fully mocked ChatService instance."""
    mock = MagicMock()
    
    mock.create_session = MagicMock(return_value="test-session-id")
    mock.send_message = AsyncMock(return_value={
        "session_id": "test-session-id",
        "response": "Hello! How can I help you?",
        "provider": "ollama",
        "model": "llama3",
        "tool_events": [],
    })
    mock.get_session_history = MagicMock(return_value=[
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello! How can I help you?"},
    ])
    mock.delete_session = MagicMock(return_value=None)
    mock.stream_message = AsyncMock()
    mock.sessions = {}
    
    return mock


def make_mock_runtime_service():
    """Create a fully mocked RuntimeService instance."""
    mock = MagicMock()
    
    mock.get_system_info = AsyncMock(return_value={
        "platform": "test",
        "python_version": "3.14.5",
        "hostname": "test-host",
        "processor": "x86_64",
        "cpus": 8,
        "total_ram_gb": 16.0,
        "available_ram_gb": 8.0,
        "total_disk_gb": 256.0,
        "free_disk_gb": 128.0,
        "gpu_available": False,
        "gpu_name": None,
    })
    mock.get_current_metrics = AsyncMock(return_value={
        "cpu_percent": 25.0,
        "ram_percent": 50.0,
        "ram_used_gb": 8.0,
        "ram_total_gb": 16.0,
        "gpu_percent": None,
        "vram_used_gb": None,
        "active_models": 1,
        "active_mcps": 0,
        "token_throughput": None,
        "timestamp": "2024-01-01T00:00:00Z",
    })
    mock.get_metrics_history = AsyncMock(return_value=[
        {"cpu_percent": 25.0, "ram_percent": 50.0, "timestamp": "2024-01-01T00:00:00Z"}
    ])
    mock.cleanup_zombie_processes = AsyncMock(return_value={"cleaned": 0, "pids": []})
    mock.check_resource_limits = AsyncMock(return_value={
        "safe": True,
        "warnings": [],
        "metrics": {"cpu_percent": 25.0, "ram_percent": 50.0},
    })
    mock.start_monitoring = AsyncMock(return_value=None)
    mock.stop_monitoring = MagicMock(return_value=None)
    
    return mock


# ══════════════════════════════════════════
# App & Client Fixtures
# ══════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Set up test environment once per session."""
    # Create temp test data directory
    test_data_dir = os.path.join(os.path.dirname(__file__), '..', 'ai-workspace', 'apps', 'backend', 'test_data')
    os.makedirs(test_data_dir, exist_ok=True)
    
    yield
    
    # Cleanup test data
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir, ignore_errors=True)


@pytest.fixture
def app():
    """Create the FastAPI application with mocked services."""
    from main import app as fastapi_app
    from api.routes import ollama_service, mcp_service, provider_service, chat_service, runtime_service
    
    # Replace real services with mocks
    mock_ollama = make_mock_ollama_service()
    mock_mcp = make_mock_mcp_service()
    mock_provider = make_mock_provider_service()
    mock_chat = make_mock_chat_service()
    mock_runtime = make_mock_runtime_service()
    
    # Patch services on the routes module
    import api.routes as routes_module
    routes_module.ollama_service = mock_ollama
    routes_module.mcp_service = mock_mcp
    routes_module.provider_service = mock_provider
    routes_module.chat_service = mock_chat
    routes_module.runtime_service = mock_runtime
    
    # Also store mocks on app for test access
    fastapi_app.state.mock_ollama = mock_ollama
    fastapi_app.state.mock_mcp = mock_mcp
    fastapi_app.state.mock_provider = mock_provider
    fastapi_app.state.mock_chat = mock_chat
    fastapi_app.state.mock_runtime = mock_runtime
    
    return fastapi_app


@pytest.fixture
def client(app) -> Generator:
    """Create test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_ollama(app):
    """Get the mocked ollama service."""
    return app.state.mock_ollama


@pytest.fixture
def mock_mcp(app):
    """Get the mocked mcp service."""
    return app.state.mock_mcp


@pytest.fixture
def mock_provider(app):
    """Get the mocked provider service."""
    return app.state.mock_provider


@pytest.fixture
def mock_chat(app):
    """Get the mocked chat service."""
    return app.state.mock_chat


@pytest.fixture
def mock_runtime(app):
    """Get the mocked runtime service."""
    return app.state.mock_runtime
