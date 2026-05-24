"""Provider Service Tests - Covers PAPI test cases from test.txt."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
import httpx

from services.provider_service import (
    OpenRouterProvider,
    OpenAIProvider,
    GeminiProvider,
    ProviderFactory,
    ProviderService,
    provider_service,
)


@pytest.mark.asyncio
class TestProviderInstances:
    """PAPI-001 to PAPI-004: Provider connection tests"""

    async def test_openrouter_connection(self):
        """PAPI-001: Positive - OpenRouter connect"""
        provider = OpenRouterProvider(
            name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
        )
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await provider.health_check()
            assert result["status"] == "healthy"

    async def test_gemini_connection(self):
        """PAPI-002: Positive - Gemini connect"""
        provider = GeminiProvider(
            name="Gemini",
            base_url="https://generativelanguage.googleapis.com",
            api_key="test-key",
        )
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await provider.health_check()
            assert result["status"] == "healthy"

    async def test_invalid_api_key(self):
        """PAPI-004: Negative - Invalid API key"""
        provider = OpenRouterProvider(
            name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            api_key="invalid-key",
        )
        mock_response = AsyncMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await provider.health_check()
            assert result["status"] == "unhealthy"

    async def test_network_timeout(self):
        """PAPI-006: Negative - Network timeout"""
        provider = OpenAIProvider(
            name="OpenAI",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection timeout")):
            result = await provider.health_check()
            assert result["status"] == "unreachable"

    async def test_openrouter_list_models(self):
        """PAPI-001: Fetch available models"""
        provider = OpenRouterProvider(
            name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
        )
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "mistral-large"}, {"id": "deepseek/deepseek-r1"}]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            models = await provider.list_models()
            assert len(models) == 2
            assert "mistral-large" in models

    async def test_openai_chat(self):
        """PAPI-001: Send chat request"""
        provider = OpenAIProvider(
            name="OpenAI",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}]
        }

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await provider.chat(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hi"}],
            )
            assert result["choices"][0]["message"]["content"] == "Hello!"


class TestProviderFactory:
    """PAPI: Provider factory tests"""

    def test_create_openrouter_provider(self):
        provider = ProviderFactory.create("openrouter", "Test", "https://openrouter.ai/api/v1", "key")
        assert isinstance(provider, OpenRouterProvider)
        assert provider.name == "Test"

    def test_create_gemini_provider(self):
        provider = ProviderFactory.create("gemini", "Test", "https://generativelanguage.googleapis.com", "key")
        assert isinstance(provider, GeminiProvider)

    def test_create_default_provider(self):
        provider = ProviderFactory.create("unknown", "Test", "https://unknown.api/v1", "key")
        assert isinstance(provider, OpenAIProvider)

    def test_create_without_api_key(self):
        provider = ProviderFactory.create("openrouter", "Test", "https://openrouter.ai/api/v1")
        assert provider.api_key is None


@pytest.mark.asyncio
class TestProviderService:
    """PAPI-007: Provider failover and management tests"""

    async def test_add_and_get_provider(self):
        service = ProviderService()
        provider = service.get_provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "key")
        assert provider is not None
        assert provider.name == "OpenRouter"

        # Should return cached instance
        cached = service.get_provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1")
        assert cached is provider

    async def test_remove_provider(self):
        service = ProviderService()
        service.get_provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "key")
        assert "OpenRouter" in service.instances

        service.remove_provider("OpenRouter")
        assert "OpenRouter" not in service.instances

    async def test_test_connection_success(self):
        """PAPI-005: Positive - Provider healthcheck"""
        service = ProviderService()
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await service.test_connection("openrouter", "https://openrouter.ai/api/v1", "test-key")
            assert result["status"] == "healthy"
            assert "latency_ms" in result

    async def test_test_connection_failure(self):
        """PAPI-005: Negative - Provider healthcheck fails"""
        service = ProviderService()
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection failed")):
            result = await service.test_connection("openrouter", "https://openrouter.ai/api/v1", "bad-key")
            # The health_check returns "unreachable" on connection failure
            assert result["status"] in ("error", "unreachable")
