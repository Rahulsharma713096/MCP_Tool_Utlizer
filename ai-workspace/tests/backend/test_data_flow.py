"""Data Flow Tests - Covers DF-001 to DF-008 from test.txt.
Tests the complete data flow through the system layers.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
import json
import httpx

from services.ollama_service import OllamaService
from services.chat_service import ChatService
from services.mcp_service import MCPService
from services.provider_service import ProviderService
from services.runtime_service import RuntimeService


@pytest.mark.asyncio
class TestOllamaDataFlow:
    """DF-001 to DF-005: Ollama data flow tests."""

    async def test_ui_to_backend_request(self):
        """DF-001: UI -> backend request valid - simulate frontend API call"""
        service = OllamaService()
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3", "size": 4700000000}]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            # Simulate what the UI would call
            models = await service.list_models()
            assert len(models) == 1
            assert models[0]["name"] == "llama3"

    async def test_backend_to_ollama_command(self):
        """DF-002: Backend -> Ollama command valid"""
        service = OllamaService()
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"ollama version 0.3.0\n", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Backend issues a command to Ollama CLI
            detected = await service.detect_ollama()
            assert detected is True

    async def test_runtime_state_sync(self):
        """DF-003: Runtime state sync correct"""
        service = OllamaService()
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with patch.object(service, "_find_ollama_process", return_value=12345):
                result = await service.start_model("llama3")
                assert result["status"] == "started"
                # Verify runtime state is tracked
                assert "llama3" in service.running_processes
                assert service.running_processes["llama3"] == 12345

    async def test_process_state_persistence(self):
        """DF-005: Process state persistence"""
        service = OllamaService()
        service.running_processes["test-model"] = 99999

        # Verify state is accessible
        assert "test-model" in service.running_processes
        assert service.running_processes["test-model"] == 99999

        # Stop and verify cleanup
        result = await service.stop_model("test-model")
        assert result["status"] == "stopped"
        assert "test-model" not in service.running_processes


@pytest.mark.asyncio
class TestChatDataFlow:
    """DF-006: WebSocket data consistency tests."""

    async def test_chat_request_response_flow(self):
        """DF-001: Chat request/response flow"""
        service = ChatService()
        session_id = service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Response from assistant"}
        }

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await service.send_message(
                session_id=session_id,
                content="Test message",
                provider="ollama",
                model="llama3",
            )
            assert result["response"] == "Response from assistant"

    async def test_message_persistence(self):
        """DF-006: Messages persist in session history"""
        service = ChatService()
        session_id = service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Hello!"}}

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            await service.send_message(session_id, "Hi!", provider="ollama")
            await service.send_message(session_id, "How are you?", provider="ollama")

        # Verify all messages persisted
        history = service.get_session_history(session_id)
        assert len(history) == 4  # 2 user + 2 assistant
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hi!"
        assert history[2]["content"] == "How are you?"


@pytest.mark.asyncio
class TestMCPDataFlow:
    """DF-007: MCP tool output data flow tests."""

    async def test_mcp_output_returned(self):
        """DF-007: MCP tool output returned correctly"""
        service = MCPService()
        mcp_data = {
            "name": "test-mcp",
            "type": "python",
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "print('hello')"],
        }

        result = await service.register_mcp(mcp_data)
        assert result["status"] == "registered"
        assert result["mcp"]["name"] == "test-mcp"


@pytest.mark.asyncio
class TestRuntimeDataFlow:
    """Runtime data flow tests."""

    async def test_metrics_data_flow(self):
        """Metrics collection and storage"""
        runtime = RuntimeService()
        metrics = await runtime.get_current_metrics()

        assert "cpu_percent" in metrics
        assert "ram_percent" in metrics
        assert "timestamp" in metrics
        assert isinstance(metrics["cpu_percent"], (int, float))

    async def test_metrics_history(self):
        """DF-004: Metrics history tracking"""
        runtime = RuntimeService()
        # Collect some metrics
        await runtime.get_current_metrics()
        await runtime.get_current_metrics()

        # Get history
        history = await runtime.get_metrics_history(minutes=60)
        assert len(history) >= 2

    async def test_resource_check_flow(self):
        """Resource check data flow"""
        runtime = RuntimeService()
        result = await runtime.check_resource_limits()

        assert "safe" in result
        assert "warnings" in result
        assert "metrics" in result


@pytest.mark.asyncio
class TestProviderDataFlow:
    """DF-008: Provider data flow tests."""

    async def test_provider_config_update(self):
        """DF-008: Config updates propagate instantly"""
        service = ProviderService()

        # Add provider
        provider = service.get_provider("openrouter", "FlowTest", "https://openrouter.ai/api/v1", "test-key")
        assert provider is not None
        assert "FlowTest" in service.instances
        assert service.instances["FlowTest"] is provider

        # Verify it's accessible immediately
        cached = service.get_provider("openrouter", "FlowTest", "https://openrouter.ai/api/v1")
        assert cached is provider

        # Remove
        service.remove_provider("FlowTest")
        assert "FlowTest" not in service.instances
