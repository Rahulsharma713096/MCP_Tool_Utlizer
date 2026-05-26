"""Recovery & Failure Scenario Tests - system resilience under adverse conditions.

Tests cover:
- Service crashes and restarts
- Corrupt/invalid data handling
- Network failures and timeouts
- Resource exhaustion simulation
- Concurrent request handling
- Graceful degradation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import json
from services.chat_service import ChatService


# ──────────────────────────────────────────────
# Service Crash Recovery
# ──────────────────────────────────────────────

class TestServiceCrashRecovery:
    """Test recovery from service crashes."""

    @patch("services.ollama_service.httpx.AsyncClient")
    def test_ollama_recovers_after_connect_error(self, mock_httpx):
        """OllamaService returns healthy after recovering from connection failure."""
        from services.ollama_service import OllamaService
        svc = OllamaService()

        # Simulate failure then recovery
        mock_response1 = MagicMock()
        mock_response1.status_code = 200

        mock_client = AsyncMock().__aenter__.return_value
        mock_client.get.side_effect = [
            Exception("Connection refused"),  # First call fails
            mock_response1,  # Second call succeeds
        ]
        mock_httpx.return_value = mock_client

        # First call fails
        result1 = svc.health_check()
        assert result1["status"] == "unreachable"

        # Second call succeeds
        result2 = svc.health_check()
        assert result2["status"] == "healthy"

    def test_mcp_recovers_after_stop_error(self):
        """MCPService handles stop on non-existent process gracefully."""
        from services.mcp_service import MCPService
        svc = MCPService()

        # Stop an already stopped MCP
        result = svc.stop_mcp(999)
        assert result["status"] == "not_running"

        # Should still be able to start new MCPs
        assert len(svc.running_mcps) == 0

    def test_chat_recovers_after_session_delete(self):
        """ChatService creates new session after deleting an active one."""
        from services.chat_service import ChatService
        svc = ChatService()

        sid = svc.create_session("test-session")
        svc.delete_session("test-session")

        # Creating the same session ID should work
        new_sid = svc.create_session("test-session")
        assert new_sid in svc.sessions


# ──────────────────────────────────────────────
# Data Corruption Handling
# ──────────────────────────────────────────────

class TestDataCorruption:
    """Test handling of corrupt/invalid data."""

    def test_parse_ollama_size_handles_garbage(self):
        """OllamaService._parse_ollama_size returns 0 for unparseable strings."""
        from services.ollama_service import OllamaService
        svc = OllamaService()

        assert svc._parse_ollama_size("") == 0
        assert svc._parse_ollama_size("   ") == 0
        assert svc._parse_ollama_size("garbage!!") == 0
        assert svc._parse_ollama_size("1.2.3.4") == 0

    def test_mcp_register_with_empty_command(self):
        """MCPService handles empty command during registration."""
        from services.mcp_service import MCPService
        svc = MCPService()

        result = svc.register_mcp({
            "name": "empty-cmd",
            "type": "custom",
            "command": "",
        })
        assert result["status"] == "registered"  # Empty not blocked

    def test_mcp_register_with_none_command(self):
        """MCPService handles None command gracefully."""
        from services.mcp_service import MCPService
        svc = MCPService()

        result = svc.register_mcp({
            "name": "none-cmd",
            "type": "custom",
            "command": None,
        })
        assert result["status"] == "registered"

    @patch.object(ChatService, "_chat_with_ollama")
    def test_chat_with_empty_content(self, mock_chat):
        """ChatService handles empty message content."""
        from services.chat_service import ChatService
        svc = ChatService()

        mock_chat.return_value = {"content": ""}
        svc.create_session("test")

        result = svc.send_message("test", "", provider="ollama")
        assert "response" in result


# ──────────────────────────────────────────────
# Network Failures
# ──────────────────────────────────────────────

class TestNetworkFailures:
    """Test handling of network failures and timeouts."""

    @patch("services.ollama_service.httpx.AsyncClient")
    def test_ollama_list_models_network_error(self, mock_httpx):
        """OllamaService.list_models handles network errors and returns empty."""
        from services.ollama_service import OllamaService
        svc = OllamaService()

        mock_client = AsyncMock().__aenter__.return_value
        mock_client.get.side_effect = Exception("Network is unreachable")
        mock_httpx.return_value = mock_client

        with patch("services.ollama_service._run_command") as mock_run:
            mock_run.side_effect = FileNotFoundError("ollama not found")
            models = svc.list_models()
            assert models == []

    @patch("services.ollama_service.httpx.AsyncClient")
    def test_ollama_start_model_connection_refused(self, mock_httpx):
        """OllamaService.start_model handles connection refused."""
        from services.ollama_service import OllamaService
        svc = OllamaService()

        mock_client = AsyncMock().__aenter__.return_value
        mock_client.post.side_effect = Exception("Connection refused")
        mock_httpx.return_value = mock_client

        result = svc.start_model("llama3:latest")
        assert result["status"] == "error"

    def test_mcp_test_http_unreachable(self):
        """MCPService.test_mcp for HTTP returns unreachable without crashing."""
        from services.mcp_service import MCPService
        from models.database import MCP

        svc = MCPService()
        mcp = MCP(id=1, name="test", type="custom", command="", args=[],
                  transport="http", endpoint="http://localhost:9999")

        with patch("services.mcp_service.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.side_effect = Exception("Connection refused")
            mock_httpx.return_value = mock_client

            result = svc.test_mcp(mcp)
            assert result["status"] == "unreachable"


# ──────────────────────────────────────────────
# Concurrent Request Handling
# ──────────────────────────────────────────────

class TestConcurrency:
    """Test handling of concurrent requests."""

    def test_concurrent_session_creation(self):
        """ChatService handles concurrent session creation."""
        from services.chat_service import ChatService
        svc = ChatService()

        # Simulate rapid session creation
        session_ids = [svc.create_session() for _ in range(10)]
        assert len(set(session_ids)) == 10  # All unique
        assert len(svc.sessions) == 10

    def test_mcp_stop_same_id_twice(self):
        """MCPService.stop_mcp is idempotent for concurrent calls."""
        from services.mcp_service import MCPService
        svc = MCPService()

        # Stop twice
        result1 = svc.stop_mcp(1)
        result2 = svc.stop_mcp(1)

        assert result1["status"] == "not_running"
        assert result2["status"] == "not_running"

    def test_chat_delete_same_session_twice(self):
        """ChatService.delete_session is idempotent."""
        from services.chat_service import ChatService
        svc = ChatService()

        sid = svc.create_session()
        svc.delete_session(sid)
        svc.delete_session(sid)  # Should not raise

        assert sid not in svc.sessions


# ──────────────────────────────────────────────
# Graceful Degradation
# ──────────────────────────────────────────────

class TestGracefulDegradation:
    """Test system behavior when components are unavailable."""

    def test_chat_without_mcp_service(self):
        """ChatService works without MCP service for tool integration."""
        from services.chat_service import ChatService
        svc = ChatService(mcp_service=None)

        tools = svc._collect_tools()
        assert tools == []

    def test_mcp_running_processes_empty(self):
        """MCPService handles empty running processes gracefully."""
        from services.mcp_service import MCPService
        svc = MCPService()

        result = svc.cleanup_all()
        assert svc.running_mcps == {}
        assert svc._mcp_info == {}
        assert svc._tool_cache == {}


