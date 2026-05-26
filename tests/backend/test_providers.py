"""Unit tests for ProviderService - provider factory, API providers, and connection testing.

All provider chat/list/health methods are async def — tests use @pytest.mark.asyncio + await.
Factory methods and ProviderService.get_provider/remove_provider are sync.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ──────────────────────────────────────────────
# ProviderFactory (Sync methods)
# ──────────────────────────────────────────────

class TestProviderFactory:
    """Test provider factory creates correct types."""

    def test_create_openai(self):
        """Factory creates OpenAIProvider for 'openai' type."""
        from services.provider_service import ProviderFactory, OpenAIProvider
        provider = ProviderFactory.create("openai", "my-openai", "https://api.openai.com/v1", "sk-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "my-openai"
        assert provider.base_url == "https://api.openai.com/v1"
        assert provider.api_key == "sk-key"

    def test_create_openrouter(self):
        """Factory creates OpenRouterProvider for 'openrouter' type."""
        from services.provider_service import ProviderFactory, OpenRouterProvider
        provider = ProviderFactory.create("openrouter", "my-router", "https://openrouter.ai/api/v1", "sk-key")
        assert isinstance(provider, OpenRouterProvider)

    def test_create_gemini(self):
        """Factory creates GeminiProvider for 'gemini' type."""
        from services.provider_service import ProviderFactory, GeminiProvider
        provider = ProviderFactory.create("gemini", "my-gemini", "https://generativelanguage.googleapis.com", "api-key")
        assert isinstance(provider, GeminiProvider)

    def test_create_zai_uses_openai(self):
        """Factory uses OpenAIProvider for 'zai' type."""
        from services.provider_service import ProviderFactory, OpenAIProvider
        provider = ProviderFactory.create("zai", "my-zai", "https://api.z.ai/v1", "sk-key")
        assert isinstance(provider, OpenAIProvider)

    def test_create_unknown_defaults_to_openai(self):
        """Factory defaults to OpenAIProvider for unknown types."""
        from services.provider_service import ProviderFactory, OpenAIProvider
        provider = ProviderFactory.create("unknown", "fallback", "https://api.example.com/v1", "sk-key")
        assert isinstance(provider, OpenAIProvider)


# ──────────────────────────────────────────────
# OpenAI Provider (Async methods)
# ──────────────────────────────────────────────

class TestOpenAIProvider:
    """Test OpenAI-compatible provider."""

    @pytest.fixture
    def provider(self):
        from services.provider_service import OpenAIProvider
        return OpenAIProvider("test-openai", "https://api.openai.com/v1", "sk-test-key")

    def test_setup_auth(self, provider):
        """Auth header is set from API key."""
        assert provider.headers["Authorization"] == "Bearer sk-test-key"

    @pytest.mark.asyncio
    async def test_chat_success(self, provider):
        """chat returns response from the API."""
        with patch("services.provider_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Hello!"}}]
            }
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.post.return_value = mock_response
            mock_httpx.return_value = mock_client

            result = await provider.chat("gpt-4", [{"role": "user", "content": "Hi"}])
            assert result["choices"][0]["message"]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_list_models(self, provider):
        """list_models returns model IDs from the API."""
        with patch("services.provider_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"id": "gpt-4"}, {"id": "gpt-3.5-turbo"}]
            }
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.return_value = mock_response
            mock_httpx.return_value = mock_client

            models = await provider.list_models()
            assert "gpt-4" in models
            assert "gpt-3.5-turbo" in models

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, provider):
        """health_check returns healthy when API responds."""
        with patch("services.provider_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.return_value = mock_response
            mock_httpx.return_value = mock_client

            result = await provider.health_check()
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unreachable(self, provider):
        """health_check returns unreachable on connection error."""
        with patch("services.provider_service.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.side_effect = Exception("Connection error")
            mock_httpx.return_value = mock_client

            result = await provider.health_check()
            assert result["status"] == "unreachable"


# ──────────────────────────────────────────────
# Gemini Provider (Async methods)
# ──────────────────────────────────────────────

class TestGeminiProvider:
    """Test Google Gemini provider."""

    @pytest.fixture
    def provider(self):
        from services.provider_service import GeminiProvider
        return GeminiProvider("test-gemini", "https://generativelanguage.googleapis.com", "gemini-key")

    @pytest.mark.asyncio
    async def test_chat_maps_messages_to_contents(self, provider):
        """chat maps user/assistant messages to Gemini content format."""
        with patch("services.provider_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Hi there!"}]}}]
            }
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.post.return_value = mock_response
            mock_httpx.return_value = mock_client

            result = await provider.chat("gemini-pro", [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ])

            call_kwargs = mock_client.post.call_args[1]
            sent_json = call_kwargs["json"]
            assert len(sent_json["contents"]) == 2
            assert sent_json["contents"][0]["role"] == "user"
            assert sent_json["contents"][0]["parts"][0]["text"] == "Hello"
            assert call_kwargs["params"]["key"] == "gemini-key"

    @pytest.mark.asyncio
    async def test_list_models(self, provider):
        """list_models returns model names stripped of 'models/' prefix."""
        with patch("services.provider_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "models": [{"name": "models/gemini-pro"}, {"name": "models/gemini-ultra"}]
            }
            mock_client = AsyncMock().__aenter__.return_value
            mock_client.get.return_value = mock_response
            mock_httpx.return_value = mock_client

            models = await provider.list_models()
            assert "gemini-pro" in models
            assert "gemini-ultra" in models


# ──────────────────────────────────────────────
# ProviderService (Mix of sync/async)
# ──────────────────────────────────────────────

class TestProviderService:
    """Test ProviderService management."""

    @pytest.fixture
    def service(self):
        from services.provider_service import ProviderService
        svc = ProviderService()
        svc.instances = {}
        return svc

    def test_get_provider_creates_new(self, service):
        """get_provider creates a new provider if not cached."""
        provider = service.get_provider("openai", "my-openai", "https://api.openai.com/v1", "sk-key")
        assert provider is not None
        assert "my-openai" in service.instances

    def test_get_provider_returns_cached(self, service):
        """get_provider returns existing instance from cache."""
        from services.provider_service import OpenAIProvider
        cached = OpenAIProvider("my-openai", "https://api.openai.com/v1", "sk-key")
        service.instances["my-openai"] = cached

        provider = service.get_provider("openai", "my-openai", "https://other-url.com", "other-key")
        assert provider is cached
        assert provider.base_url == "https://api.openai.com/v1"

    def test_remove_provider(self, service):
        """remove_provider deletes provider from instances."""
        from services.provider_service import OpenAIProvider
        service.instances["test"] = OpenAIProvider("test", "https://api.test.com", "key")
        service.remove_provider("test")
        assert "test" not in service.instances

    def test_remove_provider_nonexistent(self, service):
        """remove_provider is idempotent for nonexistent names."""
        service.remove_provider("nonexistent")

    @pytest.mark.asyncio
    async def test_test_connection_success(self, service):
        """test_connection returns health check result with latency."""
        with patch("services.provider_service.ProviderFactory.create") as mock_create:
            mock_provider = MagicMock()
            mock_provider.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_create.return_value = mock_provider

            result = await service.test_connection("openai", "https://api.openai.com/v1", "sk-key")

        assert result["status"] == "healthy"
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_test_connection_error(self, service):
        """test_connection returns error status on exception."""
        with patch("services.provider_service.ProviderFactory.create") as mock_create:
            mock_provider = MagicMock()
            mock_provider.health_check = AsyncMock(side_effect=Exception("Something went wrong"))
            mock_create.return_value = mock_provider

            result = await service.test_connection("openai", "https://api.openai.com/v1", "sk-key")

        assert result["status"] == "error"
        assert "message" in result
