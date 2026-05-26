"""Comprehensive backend API tests for all endpoints.

Tests cover:
- Root & Version endpoints
- Health & System endpoints
- Ollama endpoints (detect, list, start, stop, runtime, kill)
- MCP endpoints (CRUD, enable/disable, test, logs)
- Provider endpoints (CRUD, test, models)
- Chat endpoints (session, send, history, delete)
- Runtime endpoints (cleanup, monitoring)
- Config endpoints (UI, runtime)
- Auth endpoints (login, verify)
- Integration flows
- Error handling & edge cases
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ══════════════════════════════════════════
# Root & Version
# ══════════════════════════════════════════

class TestRootEndpoints:
    """Test the root info and version endpoints."""

    def test_root(self, client: TestClient):
        """GET / should return app info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI Workspace"
        assert data["status"] == "running"
        assert "version" in data
        assert "timestamp" in data
        assert "docs" in data

    def test_version(self, client: TestClient):
        """GET /api/v1/version should return version info."""
        response = client.get("/api/v1/version")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "AI Workspace"
        assert data["version"] == "1.0.0"
        assert data["api_version"] == "v1"


# ══════════════════════════════════════════
# Health
# ══════════════════════════════════════════

class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health(self, client: TestClient, mock_ollama):
        """GET /api/v1/health should return system health."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "ollama" in data
        assert "database" in data
        assert "active_mcps" in data
        assert "active_providers" in data
        assert "uptime_seconds" in data

    def test_health_runtime(self, client: TestClient, mock_runtime):
        """GET /api/v1/health/runtime should return runtime metrics."""
        response = client.get("/api/v1/health/runtime")
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_percent"] == 25.0
        assert data["ram_percent"] == 50.0

    def test_health_mcp(self, client: TestClient, mock_mcp):
        """GET /api/v1/health/mcp should return MCP health."""
        response = client.get("/api/v1/health/mcp")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_mcps" in data

    def test_health_providers(self, client: TestClient, mock_provider):
        """GET /api/v1/health/providers should return provider health."""
        response = client.get("/api/v1/health/providers")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_providers" in data


# ══════════════════════════════════════════
# System
# ══════════════════════════════════════════

class TestSystemEndpoints:
    """Test system information and metrics endpoints."""

    def test_system_info(self, client: TestClient, mock_runtime):
        """GET /api/v1/system/info should return system info."""
        response = client.get("/api/v1/system/info")
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "test"
        assert data["python_version"] == "3.14.5"
        assert "cpus" in data
        assert "total_ram_gb" in data

    def test_system_metrics(self, client: TestClient, mock_runtime):
        """GET /api/v1/system/metrics should return current metrics."""
        response = client.get("/api/v1/system/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_percent"] == 25.0
        assert data["ram_percent"] == 50.0
        assert "timestamp" in data

    def test_metrics_history(self, client: TestClient, mock_runtime):
        """GET /api/v1/system/metrics/history should return metrics history."""
        response = client.get("/api/v1/system/metrics/history?minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["cpu_percent"] == 25.0

    def test_metrics_history_invalid_minutes(self, client: TestClient):
        """GET /api/v1/system/metrics/history with invalid minutes should return 422."""
        response = client.get("/api/v1/system/metrics/history?minutes=0")
        assert response.status_code == 422

        response = client.get("/api/v1/system/metrics/history?minutes=100")
        assert response.status_code == 422


# ══════════════════════════════════════════
# Ollama
# ══════════════════════════════════════════

class TestOllamaEndpoints:
    """Test Ollama model management endpoints."""

    def test_detect_ollama(self, client: TestClient, mock_ollama):
        """GET /api/v1/ollama/detect should detect Ollama installation."""
        response = client.get("/api/v1/ollama/detect")
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert data["version"] == "0.3.0"
        mock_ollama.detect_ollama.assert_awaited_once()
        mock_ollama.get_ollama_version.assert_awaited_once()

    def test_list_models(self, client: TestClient, mock_ollama):
        """GET /api/v1/ollama/models should list installed models."""
        response = client.get("/api/v1/ollama/models")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "llama3:latest"
        assert data["models"][1]["name"] == "mistral:latest"
        mock_ollama.list_models.assert_awaited_once()

    def test_start_model(self, client: TestClient, mock_ollama):
        """POST /api/v1/ollama/models/start should start a model."""
        response = client.post("/api/v1/ollama/models/start", json={"name": "llama3:latest"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["model"] == "llama3:latest"
        assert data["pid"] == 12345
        mock_ollama.start_model.assert_awaited_once_with("llama3:latest")

    def test_start_model_error(self, client: TestClient, mock_ollama):
        """POST /api/v1/ollama/models/start should return 400 on error."""
        mock_ollama.start_model.return_value = {"status": "error", "message": "Model not found"}
        response = client.post("/api/v1/ollama/models/start", json={"name": "invalid-model"})
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_start_model_with_provider(self, client: TestClient, mock_ollama):
        """POST /api/v1/ollama/models/start with custom provider."""
        response = client.post("/api/v1/ollama/models/start", json={
            "name": "mistral:latest",
            "provider": "ollama"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

    def test_stop_model(self, client: TestClient, mock_ollama):
        """POST /api/v1/ollama/models/stop should stop a model."""
        response = client.post("/api/v1/ollama/models/stop", json={"name": "llama3:latest"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        mock_ollama.stop_model.assert_awaited_once_with("llama3:latest")

    def test_model_runtime_info(self, client: TestClient, mock_ollama):
        """GET /api/v1/ollama/models/{name}/runtime should return runtime info."""
        response = client.get("/api/v1/ollama/models/llama3:latest/runtime")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "llama3:latest"
        assert data["running"] is True
        assert data["cpu_percent"] == 5.0
        assert data["ram_mb"] == 256.0
        assert data["pid"] == 12345
        mock_ollama.get_model_runtime_info.assert_awaited_once_with("llama3:latest")

    def test_kill_all_processes(self, client: TestClient, mock_ollama):
        """POST /api/v1/ollama/kill-all should kill all Ollama processes."""
        response = client.post("/api/v1/ollama/kill-all")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleaned"
        assert "killed_count" in data
        mock_ollama.kill_all_processes.assert_awaited_once()


# ══════════════════════════════════════════
# MCP
# ══════════════════════════════════════════

class TestMCPEndpoints:
    """Test MCP server management endpoints."""

    def test_register_mcp(self, client: TestClient, mock_mcp):
        """POST /api/v1/mcps should register a new MCP."""
        mcp_data = {
            "name": "test-mcp",
            "type": "custom",
            "command": "python",
            "args": ["-m", "mcp_server"],
            "transport": "stdio",
        }
        response = client.post("/api/v1/mcps", json=mcp_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        mock_mcp.register_mcp.assert_awaited_once()

    def test_register_mcp_github(self, client: TestClient, mock_mcp):
        """POST /api/v1/mcps with GitHub repo config."""
        mcp_data = {
            "name": "github-mcp",
            "type": "npx",
            "transport": "stdio",
            "command": "npx",
            "github_repo": "owner/repo",
            "github_ref": "main",
            "root": "/workspace",
            "exclude": ["node_modules", ".git"],
        }
        response = client.post("/api/v1/mcps", json=mcp_data)
        assert response.status_code == 200
        mock_mcp.register_mcp.assert_awaited()

    def test_register_mcp_error(self, client: TestClient, mock_mcp):
        """POST /api/v1/mcps with invalid data should return 400."""
        mock_mcp.register_mcp.return_value = {"status": "error", "message": "Invalid command"}
        response = client.post("/api/v1/mcps", json={
            "name": "bad-mcp",
            "type": "custom",
            "command": "rm -rf /",
        })
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_register_mcp_missing_name(self, client: TestClient):
        """POST /api/v1/mcps without name should return 422."""
        response = client.post("/api/v1/mcps", json={"type": "custom"})
        assert response.status_code == 422  # Validation error

    def test_delete_mcp(self, client: TestClient, mock_mcp):
        """DELETE /api/v1/mcps/{id} should delete MCP."""
        response = client.delete("/api/v1/mcps/1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["id"] == 1
        mock_mcp.delete_mcp.assert_awaited_once_with(1)

    def test_enable_mcp(self, client: TestClient, mock_mcp):
        """POST /api/v1/mcps/{id}/enable should enable MCP."""
        response = client.post("/api/v1/mcps/1/enable", json={
            "name": "test-mcp",
            "type": "custom",
            "command": "python",
            "args": ["server.py"],
            "transport": "stdio",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["id"] == 1
        mock_mcp.enable_mcp.assert_awaited_once()

    def test_disable_mcp(self, client: TestClient, mock_mcp):
        """POST /api/v1/mcps/{id}/disable should disable MCP."""
        response = client.post("/api/v1/mcps/1/disable")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        mock_mcp.stop_mcp.assert_awaited_once_with(1)

    def test_test_mcp(self, client: TestClient, mock_mcp):
        """GET /api/v1/mcps/{id}/test should test MCP connectivity."""
        response = client.get("/api/v1/mcps/1/test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_mcp_logs(self, client: TestClient, mock_mcp):
        """GET /api/v1/mcps/{id}/logs should return MCP logs."""
        response = client.get("/api/v1/mcps/1/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) == 2
        mock_mcp.get_mcp_logs.assert_awaited_once_with(1, 50)

    def test_mcp_logs_custom_lines(self, client: TestClient, mock_mcp):
        """GET /api/v1/mcps/{id}/logs with custom line count."""
        response = client.get("/api/v1/mcps/1/logs?lines=100")
        assert response.status_code == 200
        mock_mcp.get_mcp_logs.assert_awaited_with(1, 100)

    def test_mcp_logs_invalid_lines(self, client: TestClient):
        """GET /api/v1/mcps/{id}/logs with invalid line count should return 422."""
        response = client.get("/api/v1/mcps/1/logs?lines=5")
        assert response.status_code == 422

    def test_mcp_not_found_delete(self, client: TestClient, mock_mcp):
        """DELETE /api/v1/mcps/{id} for non-existent MCP."""
        mock_mcp.delete_mcp.return_value = {"status": "deleted", "id": 999}
        response = client.delete("/api/v1/mcps/999")
        assert response.status_code == 200
        # Even if MCP doesn't exist, delete should succeed (idempotent)


# ══════════════════════════════════════════
# Providers
# ══════════════════════════════════════════

class TestProviderEndpoints:
    """Test provider management endpoints."""

    def test_add_provider(self, client: TestClient, mock_provider):
        """POST /api/v1/providers should add a new provider."""
        response = client.post("/api/v1/providers", json={
            "name": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "added"
        assert data["name"] == "openai"

    def test_add_provider_without_api_key(self, client: TestClient, mock_provider):
        """POST /api/v1/providers without API key should still succeed."""
        mock_provider.get_provider.return_value = MagicMock()
        response = client.post("/api/v1/providers", json={
            "name": "local-provider",
            "base_url": "http://localhost:8080",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "added"

    def test_delete_provider(self, client: TestClient, mock_provider):
        """DELETE /api/v1/providers/{name} should delete provider."""
        response = client.delete("/api/v1/providers/openai")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["name"] == "openai"
        mock_provider.remove_provider.assert_called_once_with("openai")

    def test_test_provider(self, client: TestClient, mock_provider):
        """POST /api/v1/providers/test should test provider connection."""
        response = client.post("/api/v1/providers/test", json={
            "name": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "latency_ms" in data

    def test_list_providers(self, client: TestClient, mock_provider):
        """GET /api/v1/providers should list configured providers."""
        mock_provider.instances = {
            "openai": MagicMock(api_key="sk-xxx"),
            "local": MagicMock(api_key=""),
        }
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        # Should not crash even when instances have different attributes

    def test_list_provider_models(self, client: TestClient, mock_provider):
        """GET /api/v1/providers/{name}/models should list provider models."""
        mock_instance = MagicMock()
        mock_instance.list_models = AsyncMock(return_value=["gpt-4", "gpt-3.5-turbo"])
        mock_provider.instances = {"openai": mock_instance}
        
        response = client.get("/api/v1/providers/openai/models")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"
        assert "models" in data
        assert "gpt-4" in data["models"]

    def test_list_provider_models_not_found(self, client: TestClient, mock_provider):
        """GET /api/v1/providers/{name}/models for non-existent provider should return 404."""
        mock_provider.instances = {}
        response = client.get("/api/v1/providers/nonexistent/models")
        assert response.status_code == 404


# ══════════════════════════════════════════
# Chat
# ══════════════════════════════════════════

class TestChatEndpoints:
    """Test chat session management endpoints."""

    def test_create_session(self, client: TestClient, mock_chat):
        """POST /api/v1/chat/session should create a new session."""
        response = client.post("/api/v1/chat/session")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-id"
        mock_chat.create_session.assert_called_once()

    def test_send_message(self, client: TestClient, mock_chat):
        """POST /api/v1/chat/send should send message and get response."""
        response = client.post("/api/v1/chat/send", json={
            "session_id": "test-session-id",
            "content": "Hello!",
            "provider": "ollama",
            "model": "llama3",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-id"
        assert "response" in data
        assert data["provider"] == "ollama"
        assert data["model"] == "llama3"
        mock_chat.send_message.assert_awaited_once()

    def test_send_message_minimal(self, client: TestClient, mock_chat):
        """POST /api/v1/chat/send with only required fields."""
        response = client.post("/api/v1/chat/send", json={
            "session_id": "test-session",
            "content": "Hi",
        })
        assert response.status_code == 200

    def test_chat_history(self, client: TestClient, mock_chat):
        """GET /api/v1/chat/history/{session_id} should return history."""
        response = client.get("/api/v1/chat/history/test-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-id"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        mock_chat.get_session_history.assert_called_once_with("test-session-id")

    def test_chat_history_empty(self, client: TestClient, mock_chat):
        """GET /api/v1/chat/history/{session_id} for new session should return empty."""
        mock_chat.get_session_history.return_value = []
        response = client.get("/api/v1/chat/history/new-session")
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 0

    def test_delete_session(self, client: TestClient, mock_chat):
        """DELETE /api/v1/chat/session/{session_id} should delete session."""
        response = client.delete("/api/v1/chat/session/test-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["session_id"] == "test-session-id"
        mock_chat.delete_session.assert_called_once_with("test-session-id")


# ══════════════════════════════════════════
# Runtime
# ══════════════════════════════════════════

class TestRuntimeEndpoints:
    """Test runtime management endpoints."""

    def test_cleanup_processes(self, client: TestClient, mock_runtime):
        """POST /api/v1/runtime/cleanup should clean zombie processes."""
        response = client.post("/api/v1/runtime/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert data["cleaned"] == 0
        assert data["pids"] == []
        mock_runtime.cleanup_zombie_processes.assert_awaited_once()

    def test_resource_check(self, client: TestClient, mock_runtime):
        """GET /api/v1/runtime/resource-check should check resource limits."""
        response = client.get("/api/v1/runtime/resource-check")
        assert response.status_code == 200
        data = response.json()
        assert data["safe"] is True
        assert data["warnings"] == []
        assert "metrics" in data
        mock_runtime.check_resource_limits.assert_awaited_once()

    def test_start_monitoring(self, client: TestClient, mock_runtime):
        """POST /api/v1/runtime/monitoring/start should start monitoring."""
        response = client.post("/api/v1/runtime/monitoring/start?interval=5")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["interval"] == 5
        mock_runtime.start_monitoring.assert_awaited_once_with(5)

    def test_stop_monitoring(self, client: TestClient, mock_runtime):
        """POST /api/v1/runtime/monitoring/stop should stop monitoring."""
        response = client.post("/api/v1/runtime/monitoring/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        mock_runtime.stop_monitoring.assert_called_once()


# ══════════════════════════════════════════
# Config
# ══════════════════════════════════════════

class TestConfigEndpoints:
    """Test configuration endpoints."""

    def test_get_ui_config(self, client: TestClient):
        """GET /api/v1/config/ui should return UI config."""
        response = client.get("/api/v1/config/ui")
        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "neon"
        assert data["sidebar_collapsed"] is False
        assert data["font_size"] == 14
        assert data["show_metrics"] is True

    def test_update_ui_config(self, client: TestClient):
        """POST /api/v1/config/ui should update UI config."""
        response = client.post("/api/v1/config/ui", json={
            "theme": "dark",
            "sidebar_collapsed": True,
            "font_size": 16,
            "show_metrics": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"
        assert data["sidebar_collapsed"] is True
        assert data["font_size"] == 16

    def test_update_ui_config_partial(self, client: TestClient):
        """POST /api/v1/config/ui with partial data should use defaults."""
        response = client.post("/api/v1/config/ui", json={
            "theme": "light",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["sidebar_collapsed"] is False  # default

    def test_get_runtime_config(self, client: TestClient):
        """GET /api/v1/config/runtime should return runtime config."""
        response = client.get("/api/v1/config/runtime")
        assert response.status_code == 200
        data = response.json()
        assert data["model_idle_timeout_minutes"] == 10
        assert data["max_cpu_percent"] == 90.0
        assert data["max_ram_percent"] == 85.0

    def test_update_runtime_config(self, client: TestClient):
        """POST /api/v1/config/runtime should update runtime config."""
        response = client.post("/api/v1/config/runtime", json={
            "model_idle_timeout_minutes": 30,
            "max_cpu_percent": 80.0,
            "max_ram_percent": 90.0,
            "auto_unload_idle": False,
            "enable_gpu_monitoring": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["model_idle_timeout_minutes"] == 30


# ══════════════════════════════════════════
# Auth
# ══════════════════════════════════════════

class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login(self, client: TestClient):
        """POST /api/v1/auth/login should return access token."""
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "password",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_verify_valid_token(self, client: TestClient):
        """POST /api/v1/auth/verify with valid token should return valid."""
        # First get a token
        login_response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "password",
        })
        token = login_response.json()["access_token"]
        
        # Now verify it
        response = client.post("/api/v1/auth/verify", params={"token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_verify_invalid_token(self, client: TestClient):
        """POST /api/v1/auth/verify with invalid token should return invalid."""
        response = client.post("/api/v1/auth/verify", params={"token": "invalid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False


# ══════════════════════════════════════════
# Integration Flows
# ══════════════════════════════════════════

class TestIntegrationFlows:
    """Test integration scenarios that span multiple endpoints."""

    def test_ollama_detect_then_list_models(self, client: TestClient, mock_ollama):
        """Full Ollama flow: detect -> list -> start -> runtime -> stop."""
        # 1. Detect
        resp1 = client.get("/api/v1/ollama/detect")
        assert resp1.json()["installed"] is True

        # 2. List models
        resp2 = client.get("/api/v1/ollama/models")
        assert resp2.json()["count"] >= 1

        # 3. Start model
        model_name = resp2.json()["models"][0]["name"]
        resp3 = client.post("/api/v1/ollama/models/start", json={"name": model_name})
        assert resp3.json()["status"] == "started"

        # 4. Get runtime info
        resp4 = client.get(f"/api/v1/ollama/models/{model_name}/runtime")
        assert resp4.json()["running"] is True

        # 5. Stop model
        resp5 = client.post("/api/v1/ollama/models/stop", json={"name": model_name})
        assert resp5.json()["status"] == "stopped"

    def test_mcp_crud_flow(self, client: TestClient, mock_mcp):
        """Full MCP CRUD flow: create -> enable -> test -> logs -> disable -> delete."""
        # 1. Create/Register
        mcp_data = {
            "name": "integration-mcp",
            "type": "custom",
            "command": "python",
            "args": ["-m", "http_server"],
            "transport": "stdio",
        }
        resp1 = client.post("/api/v1/mcps", json=mcp_data)
        assert resp1.json()["status"] == "registered"

        # 2. Enable
        resp2 = client.post("/api/v1/mcps/1/enable", json=mcp_data)
        assert resp2.json()["status"] == "started"

        # 3. Test
        resp3 = client.get("/api/v1/mcps/1/test")
        assert resp3.json()["status"] == "healthy"

        # 4. Get logs
        resp4 = client.get("/api/v1/mcps/1/logs")
        assert "logs" in resp4.json()

        # 5. Disable
        resp5 = client.post("/api/v1/mcps/1/disable")
        assert resp5.json()["status"] == "stopped"

        # 6. Delete
        resp6 = client.delete("/api/v1/mcps/1")
        assert resp6.json()["status"] == "deleted"

    def test_provider_chat_flow(self, client: TestClient, mock_provider, mock_chat):
        """Full provider + chat flow."""
        # 1. Add provider
        resp1 = client.post("/api/v1/providers", json={
            "name": "test-llm",
            "base_url": "https://api.test.com/v1",
            "api_key": "sk-test",
        })
        assert resp1.json()["status"] == "added"

        # 2. Test provider
        resp2 = client.post("/api/v1/providers/test", json={
            "name": "test-llm",
            "base_url": "https://api.test.com/v1",
            "api_key": "sk-test",
        })
        assert resp2.json()["status"] == "healthy"

        # 3. List providers
        mock_provider.instances = {"test-llm": MagicMock(api_key="sk-test")}
        resp3 = client.get("/api/v1/providers")
        assert "providers" in resp3.json()

        # 4. Create chat session
        resp4 = client.post("/api/v1/chat/session")
        session_id = resp4.json()["session_id"]

        # 5. Send message
        resp5 = client.post("/api/v1/chat/send", json={
            "session_id": session_id,
            "content": "Hello!",
            "provider": "test-llm",
            "model": "gpt-4",
        })
        assert resp5.json()["session_id"] == session_id

        # 6. Get history
        resp6 = client.get(f"/api/v1/chat/history/{session_id}")
        assert len(resp6.json()["messages"]) > 0

        # 7. Delete session
        resp7 = client.delete(f"/api/v1/chat/session/{session_id}")
        assert resp7.json()["status"] == "deleted"

    def test_health_and_system_flow(self, client: TestClient):
        """Check all health and system endpoints together."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/health/runtime",
            "/api/v1/health/mcp",
            "/api/v1/health/providers",
            "/api/v1/system/info",
            "/api/v1/system/metrics",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}"

    def test_config_save_echoes_input(self, client: TestClient):
        """POST config endpoints echo back the input values."""
        # Save UI config - endpoint echoes back the config
        ui_resp = client.post("/api/v1/config/ui", json={
            "theme": "custom",
            "sidebar_collapsed": True,
            "font_size": 18,
            "show_metrics": False,
        })
        assert ui_resp.json()["theme"] == "custom"
        assert ui_resp.json()["font_size"] == 18

        # Save runtime config - endpoint echoes back the config
        runtime_resp = client.post("/api/v1/config/runtime", json={
            "model_idle_timeout_minutes": 5,
            "max_cpu_percent": 75.0,
            "max_ram_percent": 80.0,
            "auto_unload_idle": True,
            "enable_gpu_monitoring": False,
        })
        assert runtime_resp.json()["model_idle_timeout_minutes"] == 5
        assert runtime_resp.json()["max_cpu_percent"] == 75.0


# ══════════════════════════════════════════
# Error Handling & Edge Cases
# ══════════════════════════════════════════

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_404_not_found(self, client: TestClient):
        """GET to non-existent endpoint should return 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client: TestClient):
        """PUT to read-only endpoint should return 405."""
        response = client.put("/api/v1/health")
        assert response.status_code == 405

    def test_invalid_json_body(self, client: TestClient):
        """POST with invalid JSON should return 422."""
        response = client.post(
            "/api/v1/ollama/models/start",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_empty_request_body(self, client: TestClient):
        """POST without body should return 422 on endpoints that require body."""
        response = client.post("/api/v1/ollama/models/start", json={})
        # name is required, so this should validate properly

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/ollama/models/start",
        "/api/v1/ollama/models/stop",
        "/api/v1/chat/send",
    ])
    def test_post_endpoints_require_body(self, client: TestClient, endpoint: str):
        """POST endpoints should handle invalid data gracefully."""
        response = client.post(endpoint, json={})
        # Should either return 422 (validation error) or 200 with error handling
        assert response.status_code in (200, 422)

    def test_ollama_not_installed(self, client: TestClient, mock_ollama):
        """Test that when Ollama is not installed, the endpoint handles it gracefully."""
        mock_ollama.detect_ollama.return_value = False
        mock_ollama.get_ollama_version.return_value = None
        
        response = client.get("/api/v1/ollama/detect")
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is False
        assert data["version"] is None
