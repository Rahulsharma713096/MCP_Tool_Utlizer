"""Online Provider System - Dynamic provider abstraction layer with model fetching."""

import asyncio
from typing import Optional, Any
import time
import sys
import shutil

import httpx

from core.logging import log_manager

logger = log_manager.get_logger("provider_service")


class BaseProvider:
    """Base class for all AI providers."""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers: dict[str, str] = {}
        if api_key:
            self._setup_auth()

    def _setup_auth(self):
        """Set up authentication headers. Override in subclasses."""
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def chat(self, model: str, messages: list[dict], stream: bool = False, tools: Optional[list[dict]] = None) -> dict:
        """Send a chat request. Override in subclasses."""
        raise NotImplementedError

    async def list_models(self) -> list[str]:
        """Fetch available models. Override in subclasses."""
        raise NotImplementedError

    async def health_check(self) -> dict:
        """Check provider health."""
        raise NotImplementedError

    def get_model_suggestions(self) -> list[str]:
        """Return common model suggestions for this provider. Override in subclasses."""
        return []


class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider."""

    def _setup_auth(self):
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-workspace.app",
            "X-Title": "AI Workspace",
        }

    async def chat(self, model: str, messages: list[dict], stream: bool = False, tools: Optional[list[dict]] = None) -> dict:
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": stream}
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            return response.json()

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                data = response.json()
                return [m["id"] for m in data.get("data", []) if m.get("id")]
        except Exception as e:
            logger.error("openrouter_list_models_error", error=str(e))
            return self.get_model_suggestions()

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}

    def get_model_suggestions(self) -> list[str]:
        return [
            "openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-3.5-turbo",
            "anthropic/claude-3.5-sonnet", "anthropic/claude-3-haiku",
            "google/gemini-2.0-flash-exp", "google/gemini-1.5-pro",
            "meta-llama/llama-3.1-405b-instruct", "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large-latest", "deepseek/deepseek-r1",
            "qwen/qwen-2.5-72b-instruct",
        ]


class OpenAIProvider(BaseProvider):
    """OpenAI API provider (also works with compatible APIs)."""

    async def chat(self, model: str, messages: list[dict], stream: bool = False, tools: Optional[list[dict]] = None) -> dict:
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": stream}
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            return response.json()

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                data = response.json()
                return [m["id"] for m in data.get("data", []) if m.get("id")]
        except Exception as e:
            logger.error("openai_list_models_error", error=str(e))
            return self.get_model_suggestions()

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}

    def get_model_suggestions(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    def _setup_auth(self):
        self.headers = {"Content-Type": "application/json"}

    async def chat(self, model: str, messages: list[dict], stream: bool = False, tools: Optional[list[dict]] = None) -> dict:
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
            async with httpx.AsyncClient(timeout=15) as client:
                url = f"{self.base_url}/v1beta/models"
                response = await client.get(url, params={"key": self.api_key})
                data = response.json()
                return [m["name"].replace("models/", "") for m in data.get("models", [])]
        except Exception as e:
            logger.error("gemini_list_models_error", error=str(e))
            return self.get_model_suggestions()

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"{self.base_url}/v1beta/models"
                response = await client.get(url, params={"key": self.api_key})
                return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}

    def get_model_suggestions(self) -> list[str]:
        return ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    def _setup_auth(self):
        self.headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def chat(self, model: str, messages: list[dict], stream: bool = False, tools: Optional[list[dict]] = None) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] in ("user", "assistant"):
                    chat_messages.append({"role": msg["role"], "content": msg["content"]})
            payload: dict[str, Any] = {"model": model, "max_tokens": 4096, "messages": chat_messages}
            if system_msg:
                payload["system"] = system_msg
            if tools:
                payload["tools"] = tools
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=self.headers,
                json=payload,
            )
            data = response.json()
            content = data.get("content", [{}])[0].get("text", "")
            return {"choices": [{"message": {"content": content}}]}

    async def list_models(self) -> list[str]:
        return self.get_model_suggestions()

    async def health_check(self) -> dict:
        if not self.api_key:
            return {"status": "error", "message": "API key required"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/v1/messages",
                    headers=self.headers,
                )
                return {"status": "healthy" if response.status_code in (200, 400, 405) else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}

    def get_model_suggestions(self) -> list[str]:
        return [
            "claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", "claude-3-haiku-20240307",
        ]


class ProviderFactory:
    """Factory for creating provider instances."""

    PROVIDER_MAP = {
        "openrouter": OpenRouterProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "anthropic": AnthropicProvider,
        "claude": AnthropicProvider,
        "zai": OpenAIProvider,
    }

    @classmethod
    def create(cls, provider_type: str, name: str, base_url: str, api_key: Optional[str] = None) -> BaseProvider:
        provider_class = cls.PROVIDER_MAP.get(provider_type.lower())
        if not provider_class:
            provider_class = OpenAIProvider
        return provider_class(name=name, base_url=base_url, api_key=api_key)

    @classmethod
    def get_default_models(cls, provider_type: str) -> list[str]:
        """Get default model suggestions for a provider type."""
        provider_class = cls.PROVIDER_MAP.get(provider_type.lower(), OpenAIProvider)
        temp = provider_class(name="temp", base_url="", api_key=None)
        return temp.get_model_suggestions()


class ProviderService:
    """Manages multiple AI providers."""

    def __init__(self):
        self.instances: dict[str, BaseProvider] = {}

    def get_provider(self, provider_type: str, name: str, base_url: str, api_key: Optional[str] = None) -> BaseProvider:
        """Get or create a provider instance."""
        existing = self._find_instance(name)
        if existing:
            existing.base_url = base_url.rstrip("/")
            if api_key:
                existing.api_key = api_key
                existing._setup_auth()
            return existing
        provider = ProviderFactory.create(provider_type, name, base_url, api_key)
        self.instances[name] = provider
        return provider

    def _find_instance(self, name: str) -> Optional[BaseProvider]:
        """Find a provider instance by name (case-insensitive)."""
        for stored_name, inst in self.instances.items():
            if stored_name.lower() == name.lower():
                return inst
        return None

    def remove_provider(self, name: str):
        """Remove a provider instance."""
        existing = self._find_instance(name)
        if existing:
            for stored_name, inst in list(self.instances.items()):
                if inst is existing:
                    self.instances.pop(stored_name, None)
                    break

    async def test_connection(self, provider_type: str, base_url: str, api_key: str, retries: int = 2) -> dict:
        """Test a provider connection with retries."""
        last_error = None
        for attempt in range(retries + 1):
            provider = ProviderFactory.create(provider_type, "test", base_url, api_key)
            try:
                start = time.time()
                result = await provider.health_check()
                latency = (time.time() - start) * 1000
                if result.get("status") == "healthy":
                    return {**result, "latency_ms": round(latency, 2), "attempt": attempt + 1}
                last_error = result
            except Exception as e:
                last_error = {"status": "error", "message": str(e)}
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))
        return last_error or {"status": "error", "message": "Connection failed after retries"}

    async def fetch_models(self, provider_type: str, base_url: str, api_key: str) -> dict:
        """Fetch available models from a provider."""
        if not api_key:
            defaults = ProviderFactory.get_default_models(provider_type)
            return {"models": defaults, "source": "suggestions", "message": "No API key — showing suggested models"}
        provider = ProviderFactory.create(provider_type, "fetch", base_url, api_key)
        try:
            models = await provider.list_models()
            if models:
                return {"models": models, "source": "api", "count": len(models)}
            defaults = ProviderFactory.get_default_models(provider_type)
            return {"models": defaults, "source": "suggestions", "message": "API returned no models — showing suggestions"}
        except Exception as e:
            defaults = ProviderFactory.get_default_models(provider_type)
            return {"models": defaults, "source": "suggestions", "message": f"API error: {e} — showing suggestions"}


provider_service = ProviderService()
