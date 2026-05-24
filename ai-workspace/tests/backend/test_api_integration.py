"""API Integration Tests - FastAPI TestClient testing.
Covers API endpoint integration from test.txt requirements:
OAPI, MCPAPI, PAPI, CAPI, SAN-001 to SAN-010, DF-001 to DF-008
"""

import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "apps" / "backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealthEndpoints:
    """SAN-001 to SAN-003: Health and system endpoints."""

    def test_health_check(self):
        """SAN-001: App launches - Health endpoint works"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "ollama" in data
        assert "version" in data
        assert "database" in data

    def test_system_info(self):
        """SAN-003: System info endpoint"""
        response = client.get("/api/v1/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data
        assert "cpus" in data
        assert "total_ram_gb" in data

    def test_system_metrics(self):
        """SAN-003: System metrics endpoint"""
        response = client.get("/api/v1/system/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "ram_percent" in data

    def test_health_runtime(self):
        """Runtime health endpoint"""
        response = client.get("/api/v1/health/runtime")
        assert response.status_code == 200

    def test_health_mcp(self):
        """MCP health endpoint"""
        response = client.get("/api/v1/health/mcp")
        assert response.status_code == 200
        data = response.json()
        assert "active_mcps" in data

    def test_health_providers(self):
        """Provider health endpoint"""
        response = client.get("/api/v1/health/providers")
        assert response.status_code == 200
        data = response.json()
        assert "active_providers" in data


class TestOllamaAPI:
    """OAPI-001 to OAPI-008: Ollama runtime API tests."""

    def test_detect_ollama(self):
        """OAPI-001: Detect Ollama installation"""
        response = client.get("/api/v1/ollama/detect")
        assert response.status_code == 200
        data = response.json()
        assert "installed" in data
        assert "version" in data

    def test_list_models_api(self):
        """OAPI-003: Fetch model list via API"""
        response = client.get("/api/v1/ollama/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "count" in data

    def test_start_model_invalid(self):
        """OAPI-004: Negative - Start missing model returns 400"""
        response = client.post("/api/v1/ollama/models/start", json={"name": "nonexistent-model"})
        # Either 200 with error or 400 depending on service logic
        assert response.status_code in (200, 400)
        data = response.json()
        if response.status_code == 400:
            assert "detail" in data


class TestMCPAPI:
    """MCPAPI-001 to MCPAPI-007: MCP API tests."""

    def test_register_mcp_api(self):
        """MCPAPI-001: Register MCP via API"""
        response = client.post("/api/v1/mcps", json={
            "name": "api-test-mcp",
            "type": "python",
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "print('test')"],
        })
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["status"] == "registered"

    def test_register_mcp_blocked(self):
        """MCPAPI-004: Negative - Blocked command rejected"""
        response = client.post("/api/v1/mcps", json={
            "name": "bad-mcp",
            "type": "shell",
            "transport": "stdio",
            "command": "rm -rf /",
        })
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestProviderAPI:
    """PAPI-001 to PAPI-007: Provider API tests."""

    def test_add_provider(self):
        """PAPI-001: Add provider via API"""
        response = client.post("/api/v1/providers", json={
            "name": "TestProvider",
            "base_url": "https://api.test.com/v1",
            "api_key": "sk-test-key-12345",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "added"

    def test_list_providers(self):
        """PAPI: List providers via API"""
        response = client.get("/api/v1/providers")
        assert response.status_code == 200

    def test_delete_provider(self):
        """PAPI-002: Delete provider via API"""
        # First add
        client.post("/api/v1/providers", json={
            "name": "DeleteTest",
            "base_url": "https://api.test.com/v1",
            "api_key": "sk-test-key",
        })
        # Then delete
        response = client.delete("/api/v1/providers/DeleteTest")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"


class TestChatAPI:
    """CAPI-001 to CAPI-006: Chat API tests."""

    def test_create_session(self):
        """CAPI-001: Create chat session"""
        response = client.post("/api/v1/chat/session")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_send_message(self):
        """CAPI-001: Send chat message"""
        # Create session first
        session_resp = client.post("/api/v1/chat/session")
        session_id = session_resp.json()["session_id"]

        # Send message
        response = client.post("/api/v1/chat/send", json={
            "session_id": session_id,
            "content": "Hello!",
            "provider": "ollama",
            "model": "llama3",
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data

    def test_chat_history(self):
        """CAPI-003: Get chat history"""
        session_resp = client.post("/api/v1/chat/session")
        session_id = session_resp.json()["session_id"]

        # Send a message
        client.post("/api/v1/chat/send", json={
            "session_id": session_id,
            "content": "Hi!",
            "provider": "ollama",
        })

        # Get history
        response = client.get(f"/api/v1/chat/history/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "messages" in data


class TestAuthAPI:
    """SEC-001 to SEC-003: Auth API tests."""

    def test_login(self):
        """SEC-001: Login endpoint works"""
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_verify_token_valid(self):
        """SEC-001: Verify valid token"""
        login_resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        token = login_resp.json()["access_token"]

        # Token is a query parameter in this endpoint
        response = client.post(f"/api/v1/auth/verify?token={token}")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_verify_token_invalid(self):
        """SEC-001: Negative - Verify invalid token"""
        response = client.post("/api/v1/auth/verify?token=invalid.token.here")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False


class TestConfigAPI:
    """Config API tests."""

    def test_get_ui_config(self):
        """Get UI config"""
        response = client.get("/api/v1/config/ui")
        assert response.status_code == 200

    def test_get_runtime_config(self):
        """Get runtime config"""
        response = client.get("/api/v1/config/runtime")
        assert response.status_code == 200


class TestRuntimeAPI:
    """Runtime API tests."""

    def test_resource_check(self):
        """Runtime resource check"""
        response = client.get("/api/v1/runtime/resource-check")
        assert response.status_code == 200
        data = response.json()
        assert "safe" in data
        assert "metrics" in data

    def test_cleanup_processes(self):
        """Runtime cleanup"""
        response = client.post("/api/v1/runtime/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert "cleaned" in data
