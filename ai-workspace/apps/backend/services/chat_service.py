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

# Maximum tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 10


class ChatService:
    """Manages chat sessions, streaming, and tool calling.

    Integrates MCP tools by:
    1. Collecting tool definitions from running MCP servers
    2. Passing them to the LLM as function definitions
    3. Handling tool call responses from the LLM
    4. Executing tool calls via MCP service and feeding results back
    """

    def __init__(self, mcp_service=None):
        self.sessions: dict[str, dict] = {}
        self.ollama_service = OllamaService()
        self.mcp_service = mcp_service

    def _build_system_prompt(self, tools: list[dict]) -> str:
        """Build a system prompt that tells the LLM about available MCP tools."""
        if not tools:
            return "You are a helpful AI assistant. You can answer questions and help with tasks."
        tool_names = [t["function"]["name"] for t in tools if "function" in t]
        tool_desc = "\n".join(
            f"  - {t.get('function', {}).get('name', 'unknown')}: {t.get('function', {}).get('description', '')}"
            for t in tools if "function" in t
        )
        return (
            "You are a helpful AI assistant with access to MCP (Model Context Protocol) tools.\n"
            "You have the following tools available. When the user asks a task that a tool can perform, "
            "CALL THE TOOL using the function calling interface - do NOT just describe steps.\n"
            "Available tools:\n"
            f"{tool_desc}\n\n"
            "IMPORTANT: Always use a tool when one is applicable. If a user asks you to manage files, "
            "browse the web, query databases, or perform any automated task, call the appropriate tool "
            "instead of giving instructions on how to do it manually."
        )

    def create_session(self, session_id: Optional[str] = None, tools: Optional[list[dict]] = None) -> str:
        """Create a new chat session."""
        sid = session_id or str(uuid.uuid4())
        self.sessions[sid] = {
            "id": sid,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active_provider": None,
            "active_model": None,
        }
        # Add system prompt with tool descriptions if tools are available
        if tools:
            system_prompt = self._build_system_prompt(tools)
            self.sessions[sid]["messages"].append({"role": "system", "content": system_prompt})
        return sid

    # ────────── MCP Tool Helpers ──────────

    async def _collect_tools(self) -> list[dict]:
        """Async: collect tool definitions from running MCPs."""
        if not self.mcp_service:
            return []
        try:
            tools = await self.mcp_service.get_all_enabled_tools()
            if tools:
                logger.info("mcp_tools_collected", count=len(tools))
            return tools
        except Exception as e:
            logger.warning("collect_tools_error", error=str(e))
            return []

    async def _execute_mcp_tool(self, tool_call: dict) -> dict:
        """Execute an MCP tool call and return the result.

        The tool_call contains:
          - function.name: "{mcp_name}__{tool_name}"
          - function.arguments: JSON string
        """
        if not self.mcp_service:
            return {"role": "tool", "content": "Error: MCP service not available", "tool_call_id": tool_call.get("id", "")}

        function_info = tool_call.get("function", {})
        qualified_name = function_info.get("name", "")

        # Parse the qualified name: "{mcp_name}__{tool_name}"
        if "__" in qualified_name:
            mcp_name, raw_tool_name = qualified_name.split("__", 1)
        else:
            return {"role": "tool", "content": f"Error: Invalid tool name format '{qualified_name}'", "tool_call_id": tool_call.get("id", "")}

        # Find the MCP ID by name
        mcp_id = None
        for mid, info in self.mcp_service._mcp_info.items():
            if info.get("name") == mcp_name:
                mcp_id = mid
                break

        if mcp_id is None:
            return {"role": "tool", "content": f"Error: MCP '{mcp_name}' not found", "tool_call_id": tool_call.get("id", "")}

        # Parse arguments
        try:
            args = json.loads(function_info.get("arguments", "{}"))
        except (json.JSONDecodeError, TypeError):
            args = {}

        # Execute the tool
        result = await self.mcp_service.execute_tool(mcp_id, raw_tool_name, args)

        if result["status"] == "success":
            content = result.get("result", "")
            if isinstance(content, list):
                # MCP content can be a list of content items
                texts = [item.get("text", json.dumps(item)) for item in content if isinstance(item, dict)]
                content = "\n".join(texts)
            elif not isinstance(content, str):
                content = json.dumps(content)
            return {"role": "tool", "content": content, "tool_call_id": tool_call.get("id", ""), "name": raw_tool_name}
        else:
            return {"role": "tool", "content": f"Error: {result.get('message', 'Unknown error')}", "tool_call_id": tool_call.get("id", ""), "name": raw_tool_name}

    # ────────── Message Sending ──────────

    async def send_message(
        self,
        session_id: str,
        content: str,
        provider: str = "ollama",
        model: Optional[str] = None,
        tool_events: Optional[list[dict]] = None,
    ) -> dict:
        """Send a message and get a response, with MCP tool support.

        tool_events: Optional list to collect tool_call/tool_result events for the caller.
        """
        # Collect MCP tools first so system prompt can include them
        tools = await self._collect_tools()

        session = self.sessions.get(session_id)
        if not session:
            session_id = self.create_session(session_id, tools=tools)
            session = self.sessions[session_id]

        # Add user message
        session["messages"].append({"role": "user", "content": content})

        if provider == "ollama":
            response = await self._chat_with_ollama_tools(model or "llama3", session["messages"], tools, tool_events)
        else:
            response = await self._chat_with_provider_tools(provider, model, session["messages"], tools, tool_events)

        # Add final assistant response
        final_content = response.get("content", "")
        if final_content:
            session["messages"].append({"role": "assistant", "content": final_content})

        return {
            "session_id": session_id,
            "response": final_content,
            "provider": provider,
            "model": model,
            "tool_events": tool_events or [],
        }

    async def stream_message(
        self,
        session_id: str,
        content: str,
        provider: str = "ollama",
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response token by token, with MCP tool support.

        Yields JSON events:
          - {"type": "token", "content": "..."}
          - {"type": "tool_call", "name": "...", "args": {...}}
          - {"type": "tool_result", "name": "...", "content": "..."}
          - {"type": "done", "content": "..."}
        """
        # Collect MCP tools (do this before session so system prompt can include them)
        tools = await self._collect_tools()

        session = self.sessions.get(session_id)
        if not session:
            session_id = self.create_session(session_id, tools=tools)
            session = self.sessions[session_id]

        session["messages"].append({"role": "user", "content": content})

        if tools:
            logger.info("mcp_tools_available_for_chat", count=len(tools))
            async for event in self._stream_with_tools(
                provider or "ollama", model, session["messages"], tools
            ):
                yield event + "\n"
        elif provider == "ollama":
            async for token in self._stream_ollama(model or "llama3", session["messages"]):
                yield json.dumps({"type": "token", "content": token}) + "\n"
            full_response = session["messages"][-1]["content"] if session["messages"][-1]["role"] == "assistant" else ""
            yield json.dumps({"type": "done", "content": full_response}) + "\n"
        else:
            async for token in self._stream_provider(provider, model, session["messages"]):
                yield json.dumps({"type": "token", "content": token}) + "\n"
            full_response = session["messages"][-1]["content"] if session["messages"][-1]["role"] == "assistant" else ""
            yield json.dumps({"type": "done", "content": full_response}) + "\n"

    # ────────── Tool-Integrated Chat ──────────

    async def _chat_with_ollama_tools(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict],
        tool_events: list[dict] | None = None,
    ) -> dict:
        """Chat with Ollama, handling tool calls in a loop."""
        iteration = 0

        while iteration < MAX_TOOL_ITERATIONS:
            iteration += 1

            # Build the request with tools
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
            }
            if tools:
                # Remove internal fields before sending to LLM
                clean_tools = []
                for t in tools:
                    clean_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"],
                        },
                    })
                payload["tools"] = clean_tools

            try:
                async with httpx.AsyncClient(timeout=300) as client:
                    response = await client.post(
                        "http://localhost:11434/api/chat",
                        json=payload,
                    )

                    if response.status_code != 200:
                        return {"content": f"Error: {response.text}"}

                    data = response.json()
                    msg = data.get("message", {})

                    # Check for tool calls
                    tool_calls = msg.get("tool_calls", [])
                    if not tool_calls:
                        # No tool calls — return the text response
                        return {"content": msg.get("content", "")}

                    # Add assistant message with tool calls to conversation
                    messages.append({
                        "role": "assistant",
                        "content": msg.get("content") or None,
                        "tool_calls": tool_calls,
                    })

                    # Execute each tool call
                    for tc in tool_calls:
                        # Emit tool_call event
                        if tool_events is not None:
                            tool_events.append({
                                "type": "tool_call",
                                "name": tc.get("function", {}).get("name", ""),
                                "args": tc.get("function", {}).get("arguments", "{}"),
                            })

                        tool_result = await self._execute_mcp_tool(tc)
                        messages.append(tool_result)

                        # Emit tool_result event
                        if tool_events is not None:
                            tool_events.append({
                                "type": "tool_result",
                                "name": tool_result.get("name", ""),
                                "content": tool_result.get("content", ""),
                            })

            except httpx.ConnectError:
                return {"content": "⚠️ Ollama is not running. Please start Ollama first."}
            except Exception as e:
                logger.error("ollama_tool_chat_error", iteration=iteration, error=str(e))
                return {"content": f"⚠️ Error: {str(e)}"}

        return {"content": "⚠️ Reached maximum tool call iterations. Please simplify your request."}

    async def _stream_with_tools(
        self,
        provider: str,
        model: Optional[str],
        messages: list[dict],
        tools: list[dict],
    ) -> AsyncGenerator[str, None]:
        """Stream chat with MCP tool support. Runs non-streaming tool loop internally."""
        tool_events: list[dict] = []

        if provider == "ollama":
            response = await self._chat_with_ollama_tools(model or "llama3", messages, tools, tool_events)
        else:
            response = await self._chat_with_provider_tools(provider, model, messages, tools, tool_events)

        # Yield tool events first
        for event in tool_events:
            yield json.dumps(event)

        # Yield the final content as tokens
        content = response.get("content", "")
        if content:
            # Simulate streaming by yielding the full content
            yield json.dumps({"type": "token", "content": content})

        # Add final assistant response to session
        if content:
            messages.append({"role": "assistant", "content": content})

        yield json.dumps({"type": "done", "content": content})

    def _get_provider(self, name: str):
        """Get provider instance with case-insensitive lookup."""
        for stored, inst in provider_service.instances.items():
            if stored.lower() == name.lower():
                return inst
        return None

    async def _chat_with_provider_tools(
        self,
        provider_name: str,
        model: Optional[str],
        messages: list[dict],
        tools: list[dict],
        tool_events: list[dict] | None = None,
    ) -> dict:
        """Chat with a provider, handling tool calls in a loop."""
        provider_instance = self._get_provider(provider_name)
        if not provider_instance:
            return {"content": f"⚠️ Provider '{provider_name}' not configured. Add it in Providers section first."}

        iteration = 0
        while iteration < MAX_TOOL_ITERATIONS:
            iteration += 1

            try:
                # Prepare tools in OpenAI function calling format
                clean_tools = []
                for t in tools:
                    clean_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"],
                        },
                    })
                result = await provider_instance.chat(
                    model=model or "gpt-3.5-turbo",
                    messages=messages,
                    tools=clean_tools if clean_tools else None,
                )

                # Check for tool calls (OpenAI format)
                if "choices" in result and result["choices"]:
                    choice = result["choices"][0]
                    msg = choice.get("message", {})
                    tool_calls = msg.get("tool_calls", [])

                    if not tool_calls:
                        content = msg.get("content", "") or ""
                        return {"content": content}

                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": msg.get("content") or None,
                        "tool_calls": tool_calls,
                    })

                    for tc in tool_calls:
                        if tool_events is not None:
                            tool_events.append({
                                "type": "tool_call",
                                "name": tc.get("function", {}).get("name", ""),
                                "args": tc.get("function", {}).get("arguments", "{}"),
                            })

                        tool_result = await self._execute_mcp_tool(tc)
                        messages.append(tool_result)

                        if tool_events is not None:
                            tool_events.append({
                                "type": "tool_result",
                                "name": tool_result.get("name", ""),
                                "content": tool_result.get("content", ""),
                            })
                elif "candidates" in result:
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    return {"content": content}
                else:
                    return {"content": str(result)}

            except Exception as e:
                logger.error("provider_tool_chat_error", provider=provider_name, error=str(e))
                return {"content": f"⚠️ Provider error: {str(e)}"}

        return {"content": "⚠️ Reached maximum tool call iterations."}

    # ────────── Simple Chat (No Tools) ──────────

    async def _chat_with_ollama(self, model: str, messages: list[dict]) -> dict:
        """Send chat request to local Ollama (no tools)."""
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
        """Stream response from local Ollama (no tools)."""
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
        """Send chat request to an online provider (no tools)."""
        provider_instance = self._get_provider(provider_name)
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
        """Stream response from an online provider (no tools)."""
        provider_instance = self._get_provider(provider_name)
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


# Global chat service instance (mcp_service set later by routes)
chat_service = ChatService()
