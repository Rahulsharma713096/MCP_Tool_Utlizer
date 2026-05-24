"""Chat Service - Core AI interaction engine with streaming and MCP tool calling."""

import asyncio
import json
import uuid
from typing import Optional, AsyncGenerator
from datetime import datetime, timezone

import httpx

from models.database import Chat, Session
from services.ollama_service import OllamaService
from services.provider_service import ProviderService, provider_service
from core.logging import log_manager

logger = log_manager.get_logger("chat_service")


class ChatService:
    """Manages chat sessions, streaming, and tool calling."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}
        self.ollama_service = OllamaService()

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new chat session."""
        sid = session_id or str(uuid.uuid4())
        self.sessions[sid] = {
            "id": sid,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active_provider": None,
            "active_model": None,
        }
        return sid

    async def send_message(
        self,
        session_id: str,
        content: str,
        provider: str = "ollama",
        model: Optional[str] = None,
    ) -> dict:
        """Send a message and get a response."""
        session = self.sessions.get(session_id)
        if not session:
            session_id = self.create_session(session_id)
            session = self.sessions[session_id]

        # Add user message
        session["messages"].append({"role": "user", "content": content})

        if provider == "ollama":
            response = await self._chat_with_ollama(model or "llama3", session["messages"])
        else:
            response = await self._chat_with_provider(provider, model, session["messages"])

        # Add assistant response
        session["messages"].append({"role": "assistant", "content": response.get("content", "")})

        return {
            "session_id": session_id,
            "response": response.get("content", ""),
            "provider": provider,
            "model": model,
        }

    async def stream_message(
        self,
        session_id: str,
        content: str,
        provider: str = "ollama",
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response token by token."""
        session = self.sessions.get(session_id)
        if not session:
            session_id = self.create_session(session_id)
            session = self.sessions[session_id]

        session["messages"].append({"role": "user", "content": content})

        full_response = ""
        if provider == "ollama":
            async for token in self._stream_ollama(model or "llama3", session["messages"]):
                full_response += token
                yield json.dumps({"type": "token", "content": token}) + "\n"
        else:
            async for token in self._stream_provider(provider, model, session["messages"]):
                full_response += token
                yield json.dumps({"type": "token", "content": token}) + "\n"

        session["messages"].append({"role": "assistant", "content": full_response})
        yield json.dumps({"type": "done", "content": full_response}) + "\n"

    async def _chat_with_ollama(self, model: str, messages: list[dict]) -> dict:
        """Send chat request to local Ollama."""
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    "http://localhost:11434/api/chat",
                    json={"model": model, "messages": messages, "stream": False},
                )
                if response.status_code == 200:
                    data = response.json()
                    return {"content": data.get("message", {}).get("content", "")}
                return {"content": f"Error: {response.text}"}
        except httpx.ConnectError:
            return {"content": "⚠️ Ollama is not running. Please start Ollama first."}
        except Exception as e:
            logger.error("ollama_chat_error", error=str(e))
            return {"content": f"⚠️ Error: {str(e)}"}

    async def _stream_ollama(self, model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Stream response from local Ollama."""
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    "http://localhost:11434/api/chat",
                    json={"model": model, "messages": messages, "stream": True},
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield f"⚠️ Error: {str(e)}"

    async def _chat_with_provider(self, provider_name: str, model: Optional[str], messages: list[dict]) -> dict:
        """Send chat request to an online provider."""
        provider_instance = provider_service.instances.get(provider_name)
        if not provider_instance:
            return {"content": f"⚠️ Provider '{provider_name}' not configured."}

        try:
            result = await provider_instance.chat(model or "gpt-3.5-turbo", messages)
            if "choices" in result:
                content = result["choices"][0]["message"]["content"]
            elif "candidates" in result:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                content = str(result)
            return {"content": content}
        except Exception as e:
            logger.error("provider_chat_error", provider=provider_name, error=str(e))
            return {"content": f"⚠️ Provider error: {str(e)}"}

    async def _stream_provider(self, provider_name: str, model: Optional[str], messages: list[dict]) -> AsyncGenerator[str, None]:
        """Stream response from an online provider."""
        provider_instance = provider_service.instances.get(provider_name)
        if not provider_instance:
            yield f"⚠️ Provider '{provider_name}' not configured."
            return

        try:
            result = await provider_instance.chat(model or "gpt-3.5-turbo", messages, stream=False)
            if "choices" in result:
                content = result["choices"][0]["message"]["content"]
            elif "candidates" in result:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                content = str(result)
            # For now, return full content since streaming varies by provider
            yield content
        except Exception as e:
            yield f"⚠️ Error: {str(e)}"

    def get_session_history(self, session_id: str) -> list[dict]:
        """Get message history for a session."""
        session = self.sessions.get(session_id)
        return session["messages"] if session else []

    def delete_session(self, session_id: str):
        """Delete a chat session."""
        self.sessions.pop(session_id, None)


# Global chat service instance
chat_service = ChatService()
