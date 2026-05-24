"""Ollama Runtime Tests - Covers OAPI test cases from test.txt."""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import psutil
import httpx

from services.ollama_service import OllamaService


@pytest.fixture
def ollama_service():
    """Create OllamaService instance for testing."""
    return OllamaService()


@pytest.mark.asyncio
class TestOllamaDetection:
    """OAPI-001: Detect Ollama installation - Positive"""

    async def test_detect_ollama_installed(self, ollama_service):
        """OAPI-001: Positive - Detect installed Ollama"""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"ollama version 0.3.0\n", b"")
        mock_process.stdout = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await ollama_service.detect_ollama()
            assert result is True

    async def test_detect_ollama_not_installed(self, ollama_service):
        """OAPI-002: Negative - Handle missing executable"""
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("ollama not found")):
            result = await ollama_service.detect_ollama()
            assert result is False

    async def test_get_ollama_version(self, ollama_service):
        """OAPI-001: Get Ollama version"""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"ollama version 0.3.0\n", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            version = await ollama_service.get_ollama_version()
            assert version == "ollama version 0.3.0"


@pytest.mark.asyncio
class TestOllamaModelManagement:
    """OAPI-003 to OAPI-008: Model lifecycle tests"""

    async def test_list_models(self, ollama_service):
        """OAPI-003: Positive - Fetch model list"""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3", "size": 4700000000, "details": {"quantization": "Q4_K_M"}},
                {"name": "mistral", "size": 4100000000, "details": {"quantization": "Q4_K_M"}},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            models = await ollama_service.list_models()
            assert len(models) == 2
            assert models[0]["name"] == "llama3"
            assert models[1]["name"] == "mistral"

    async def test_list_models_api_unreachable(self, ollama_service):
        """OAPI-002: Negative - API unreachable"""
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
            models = await ollama_service.list_models()
            assert models == []

    async def test_start_model_success(self, ollama_service):
        """OAPI-004: Positive - Start runtime"""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with patch.object(ollama_service, "_find_ollama_process", return_value=12345):
                result = await ollama_service.start_model("llama3")
                assert result["status"] == "started"
                assert result["model"] == "llama3"
                assert result["pid"] == 12345

    async def test_start_model_connect_error(self, ollama_service):
        """OAPI-007: Negative - Runtime timeout/unreachable"""
        with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
            result = await ollama_service.start_model("llama3")
            assert result["status"] == "error"

    async def test_stop_model_with_pid(self, ollama_service):
        """OAPI-005: Positive - Kill runtime process"""
        ollama_service.running_processes["llama3"] = 12345

        mock_process = MagicMock(spec=psutil.Process)
        with patch("psutil.Process", return_value=mock_process):
            result = await ollama_service.stop_model("llama3")
            assert result["status"] == "stopped"
            assert result["model"] == "llama3"

    async def test_stop_model_not_found(self, ollama_service):
        """OAPI-006: Negative - Invalid PID handled"""
        result = await ollama_service.stop_model("nonexistent_model")
        assert result["status"] == "not_found"

    async def test_concurrent_start_requests(self, ollama_service):
        """OAPI-008: Positive - Concurrent runtime requests safe"""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with patch.object(ollama_service, "_find_ollama_process", return_value=12345):
                results = await asyncio.gather(
                    ollama_service.start_model("llama3"),
                    ollama_service.start_model("mistral"),
                )
                assert results[0]["status"] == "started"
                assert results[1]["status"] == "started"

    async def test_kill_all_processes(self, ollama_service):
        """Kill all running processes"""
        ollama_service.running_processes["llama3"] = 12345
        result = await ollama_service.kill_all_processes()
        assert result["status"] == "cleaned"
        assert ollama_service.running_processes == {}

    async def test_health_check(self, ollama_service):
        """Ollama health check"""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await ollama_service.health_check()
            assert result["status"] == "healthy"

