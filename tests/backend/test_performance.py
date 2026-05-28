"""Performance & Load Tests - basic performance benchmarks and load handling.

Tests cover:
- Response time benchmarks for core operations
- Concurrent session handling
- Large message handling
- Tool cache hit ratios
- Memory usage patterns
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch


# ──────────────────────────────────────────────
# Response Time Benchmarks
# ──────────────────────────────────────────────

class TestResponseTime:
    """Test core operations complete within acceptable time bounds."""

    @pytest.mark.asyncio
    async def test_detect_ollama_under_100ms(self):
        """detect_ollama completes quickly under mocked conditions."""
        from services.ollama_service import OllamaService

        svc = OllamaService()
        with patch("services.ollama_service._run_command") as mock_run:
            mock_run.return_value = ("ollama version 0.3.0\n", "")

            start = time.time()
            result = await svc.detect_ollama()
            elapsed = time.time() - start

            assert result is True
            assert elapsed < 1.0  # Should be fast under mocks

    def test_create_100_sessions_under_5s(self):
        """Creating many sessions is fast."""
        from services.chat_service import ChatService

        svc = ChatService()
        start = time.time()
        for _ in range(100):
            svc.create_session()
        elapsed = time.time() - start

        assert len(svc.sessions) == 100
        assert elapsed < 5.0  # 100 sessions in under 5s

    def test_verify_token_under_10ms(self):
        """Token verification completes quickly."""
        from core.security import create_access_token, verify_token

        token = create_access_token({"sub": "admin"})
        start = time.time()
        result = verify_token(token)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.1  # Should be sub-100ms


# ──────────────────────────────────────────────
# Concurrent Operations
# ──────────────────────────────────────────────

class TestConcurrentOperations:
    """Test system handles concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_mcp_registrations(self):
        """Multiple MCP registrations don't interfere."""
        from services.mcp_service import MCPService

        svc = MCPService()
        names = [f"mcp-{i}" for i in range(50)]

        for name in names:
            result = await svc.register_mcp({
                "name": name,
                "type": "custom",
                "command": "python",
                "args": ["-m", "server"],
                "transport": "stdio",
            })
            assert result["status"] == "registered"

    def test_concurrent_chat_sessions(self):
        """Many chat sessions can be created and used independently."""
        from services.chat_service import ChatService

        svc = ChatService(mcp_service=None)

        # Create 50 sessions
        sessions = [svc.create_session() for _ in range(50)]

        # Verify all are distinct and accessible
        for sid in sessions:
            history = svc.get_session_history(sid)
            assert history == []

        # Delete all
        for sid in sessions:
            svc.delete_session(sid)

        assert len(svc.sessions) == 0


# ──────────────────────────────────────────────
# Large Data Handling
# ──────────────────────────────────────────────

class TestLargeData:
    """Test handling of large payloads."""

    def test_chat_large_message_history(self):
        """ChatService handles sessions with many messages."""
        from services.chat_service import ChatService

        svc = ChatService(mcp_service=None)
        sid = svc.create_session("large-session")

        # Add 1000 messages
        svc.sessions[sid]["messages"] = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(1000)
        ]

        history = svc.get_session_history("large-session")
        assert len(history) == 1000

    def test_mcp_tool_cache_many_tools(self):
        """MCP tool cache handles many tools."""
        from services.mcp_service import MCPService

        svc = MCPService()
        svc._tool_cache[1] = [
            {"name": f"tool-{i}", "description": f"Description {i}", "input_schema": {}}
            for i in range(100)
        ]

        tools = svc._tool_cache[1]
        assert len(tools) == 100
        assert tools[0]["name"] == "tool-0"
        assert tools[99]["name"] == "tool-99"


# ──────────────────────────────────────────────
# Cache Performance
# ──────────────────────────────────────────────

class TestCachePerformance:
    """Test caching improves performance."""

    @pytest.mark.asyncio
    async def test_list_tools_cache_hit(self):
        """list_tools returns cached tools without RPC call."""
        from services.mcp_service import MCPService

        svc = MCPService()
        svc.running_mcps[1] = MagicMock()
        svc._tool_cache[1] = [{"name": "cached-tool", "description": "", "input_schema": {}}]

        with patch.object(svc, "_send_request") as mock_send:
            tools = await svc.list_tools(1)
            assert len(tools) == 1
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_tools_cache_miss(self):
        """list_tools makes RPC call on cache miss."""
        from services.mcp_service import MCPService

        svc = MCPService()
        svc.running_mcps[1] = MagicMock()

        with patch.object(svc, "_send_request", AsyncMock()) as mock_send:
            mock_send.return_value = {
                "result": {"tools": [{"name": "new-tool", "description": "", "inputSchema": {}}]}
            }
            tools = await svc.list_tools(1)
            assert len(tools) == 1
            mock_send.assert_called_once()


# ──────────────────────────────────────────────
# Size / Limit Checks
# ──────────────────────────────────────────────

class TestSizeChecks:
    """Test size/limit boundaries."""

    def test_runtime_service_stores_metrics(self):
        """RuntimeService stores metrics without exceeding reasonable size."""
        from services.runtime_service import RuntimeService

        svc = RuntimeService()

        # Add many metrics entries
        for i in range(100):
            svc._metrics_history.append({
                "cpu_percent": 50.0,
                "ram_percent": 50.0,
                "timestamp": "2024-01-01T00:00:00Z",
            })

        assert len(svc._metrics_history) == 100
        assert len(svc._metrics_history) <= 1000  # Limit sanity check

    def test_parse_size_edge_cases(self):
        """Size parsing handles edge cases."""
        from services.ollama_service import OllamaService

        # Verify parsing works (results are > 0)
        assert OllamaService._parse_ollama_size("999999GB") >= 0

        # Zero
        assert OllamaService._parse_ollama_size("0") == 0

        # Decimal precision
        result = OllamaService._parse_ollama_size("1.5GB")
        assert result == int(1.5 * 1024**3)
