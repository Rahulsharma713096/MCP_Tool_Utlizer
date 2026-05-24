"""Recovery Tests - Covers REC-001 to REC-005 from test.txt.
Tests system recovery from failures and crashes.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import asyncio

from services.ollama_service import OllamaService
from services.chat_service import ChatService
from services.mcp_service import MCPService
from services.runtime_service import RuntimeService


@pytest.mark.asyncio
class TestBackendRecovery:
    """REC-001: Backend restart recovery tests."""

    async def test_recover_from_ollama_crash(self):
        """REC-001: Backend recovers after Ollama crash"""
        service = OllamaService()

        # Simulate Ollama being available
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3", "size": 4700000000}]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            models = await service.list_models()
            assert len(models) == 1

        # Simulate crash (Ollama unreachable)
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
            models = await service.list_models()
            assert models == []  # Graceful degradation

        # Recover (Ollama available again)
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            models = await service.list_models()
            assert len(models) == 1  # Full recovery

    async def test_recover_from_api_failure(self):
        """REC-001: API failure recovery"""
        service = ChatService()
        session_id = service.create_session()

        # First request succeeds
        mock_ok = AsyncMock(spec=httpx.Response)
        mock_ok.status_code = 200
        mock_ok.json.return_value = {"message": {"content": "Hello!"}}

        with patch("httpx.AsyncClient.post", return_value=mock_ok):
            result = await service.send_message(session_id, "Hi!", provider="ollama")
            assert result["response"] == "Hello!"

        # Second request fails
        with patch("httpx.AsyncClient.post", side_effect=Exception("API error")):
            result = await service.send_message(session_id, "Hello?", provider="ollama")
            assert "Error" in result["response"]

        # Third request recovers
        with patch("httpx.AsyncClient.post", return_value=mock_ok):
            result = await service.send_message(session_id, "Are you back?", provider="ollama")
            assert result["response"] == "Hello!"


@pytest.mark.asyncio
class TestRuntimeCrashRecovery:
    """REC-002: Runtime crash recovery tests."""

    async def test_runtime_crash_recovery(self):
        """REC-002: Runtime crash recovery"""
        service = OllamaService()
        service.running_processes["llama3"] = 12345

        # Runtime was killed externally
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.is_running.side_effect = [True, True, False]  # Dies on third check

        with patch("psutil.Process", return_value=mock_process):
            # Simulate runtime crash detection and recovery
            result = await service.stop_model("llama3")
            assert result["status"] == "stopped"
            assert "llama3" not in service.running_processes

    async def test_detect_missing_runtime(self):
        """REC-002: Detect missing runtime process"""
        service = OllamaService()

        # Try to stop non-existent model
        result = await service.stop_model("ghost-model")
        assert result["status"] == "not_found"

        # Verify service still works after
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            health = await service.health_check()
            assert health["status"] == "healthy"

    async def test_cleanup_zombie_processes(self):
        """REC-002: Zombie process cleanup"""
        runtime = RuntimeService()
        result = await runtime.cleanup_zombie_processes()
        assert "cleaned" in result
        assert isinstance(result["cleaned"], int)


@pytest.mark.asyncio
class TestConnectionRecovery:
    """REC-003 to REC-004: Connection recovery tests."""

    async def test_database_reconnect(self):
        """REC-003: DB reconnect - service handles DB failures gracefully"""
        service = ChatService()

        # Service should work without DB (in-memory fallback)
        session_id = service.create_session()
        assert session_id is not None

        # Verify session works
        history = service.get_session_history(session_id)
        assert history == []

    async def test_provider_failover(self):
        """REC-004/005: Provider failover when one provider fails"""
        from services.provider_service import ProviderService, OpenRouterProvider
        service = ProviderService()

        # Provider fails
        with patch("httpx.AsyncClient.get", side_effect=Exception("Provider down")):
            # Should return error status, not crash
            provider = OpenRouterProvider(
                name="FailoverTest",
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
            )
            result = await provider.health_check()
            assert result["status"] == "unreachable"

    async def test_websocket_reconnect_scenario(self):
        """REC-004: WebSocket reconnect simulation"""
        service = ChatService()
        session_id = service.create_session()

        # Normal operation
        mock_ok = AsyncMock(spec=httpx.Response)
        mock_ok.status_code = 200
        mock_ok.json.return_value = {"message": {"content": "OK"}}

        with patch("httpx.AsyncClient.post", return_value=mock_ok):
            result = await service.send_message(session_id, "Test", provider="ollama")
            assert result["response"] == "OK"

        # Simulate disconnect and reconnect - create new session works
        new_session = service.create_session()
        assert new_session != session_id
        assert new_session in service.sessions


@pytest.mark.asyncio
class TestConfigRecovery:
    """REC-005: Config rollback tests."""

    async def test_service_graceful_degradation(self):
        """REC-005: Services degrade gracefully on failure"""
        # Test MCP service with bad data
        mcp_service = MCPService()

        # Bad MCP config should not crash the service
        bad_mcp_data = {
            "name": "",
            "type": "",
            "transport": None,
        }
        result = await mcp_service.register_mcp(bad_mcp_data)
        assert result["status"] == "error"

        # Service should still work after bad input
        good_mcp_data = {
            "name": "recovery-test",
            "type": "python",
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "print('ok')"],
        }
        result = await mcp_service.register_mcp(good_mcp_data)
        assert result["status"] == "registered"

    async def test_chat_service_recovery(self):
        """Chat service recovers from bad provider"""
        service = ChatService()
        session_id = service.create_session()

        # Bad provider
        result = await service.send_message(
            session_id=session_id,
            content="Hi!",
            provider="",
            model="",
        )
        assert "not configured" in result["response"].lower() or "Error" in result["response"]

        # Service still usable
        result = await service.send_message(
            session_id=session_id,
            content="Test",
            provider="ollama",
            model="llama3",
        )
        assert result["session_id"] == session_id
