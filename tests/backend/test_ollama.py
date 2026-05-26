"""Unit tests for OllamaService - detection, model lifecycle, health checks.

All service methods are async def — tests use @pytest.mark.asyncio + async def + await.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def ollama_service():
    from services.ollama_service import OllamaService
    svc = OllamaService()
    svc.ollama_host = "http://localhost:11434"
    svc.running_processes = {}
    return svc


# ──────────────────────────────────────────────
# Detection
# ──────────────────────────────────────────────

class TestDetection:
    """Test Ollama installation detection."""

    @pytest.mark.asyncio
    async def test_detect_ollama_found(self, ollama_service):
        """detect_ollama returns True when Ollama is installed."""
        with patch("services.ollama_service._run_command") as mock_run:
            mock_run.return_value = ("ollama version 0.3.0\n", "")
            result = await ollama_service.detect_ollama()
            assert result is True

    @pytest.mark.asyncio
    async def test_detect_ollama_not_found(self, ollama_service):
        """detect_ollama returns False when Ollama is not installed."""
        with patch("services.ollama_service._run_command") as mock_run:
            mock_run.side_effect = FileNotFoundError("ollama not found")
            result = await ollama_service.detect_ollama()
            assert result is False

    @pytest.mark.asyncio
    async def test_get_version_success(self, ollama_service):
        """get_ollama_version returns version string."""
        with patch("services.ollama_service._run_command") as mock_run:
            mock_run.return_value = ("ollama version 0.3.0\n", "")
            version = await ollama_service.get_ollama_version()
            assert version == "ollama version 0.3.0"

    @pytest.mark.asyncio
    async def test_get_version_failure(self, ollama_service):
        """get_ollama_version returns None on failure."""
        with patch("services.ollama_service._run_command") as mock_run:
            mock_run.side_effect = FileNotFoundError("not found")
            version = await ollama_service.get_ollama_version()
            assert version is None


# ──────────────────────────────────────────────
# Model Listing
# ──────────────────────────────────────────────

class TestListModels:
    """Test model listing (API + CLI fallback)."""

    @pytest.mark.asyncio
    async def test_list_models_via_api(self, ollama_service):
        """list_models returns models from HTTP API."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [{"name": "llama3:latest", "size": 4700000000, "details": {"quantization": "Q4_0"}, "modified_at": "2024-01-01T00:00:00Z"}]
            }
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.return_value = mock_response
            mock_httpx.return_value = mock_client

            models = await ollama_service.list_models()
            assert len(models) == 1
            assert models[0]["name"] == "llama3:latest"

    @pytest.mark.asyncio
    async def test_list_models_empty_when_api_down(self, ollama_service):
        """list_models returns empty list when API is unreachable."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.side_effect = Exception("Connection refused")
            mock_httpx.return_value = mock_client

            models = await ollama_service.list_models()
            assert models == []

    @pytest.mark.asyncio
    async def test_list_models_zero_size(self, ollama_service):
        """list_models handles '0' size string correctly."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.side_effect = Exception("API down")
            mock_httpx.return_value = mock_client

            with patch("services.ollama_service._run_command") as mock_run:
                mock_run.return_value = ("NAME\tID\tSIZE\tMODIFIED\nllama3:latest\tabc123\t0\t2 days ago\n", "")
                models = await ollama_service.list_models()
                assert len(models) >= 1
                assert models[0]["size"] == 0

    @pytest.mark.asyncio
    async def test_list_models_cli_fallback(self, ollama_service):
        """list_models falls back to CLI when API fails."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.side_effect = Exception("API unreachable")
            mock_httpx.return_value = mock_client

            with patch("services.ollama_service._run_command") as mock_run:
                cli_output = "NAME\tID\tSIZE\tMODIFIED\nllama3:latest\tabc123\t4.7GB\t2 days ago\nmistral:7b\tdef456\t4.1GB\t3 days ago\n"
                mock_run.return_value = (cli_output, "")
                models = await ollama_service.list_models()
                assert len(models) == 2
                names = [m["name"] for m in models]
                assert "llama3:latest" in names
                assert "mistral:7b" in names


# ──────────────────────────────────────────────
# Model Lifecycle
# ──────────────────────────────────────────────

class TestModelLifecycle:
    """Test model start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_model_success(self, ollama_service):
        """start_model starts a model successfully."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.post.return_value = mock_response
            mock_httpx.return_value = mock_client

            with patch.object(ollama_service, "_find_ollama_process") as mock_find:
                mock_find.return_value = 12345
                result = await ollama_service.start_model("llama3:latest")

            assert result["status"] == "started"
            assert result["model"] == "llama3:latest"
            assert result["pid"] == 12345
            assert "llama3:latest" in ollama_service.running_processes

    @pytest.mark.asyncio
    async def test_start_model_api_down(self, ollama_service):
        """start_model returns error when Ollama API is unreachable."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.post.side_effect = Exception("Connection refused")
            mock_httpx.return_value = mock_client

            result = await ollama_service.start_model("llama3:latest")
            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_stop_model_success(self, ollama_service):
        """stop_model stops a running model."""
        ollama_service.running_processes["test-model"] = 12345
        with patch("services.ollama_service.psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_process.return_value = mock_proc

            result = await ollama_service.stop_model("test-model")
            assert result["status"] == "stopped"
            assert "test-model" not in ollama_service.running_processes
            mock_proc.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_model_not_found(self, ollama_service):
        """stop_model returns not_found for unknown model."""
        result = await ollama_service.stop_model("nonexistent")
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_stop_model_no_such_process(self, ollama_service):
        """stop_model handles psutil.NoSuchProcess gracefully."""
        ollama_service.running_processes["test-model"] = 99999
        with patch("services.ollama_service.psutil.Process") as mock_process:
            mock_process.side_effect = Exception("NoSuchProcess")
            result = await ollama_service.stop_model("test-model")
            assert result["status"] == "already_stopped"


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, ollama_service):
        """health_check returns healthy when API responds."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.return_value = mock_response
            mock_httpx.return_value = mock_client

            result = await ollama_service.health_check()
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unreachable(self, ollama_service):
        """health_check returns unreachable on connection error."""
        with patch("services.ollama_service.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.side_effect = Exception("Connection refused")
            mock_httpx.return_value = mock_client

            result = await ollama_service.health_check()
            assert result["status"] == "unreachable"


# ──────────────────────────────────────────────
# Size Parsing
# ──────────────────────────────────────────────

class TestSizeParsing:
    """Test _parse_ollama_size edge cases."""

    def test_parse_gigabytes(self):
        """GB strings parse correctly."""
        from services.ollama_service import OllamaService
        assert OllamaService._parse_ollama_size("4.7GB") == int(4.7 * 1024**3)

    def test_parse_megabytes(self):
        """MB strings parse correctly."""
        from services.ollama_service import OllamaService
        assert OllamaService._parse_ollama_size("356MB") == 356 * 1024**2

    def test_parse_kilobytes(self):
        """KB strings parse correctly."""
        from services.ollama_service import OllamaService
        assert OllamaService._parse_ollama_size("128KB") == 128 * 1024

    def test_parse_zero(self):
        """0 returns 0."""
        from services.ollama_service import OllamaService
        assert OllamaService._parse_ollama_size("0") == 0

    def test_parse_empty(self):
        """Empty string returns 0."""
        from services.ollama_service import OllamaService
        assert OllamaService._parse_ollama_size("") == 0

    def test_parse_garbage(self):
        """Invalid strings return 0."""
        from services.ollama_service import OllamaService
        assert OllamaService._parse_ollama_size("garbage") == 0


# ──────────────────────────────────────────────
# Process Management
# ──────────────────────────────────────────────

class TestProcessManagement:
    """Test process management (kill_all, runtime info)."""

    @pytest.mark.asyncio
    async def test_kill_all_processes(self, ollama_service):
        """kill_all_processes kills all ollama processes."""
        with patch("services.ollama_service.psutil.process_iter") as mock_iter:
            proc = MagicMock()
            proc.info = {"pid": 12345, "name": "ollama"}
            mock_iter.return_value = [proc]

            result = await ollama_service.kill_all_processes()
            assert result["status"] == "cleaned"
            proc.kill.assert_called_once()
            assert ollama_service.running_processes == {}

    @pytest.mark.asyncio
    async def test_get_model_runtime_info_running(self, ollama_service):
        """get_model_runtime_info returns info for running model."""
        ollama_service.running_processes["test-model"] = 12345
        with patch("services.ollama_service.psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.cpu_percent.return_value = 25.0
            mock_proc.memory_info.return_value.rss = 500 * 1024 * 1024
            mock_process.return_value = mock_proc

            info = await ollama_service.get_model_runtime_info("test-model")
            assert info["running"] is True
            assert info["pid"] == 12345
