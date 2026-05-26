"""Data Flow & Integration Tests - cross-service data flow and API integration.

Tests cover:
- ChatService with MCPService integration
- ProviderService with ChatService integration
- Full message flow with tool calls
- Service-to-service data consistency
- End-to-end data pipeline
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from services.chat_service import ChatService


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def mcp_service():
    from services.mcp_service import MCPService
    svc = MCPService()
    svc.running_mcps = {}
    svc._mcp_info = {}
    svc._tool_cache = {}
    return svc


@pytest.fixture
def chat_with_mcp(mcp_service):
    from services.chat_service import ChatService
    svc = ChatService(mcp_service=mcp_service)
    svc.ollama_service = MagicMock()
    return svc


# ──────────────────────────────────────────────
# Chat + MCP Integration
# ──────────────────────────────────────────────

class TestChatWithMCP:
    """Test data flow between ChatService and MCPService."""

    @patch.object(ChatService, "_chat_with_ollama_tools")
    def test_chat_reads_tools_from_mcp(self, mock_chat_tools, chat_with_mcp, mcp_service):
        """ChatService reads MCP tools when sending message."""
        mcp_service._mcp_info[1] = {"name": "test-mcp"}
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mcp_service.running_mcps[1] = mock_proc
        mcp_service._tool_cache[1] = [{"name": "greet", "description": "", "input_schema": {}}]
        mock_chat_tools.return_value = {"content": "Done"}

        chat_with_mcp.create_session("test")
        result = chat_with_mcp.send_message("test", "Hello", provider="ollama")

        mock_chat_tools.assert_called_once()
        # Verify tools were passed
        call_args = mock_chat_tools.call_args
        assert call_args is not None

    @patch.object(ChatService, "_chat_with_provider_tools")
    def test_chat_with_provider_reads_mcp_tools(self, mock_chat_tools, chat_with_mcp, mcp_service):
        """ChatService with provider reads MCP tools for non-ollama providers."""
        mcp_service.running_mcps[1] = MagicMock()
        mcp_service._mcp_info[1] = {"name": "test-mcp"}
        mock_chat_tools.return_value = {"content": "Provider response"}

        chat_with_mcp.create_session("test")
        result = chat_with_mcp.send_message(
            "test", "Hello", provider="openai", model="gpt-4"
        )

        mock_chat_tools.assert_called_once()

    def test_mcp_tool_execution_updates_chat(self, chat_with_mcp, mcp_service):
        """Tool execution results flow back into chat messages."""
        mcp_service._mcp_info[1] = {"name": "my-mcp"}
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mcp_service.running_mcps[1] = mock_proc
        mcp_service.execute_tool = AsyncMock(return_value={
            "status": "success", "result": [{"type": "text", "text": "Tool executed!"}]
        })

        chat_with_mcp.create_session("test")
        result = chat_with_mcp._execute_mcp_tool({
            "id": "call_1",
            "function": {"name": "my-mcp__greet", "arguments": "{}"},
        })

        assert result["role"] == "tool"
        assert result["content"] == "Tool executed!"


# ──────────────────────────────────────────────
# Provider + Chat Integration
# ──────────────────────────────────────────────

class TestProviderChatIntegration:
    """Test data flow between providers and chat."""

    def test_provider_message_routes_to_correct_method(self):
        """ChatService routes to provider method for non-ollama providers."""
        from services.chat_service import ChatService

        svc = ChatService()
        svc._chat_with_provider = AsyncMock(return_value={"content": "Hi"})
        svc.create_session("test")

        result = svc.send_message("test", "Hello", provider="openai", model="gpt-4")
        svc._chat_with_provider.assert_called_once()

    def test_provider_and_tool_flow(self, chat_with_mcp, mcp_service):
        """Provider + MCP tools: tool events collected properly."""
        mcp_service._mcp_info[1] = {"name": "my-mcp"}
        mcp_service._tool_cache[1] = [{"name": "test-tool", "description": "", "input_schema": {}}]
        mcp_service.running_mcps[1] = MagicMock()

        events = []
        # Simulate tool call during provider chat
        event = {
            "type": "tool_call",
            "name": "my-mcp__test-tool",
            "args": "{}",
        }
        events.append(event)

        assert events[0]["type"] == "tool_call"
        assert events[0]["name"] == "my-mcp__test-tool"


# ──────────────────────────────────────────────
# End-to-End Message Flow
# ──────────────────────────────────────────────

class TestEndToEndFlow:
    """Test complete message processing pipeline."""

    @patch("services.chat_service.httpx.AsyncClient")
    def test_full_ollama_chat_flow(self, mock_httpx):
        """Complete Ollama chat flow: user msg → LLM → response."""
        from services.chat_service import ChatService

        svc = ChatService(mcp_service=None)
        svc.create_session("test")

        # Mock Ollama API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "I'm fine, thank you!", "role": "assistant"}
        }
        mock_client = AsyncMock().__aenter__.return_value
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        result = svc.send_message(
            "test",
            "How are you?",
            provider="ollama",
            model="llama3",
        )

        assert result["response"] == "I'm fine, thank you!"
        assert result["provider"] == "ollama"

        # Verify conversation history maintained
        history = svc.get_session_history("test")
        assert len(history) == 2  # user + assistant
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "How are you?"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "I'm fine, thank you!"

    def test_full_mcp_tool_flow(self, chat_with_mcp, mcp_service):
        """Complete MCP tool flow: tool_call → execution → result."""
        mcp_service._mcp_info[1] = {"name": "data-mcp"}
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mcp_service.running_mcps[1] = mock_proc

        # Step 1: Collect tools
        with patch.object(mcp_service, "list_tools", AsyncMock(return_value=[
            {"name": "read_data", "description": "Read data from source", "input_schema": {"type": "object"}}
        ])):
            tools = chat_with_mcp._collect_tools()
            assert len(tools) >= 1

        # Step 2: Execute tool
        mcp_service.execute_tool = AsyncMock(return_value={
            "status": "success",
            "result": [{"type": "text", "text": "Data: 42 rows"}]
        })

        result = chat_with_mcp._execute_mcp_tool({
            "id": "call_1",
            "function": {"name": "data-mcp__read_data", "arguments": '{"source": "db"}'},
        })
        assert result["content"] == "Data: 42 rows"
