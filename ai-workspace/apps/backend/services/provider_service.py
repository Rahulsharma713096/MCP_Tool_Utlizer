"""Online Provider System - Dynamic provider abstraction layer."""

import asyncio
from typing import Optional, Any
import time

import httpx

from core.security import encrypt_api_key, decrypt_api_key
from core.logging import log_manager

logger = log_manager.get_logger("provider_service")


class BaseProvider:
    """Base class for all AI providers."""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self._setup_auth()

    def _setup_auth(self):
        """Set up authentication headers. Override in subclasses."""
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def chat(self, model: str, messages: list[dict], stream: bool = False) -> dict:
        """Send a chat request. Override in subclasses."""
        raise NotImplementedError

    async def list_models(self) -> list[str]:
        """Fetch available models. Override in subclasses."""
        raise NotImplementedError

    async def health_check(self) -> dict:
        """Check provider health."""
        raise NotImplementedError


class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider."""

    def _setup_auth(self):
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(self, model: str, messages: list[dict], stream: bool = False) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={"model": model, "messages": messages, "stream": stream},
            )
            return response.json()

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.error("openrouter_list_models_error", error=str(e))
            return []

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}


class OpenAIProvider(BaseProvider):
    """OpenAI API provider (also works with compatible APIs)."""

    async def chat(self, model: str, messages: list[dict], stream: bool = False) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={"model": model, "messages": messages, "stream": stream},
            )
            return response.json()

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    async def chat(self, model: str, messages: list[dict], stream: bool = False) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            url = f"{self.base_url}/v1beta/models/{model}:generateContent"
            contents = []
            for msg in messages:
                if msg["role"] in ("user", "assistant"):
                    contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
            response = await client.post(
                url,
                params={"key": self.api_key},
                json={"contents": contents},
            )
            return response.json()

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"{self.base_url}/v1beta/models"
                response = await client.get(url, params={"key": self.api_key})
                data = response.json()
                return [m["name"].replace("models/", "") for m in data.get("models", [])]
        except Exception:
            return []

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                url = f"{self.base_url}/v1beta/models"
                response = await client.get(url, params={"key": self.api_key})
                return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}


class ProviderFactory:
    """Factory for creating provider instances."""

    PROVIDER_MAP = {
        "openrouter": OpenRouterProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "zai": OpenAIProvider,  # Z.ai uses OpenAI-compatible API
        "claude": OpenAIProvider,  # Basic OpenAI-compatible for now
    }

    @classmethod
    def create(cls, provider_type: str, name: str, base_url: str, api_key: Optional[str] = None) -> BaseProvider:
        provider_class = cls.PROVIDER_MAP.get(provider_type.lower())
        if not provider_class:
            # Default to OpenAI-compatible
            provider_class = OpenAIProvider
        return provider_class(name=name, base_url=base_url, api_key=api_key)


class ProviderService:
    """Manages multiple AI providers."""

    def __init__(self):
        self.instances: dict[str, BaseProvider] = {}

    def get_provider(self, provider_type: str, name: str, base_url: str, api_key: Optional[str] = None) -> BaseProvider:
        """Get or create a provider instance."""
        if name in self.instances:
            return self.instances[name]
        provider = ProviderFactory.create(provider_type, name, base_url, api_key)
        self.instances[name] = provider
        return provider

    def remove_provider(self, name: str):
        """Remove a provider instance."""
        self.instances.pop(name, None)

    async def test_connection(self, provider_type: str, base_url: str, api_key: str) -> dict:
        """Test a provider connection before saving."""
        provider = ProviderFactory.create(provider_type, "test", base_url, api_key)
        try:
            start = time.time()
            result = await provider.health_check()
            latency = (time.time() - start) * 1000
            return {**result, "latency_ms": round(latency, 2)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global provider service instance
provider_service = ProviderService()
