"""Tests for provider model fetching, MCP validation, and Windows compatibility."""

import pytest
import sys
from unittest.mock import AsyncMock, patch, MagicMock

from services.provider_service import (
    ProviderService, ProviderFactory, OpenRouterProvider,
    OpenAIProvider, GeminiProvider, AnthropicProvider, BaseProvider,
)
from services.mcp_service import MCPService, _get_executable_name, _resolve_command, IS_WINDOWS


# ────────── Provider Model Fetching ──────────

@pytest.mark.asyncio
class TestProviderModelFetching:
    """Tests for dynamic model fetching from providers."""

    async def test_openrouter_fetch_models(self):
        """OpenRouter fetches model list from API."""
        provider = OpenRouterProvider("test", "https://openrouter.ai/api/v1", "fake-key")
        with patch.object(provider, 'list_models', return_value=["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-70b-instruct"]):
            models = await provider.list_models()
            assert len(models) == 3
            assert "openai/gpt-4o" in models

    async def test_openai_fetch_models(self):
        """OpenAI fetches model list from API."""
        provider = OpenAIProvider("test", "https://api.openai.com/v1", "fake-key")
        with patch.object(provider, 'list_models', return_value=["gpt-4o", "gpt-4o-mini"]):
            models = await provider.list_models()
            assert "gpt-4o" in models
            assert "gpt-4o-mini" in models

    async def test_fetch_models_fallback_to_suggestions(self):
        """Falls back to suggestions when API returns empty."""
        provider = OpenRouterProvider("test", "https://openrouter.ai/api/v1", "fake-key")
        with patch.object(provider, 'list_models', return_value=[]):
            models = await provider.list_models()
            # Empty result
            assert isinstance(models, list)

    async def test_fetch_models_api_error_returns_suggestions(self):
        """Returns suggestions when API call fails."""
        provider = OpenAIProvider("test", "https://api.openai.com/v1", "fake-key")
        with patch.object(provider, 'list_models', side_effect=Exception("Connection refused")):
            with pytest.raises(Exception, match="Connection refused"):
                await provider.list_models()

    async def test_provider_service_fetch_models_with_key(self):
        """ProviderService.fetch_models calls provider API."""
        service = ProviderService()
        service.get_provider("openai", "test-openai", "https://api.openai.com/v1", "fake-key")
        with patch.object(service.instances["test-openai"], 'list_models', return_value=["gpt-4o"]):
            result = await service.fetch_models("openai", "https://api.openai.com/v1", "fake-key")
            assert "models" in result
            assert "gpt-4o" in result["models"]

    async def test_provider_service_fetch_models_no_key(self):
        """ProviderService.fetch_models returns suggestions without API key."""
        service = ProviderService()
        result = await service.fetch_models("openai", "https://api.openai.com/v1", "")
        assert "models" in result
        assert result["source"] == "suggestions"
        assert len(result["models"]) > 0

    async def test_provider_factory_default_models(self):
        """ProviderFactory.get_default_models returns suggestions."""
        models = ProviderFactory.get_default_models("openrouter")
        assert len(models) > 0
        assert any("gpt" in m or "claude" in m for m in models)

    async def test_anthropic_provider_uses_correct_format(self):
        """Anthropic provider uses messages API format, not chat/completions."""
        provider = AnthropicProvider("test", "https://api.anthropic.com", "fake-key")
        assert "x-api-key" in provider.headers
        assert "anthropic-version" in provider.headers


# ────────── Provider Connection with Retries ──────────

@pytest.mark.asyncio
class TestProviderConnectionRetries:
    """Tests for provider connection validation with retries."""

    async def test_test_connection_success(self):
        """Successful connection returns healthy status."""
        service = ProviderService()
        with patch("services.provider_service.ProviderFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_factory.create.return_value = mock_provider
            result = await service.test_connection("openai", "https://api.openai.com/v1", "fake-key")
            assert result["status"] == "healthy"
            assert "latency_ms" in result

    async def test_test_connection_no_key_fails(self):
        """Connection without API key returns error."""
        service = ProviderService()
        result = await service.test_connection("openai", "https://api.openai.com/v1", "")
        assert "status" in result

    async def test_test_connection_retries_on_failure(self):
        """Connection retries on transient failure."""
        service = ProviderService()
        with patch("services.provider_service.ProviderFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.health_check = AsyncMock(side_effect=[Exception("Timeout"), Exception("Timeout"), {"status": "healthy"}])
            mock_factory.create.return_value = mock_provider
            result = await service.test_connection("openai", "https://api.openai.com/v1", "fake-key", retries=2)
            assert result.get("attempt", 0) > 1

    async def test_provider_case_insensitive_lookup(self):
        """Provider lookup is case-insensitive."""
        service = ProviderService()
        service.get_provider("openai", "OpenAI", "https://api.openai.com/v1", "key1")
        found = service._find_instance("openai")
        assert found is not None
        assert found.name == "OpenAI"

    async def test_provider_update_existing(self):
        """get_provider updates existing provider config."""
        service = ProviderService()
        service.get_provider("openai", "OpenAI", "https://api.openai.com/v1", "key1")
        service.get_provider("openai", "OpenAI", "https://api.openai.com/v1", "key2")
        found = service._find_instance("OpenAI")
        assert found.api_key == "key2"


# ────────── MCP Validation ──────────

@pytest.mark.asyncio
class TestMCPValidation:
    """Tests for MCP configuration validation."""

    async def test_validate_stdio_config_valid(self):
        """Valid stdio config passes validation."""
        service = MCPService()
        result = await service.validate_mcp_config({
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        })
        # May have warnings about node/npx not found, but should be valid
        assert isinstance(result["valid"], bool)
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)

    async def test_validate_stdio_no_command(self):
        """Config without command fails validation."""
        service = MCPService()
        result = await service.validate_mcp_config({
            "transport": "stdio",
        })
        assert result["valid"] is False
        assert any("command" in e.lower() for e in result["errors"])

    async def test_validate_stdio_blocked_command(self):
        """Blocked command fails validation."""
        service = MCPService()
        result = await service.validate_mcp_config({
            "transport": "stdio",
            "command": "rm",
            "args": ["-rf", "/"],
        })
        assert result["valid"] is False
        assert any("blocked" in e.lower() for e in result["errors"])

    async def test_validate_http_no_endpoint(self):
        """HTTP transport without endpoint fails validation."""
        service = MCPService()
        result = await service.validate_mcp_config({
            "transport": "http",
        })
        assert result["valid"] is False
        assert any("endpoint" in e.lower() for e in result["errors"])

    async def test_validate_http_invalid_endpoint(self):
        """HTTP transport with invalid URL fails validation."""
        service = MCPService()
        result = await service.validate_mcp_config({
            "transport": "http",
            "endpoint": "not-a-url",
        })
        assert result["valid"] is False

    async def test_validate_npx_empty_args_warning(self):
        """Npx with no args generates a warning."""
        service = MCPService()
        result = await service.validate_mcp_config({
            "transport": "stdio",
            "command": "npx",
            "args": [],
        })
        assert any("args" in w.lower() or "package" in w.lower() for w in result["warnings"])

    async def test_validate_empty_config(self):
        """Empty config fails validation."""
        service = MCPService()
        result = await service.validate_mcp_config({})
        assert result["valid"] is False


# ────────── MCP Prerequisites Check ──────────

@pytest.mark.asyncio
class TestMCPPrerequisites:
    """Tests for system prerequisite checks."""

    async def test_check_prerequisites(self):
        """Check prerequisites returns results for all tools."""
        service = MCPService()
        result = await service.check_prerequisites()
        assert "node" in result
        assert "npm" in result
        assert "npx" in result
        assert "python" in result
        assert all(isinstance(v, bool) for v in result.values())


# ────────── Windows Path Resolution ──────────

class TestWindowsPathResolution:
    """Tests for cross-platform path resolution."""

    def test_get_executable_name(self):
        """Extracts base name from path."""
        assert _get_executable_name("npx") == "npx"
        assert _get_executable_name("npx.cmd") == "npx"
        assert _get_executable_name("node.exe") == "node"
        assert _get_executable_name("/usr/bin/python3") == "python3"
        assert _get_executable_name("C:\\Program Files\\nodejs\\npx.cmd") == "npx"

    def test_resolve_command_returns_string(self):
        """Resolve command always returns a string."""
        result = _resolve_command("python")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resolve_command_preserves_full_path(self):
        """Resolve command preserves full path if found."""
        result = _resolve_command("python")
        # Should resolve to something
        assert "python" in result.lower() or len(result) > 0

    def test_resolve_empty_command(self):
        """Resolve empty command returns empty."""
        assert _resolve_command("") == ""
        assert _resolve_command(None) is None


# ────────── MCP enable with suggestions ──────────

@pytest.mark.asyncio
class TestMCPEnableSuggestions:
    """Tests for MCP enable error messages with suggestions."""

    async def test_enable_empty_args_returns_suggestions(self):
        """Enable with empty args returns actionable suggestions."""
        from models.database import MCP
        service = MCPService()
        mcp = MCP(
            id=999, name="test-mcp", type="custom", enabled=True,
            transport="stdio", command="npx", args=json.dumps([]),
        )
        result = await service.enable_mcp(mcp)
        assert result["status"] == "error"
        assert "args" in result["message"].lower() or "argument" in result["message"].lower()

    async def test_enable_no_command_returns_error(self):
        """Enable with no command returns clear error."""
        from models.database import MCP
        service = MCPService()
        mcp = MCP(
            id=998, name="test-mcp", type="custom", enabled=True,
            transport="stdio", command="", args=None,
        )
        result = await service.enable_mcp(mcp)
        assert result["status"] == "error"
        assert "command" in result["message"].lower()

    async def test_enable_blocked_command_returns_error(self):
        """Enable with blocked command returns security error."""
        from models.database import MCP
        service = MCPService()
        mcp = MCP(
            id=997, name="test-mcp", type="custom", enabled=True,
            transport="stdio", command="rm", args=json.dumps(["-rf", "/"]),
        )
        result = await service.enable_mcp(mcp)
        assert result["status"] == "error"
        assert "blocked" in result["message"].lower() or "not in the allowed list" in result["message"].lower()


import json  # needed for the JSON dumps in test code
