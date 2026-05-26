"""Unit tests for ChatService - session management, messaging, MCP tool integration, streaming.

All service methods are async def — tests use @pytest.mark.asyncio + async def + await.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio


@pytest.fixture
def chat_service():
    from services.chat_service import ChatService
    svc = ChatService()
    svc.sessions = {}
    svc.ollama_service = MagicMock()
    svc.mcp_service = MagicMock()
    return svc


# ──────────────────────────────────────────────
# Session Management (Sync methods)
# ──────────────────────────────────────────────

class TestSessions:
    """Test chat session management."""

    def test_create_session_returns_id(self, chat_service):
        """create_session returns a string session ID."""
        session_id = chat_service.create_session()
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        assert session_id in chat_service.sessions

    def test_create_session_with_custom_id(self, chat_service):
        """create_session accepts a custom session ID."""
        session_id = chat_service.create_session("my-custom-id")
        assert session_id == "my-custom-id"

    def test_create_session_initializes_empty(self, chat_service):
        """create_session starts with empty messages list."""
        session_id = chat_service.create_session()
        session = chat_service.sessions[session_id]
        assert session["messages"] == []
        assert "created_at" in session
        assert "id" in session

    def test_get_session_history_exists(self, chat_service):
        """get_session_history returns messages for existing session."""
        sid = chat_service.create_session()
        chat_service.sessions[sid]["messages"] = [{"role": "user", "content": "Hi"}]
        messages = chat_service.get_session_history(sid)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_get_session_history_empty(self, chat_service):
        """get_session_history returns empty list for non-existent session."""
        messages = chat_service.get_session_history("nonexistent")
        assert messages == []

    def test_delete_session_existing(self, chat_service):
        """delete_session removes the session."""
        sid = chat_service.create_session()
        chat_service.delete_session(sid)
        assert sid not in chat_service.sessions

    def test_delete_session_nonexistent(self, chat_service):
        """delete_session is idempotent for non-existent sessions."""
        chat_service.delete_session("nonexistent")


# ──────────────────────────────────────────────
# Sending Messages (Async methods)
# ──────────────────────────────────────────────

class TestSendMessage:
    """Test message sending behavior."""

    @pytest.mark.asyncio
    async def test_send_message_with_ollama(self, chat_service):
        """send_message sends to Ollama and returns response."""
        chat_service._chat_with_ollama_tools = AsyncMock(return_value={"content": "Hello! How can I help?"})
        chat_service.create_session("test-session")

        result = await chat_service.send_message(
            "test-session",
            "Hi there!",
            provider="ollama",
            model="llama3",
        )

        assert result["session_id"] == "test-session"
        assert result["response"] == "Hello! How can I help?"
        assert result["provider"] == "ollama"
        assert result["model"] == "llama3"

    @pytest.mark.asyncio
    async def test_send_message_creates_session_if_not_exists(self, chat_service):
        """send_message creates a session if the ID doesn't exist."""
        chat_service._chat_with_ollama_tools = AsyncMock(return_value={"content": "Hello!"})

        result = await chat_service.send_message(
            "auto-session",
            "Hello",
            provider="ollama",
        )

        assert result["session_id"] == "auto-session"
        assert "auto-session" in chat_service.sessions

    @pytest.mark.asyncio
    async def test_send_message_with_provider(self, chat_service):
        """send_message dispatches to provider for non-ollama providers."""
        chat_service._chat_with_provider_tools = AsyncMock(return_value={"content": "Response from provider"})
        chat_service.create_session("test-session")

        result = await chat_service.send_message(
            "test-session",
            "Hello",
            provider="openai",
            model="gpt-4",
        )

        assert result["response"] == "Response from provider"
        assert result["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_send_message_adds_user_message(self, chat_service):
        """send_message adds user message to session history."""
        chat_service._chat_with_ollama_tools = AsyncMock(return_value={"content": "Response"})
        chat_service.create_session("test-session")

        await chat_service.send_message(
            "test-session",
            "Hello world",
            provider="ollama",
            model="llama3",
        )

        messages = chat_service.sessions["test-session"]["messages"]
        assert any(m["role"] == "user" and m["content"] == "Hello world" for m in messages)

    @pytest.mark.asyncio
    async def test_send_message_adds_assistant_response(self, chat_service):
        """send_message adds assistant response to session history."""
        chat_service._chat_with_ollama_tools = AsyncMock(return_value={"content": "Sure thing!"})
        chat_service.create_session("test-session")

        await chat_service.send_message("test-session", "Help me", provider="ollama")

        messages = chat_service.sessions["test-session"]["messages"]
        assert any(m["role"] == "assistant" and m["content"] == "Sure thing!" for m in messages)

    @pytest.mark.asyncio
    async def test_send_message_rejects_empty_content(self, chat_service):
        """send_message handles empty content gracefully."""
        chat_service._chat_with_ollama_tools = AsyncMock(return_value={"content": ""})
        chat_service.create_session("test-session")

        result = await chat_service.send_message("test-session", "", provider="ollama")
        assert "response" in result
        assert result["response"] == ""


# ──────────────────────────────────────────────
# Tool Integration
# ──────────────────────────────────────────────

class TestToolIntegration:
    """Test MCP tool integration in chat."""

    @pytest.mark.asyncio
    async def test_collect_tools_returns_empty_when_no_mcp(self, chat_service):
        """_collect_tools returns empty list when no MCP service."""
        chat_service.mcp_service = None
        tools = await chat_service._collect_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_collect_tools_with_mcp(self, chat_service):
        """_collect_tools returns tools from MCP service."""
        chat_service.mcp_service.get_all_enabled_tools = AsyncMock(return_value=[
            {"type": "function", "function": {"name": "test"}}
        ])
        tools = await chat_service._collect_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "test"

    @pytest.mark.asyncio
    async def test_collect_tools_handles_exception(self, chat_service):
        """_collect_tools returns empty list on MCP service error."""
        chat_service.mcp_service.get_all_enabled_tools = AsyncMock(side_effect=Exception("MCP error"))
        tools = await chat_service._collect_tools()
        assert tools == []


# ──────────────────────────────────────────────
# MCP Tool Execution
# ──────────────────────────────────────────────

class TestMCPToolExecution:
    """Test tool execution and name parsing."""

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_parses_qualified_name(self, chat_service):
        """_execute_mcp_tool parses 'mcp_name__tool_name' format."""
        chat_service.mcp_service = MagicMock()
        chat_service.mcp_service._mcp_info = {1: {"name": "my-mcp"}}
        chat_service.mcp_service.execute_tool = AsyncMock(return_value={
            "status": "success", "result": "Done"
        })

        result = await chat_service._execute_mcp_tool({
            "id": "call_123",
            "function": {"name": "my-mcp__greet", "arguments": '{"name": "World"}'},
        })

        assert result["role"] == "tool"
        chat_service.mcp_service.execute_tool.assert_called_once_with(1, "greet", {"name": "World"})

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_invalid_name_format(self, chat_service):
        """_execute_mcp_tool returns error for malformed tool name."""
        result = await chat_service._execute_mcp_tool({
            "id": "call_1",
            "function": {"name": "no-separator", "arguments": "{}"},
        })

        assert result["role"] == "tool"
        assert "Invalid tool name format" in result["content"]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_mcp_not_found(self, chat_service):
        """_execute_mcp_tool returns error when MCP not found by name."""
        chat_service.mcp_service = MagicMock()
        chat_service.mcp_service._mcp_info = {}

        result = await chat_service._execute_mcp_tool({
            "id": "call_1",
            "function": {"name": "nonexistent__tool", "arguments": "{}"},
        })

        assert "not found" in result["content"].lower()

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_no_mcp_service(self, chat_service):
        """_execute_mcp_tool returns error when no MCP service available."""
        chat_service.mcp_service = None

        result = await chat_service._execute_mcp_tool({
            "id": "call_1",
            "function": {"name": "mcp__tool", "arguments": "{}"},
        })

        assert "not available" in result["content"].lower()


# ──────────────────────────────────────────────
# Streaming
# ──────────────────────────────────────────────

class TestStreaming:
    """Test streaming message behavior."""

    @pytest.mark.asyncio
    async def test_stream_message_no_mcp(self, chat_service):
        """stream_message yields tokens without MCP tools."""
        chat_service._collect_tools = AsyncMock(return_value=[])
        chat_service._stream_ollama = AsyncMock()

        async def mock_stream(model, messages):
            yield "Hello"
            yield " World"

        chat_service._stream_ollama = mock_stream
        chat_service.create_session("test-session")

        events = []
        async for event in chat_service.stream_message("test-session", "Hi", model="llama3"):
            if isinstance(event, str):
                events.append(json.loads(event))

        token_events = [e for e in events if e["type"] == "token"]
        done_events = [e for e in events if e["type"] == "done"]
        assert len(token_events) >= 1
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_stream_message_with_tools(self, chat_service):
        """stream_message uses _stream_with_tools when MCP tools available."""
        chat_service._collect_tools = AsyncMock(return_value=[{"type": "function", "function": {"name": "test"}}])
        chat_service._stream_with_tools = AsyncMock()

        async def mock_stream(provider, model, messages, tools):
            yield json.dumps({"type": "done", "content": "Done"})

        chat_service._stream_with_tools = mock_stream
        chat_service.create_session("test-session")

        async for _ in chat_service.stream_message("test-session", "Run tool"):
            pass


# ──────────────────────────────────────────────
# Error Handling
# ──────────────────────────────────────────────

class TestErrorHandling:
    """Test chat error handling."""

    @pytest.mark.asyncio
    async def test_provider_not_configured(self, chat_service):
        """send_message returns error for non-existent provider."""
        chat_service.create_session("test-session")
        chat_service._chat_with_provider_tools = AsyncMock(return_value={
            "content": "⚠️ Provider 'nonexistent' not configured."
        })

        result = await chat_service.send_message(
            "test-session", "Hi", provider="nonexistent"
        )
        assert "not configured" in result["response"].lower()
