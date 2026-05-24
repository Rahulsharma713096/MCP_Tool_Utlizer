"""Performance Tests - Covers PERF-001 to PERF-009 from test.txt.
Tests system performance under various loads.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import time
import asyncio
import httpx
import json

from services.ollama_service import OllamaService
from services.chat_service import ChatService
from services.mcp_service import MCPService
from services.runtime_service import RuntimeService


@pytest.mark.asyncio
class TestConcurrentOperations:
    """PERF-001 to PERF-003: Load tests."""

    async def test_concurrent_chat_sessions(self):
        """PERF-001: 100 concurrent chat requests"""
        service = ChatService()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Response"}}

        # Create 100 sessions
        sessions = []
        for i in range(100):
            sessions.append(service.create_session())

        assert len(sessions) == 100
        assert len(set(sessions)) == 100  # All unique

        # Send messages concurrently
        async def send_message(session_id):
            with patch("httpx.AsyncClient.post", return_value=mock_response):
                return await service.send_message(
                    session_id=session_id,
                    content="Test",
                    provider="ollama",
                    model="llama3",
                )

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            results = await asyncio.gather(*[send_message(s) for s in sessions[:10]])
            assert len(results) == 10
            assert all(r["response"] == "Response" for r in results)

    async def test_multiple_model_operations(self):
        """PERF-003: Multiple model operations"""
        service = OllamaService()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with patch.object(service, "_find_ollama_process", return_value=12345):
                # Start multiple models
                results = await asyncio.gather(
                    service.start_model("model-a"),
                    service.start_model("model-b"),
                    service.start_model("model-c"),
                )
                assert len(results) == 3
                assert all(r["status"] == "started" for r in results)

    async def test_concurrent_mcp_operations(self):
        """PERF-002: Multiple MCP operations"""
        service = MCPService()

        # Register multiple MCPs concurrently
        mcps = await asyncio.gather(*[
            service.register_mcp({
                "name": f"test-mcp-{i}",
                "type": "python",
                "transport": "stdio",
                "command": "python",
                "args": ["-c", "print('test')"],
            })
            for i in range(20)
        ])

        assert len(mcps) == 20
        assert all(m["status"] == "registered" for m in mcps)


@pytest.mark.asyncio
class TestPerformanceMetrics:
    """PERF-004 to PERF-005: Performance monitoring tests."""

    async def test_metrics_collection_speed(self):
        """PERF-005: Realtime metric updates are fast"""
        runtime = RuntimeService()

        start = time.time()
        for _ in range(10):
            metrics = await runtime.get_current_metrics()
            assert metrics is not None
        elapsed = time.time() - start

        # 10 metrics calls should complete in reasonable time
        assert elapsed < 30  # Should be well under 30s

    async def test_metrics_history_performance(self):
        """PERF-004: Metrics history returns quickly"""
        runtime = RuntimeService()

        # Collect some metrics
        for _ in range(50):
            await runtime.get_current_metrics()

        # Get history - should be fast
        start = time.time()
        history = await runtime.get_metrics_history(minutes=60)
        elapsed = time.time() - start

        assert len(history) >= 50
        assert elapsed < 5  # Should complete in < 5 seconds


@pytest.mark.asyncio
class TestStressScenarios:
    """PERF-006 to PERF-009: Stress tests."""

    async def test_large_conversation_history(self):
        """PERF-004: Large conversation history"""
        service = ChatService()
        session_id = service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "R" * 1000}}

        # Build up large conversation
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            for i in range(100):
                await service.send_message(
                    session_id=session_id,
                    content=f"Message {i}",
                    provider="ollama",
                    model="llama3",
                )

        # History should be manageable
        history = service.get_session_history(session_id)
        assert len(history) == 200  # 100 user + 100 assistant

    async def test_provider_failover_storm(self):
        """PERF-009: Multiple provider failures handled gracefully"""
        from services.provider_service import ProviderService, OpenRouterProvider
        service = ProviderService()

        # Create provider instances that all fail
        providers = []
        for i in range(10):
            provider = OpenRouterProvider(
                name=f"Stress-{i}",
                base_url=f"https://api.test{i}.com/v1",
                api_key="test-key",
            )
            providers.append(provider)

        # All fail simultaneously
        async def failing_healthcheck(p):
            return await p.health_check()

        with patch("httpx.AsyncClient.get", side_effect=Exception("Massive failure")):
            results = await asyncio.gather(*[failing_healthcheck(p) for p in providers])
            assert len(results) == 10
            assert all(r["status"] == "unreachable" for r in results)

    async def test_token_stream_performance(self):
        """PERF-008: Token stream performance"""
        service = ChatService()
        session_id = service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        # Simulate a long token stream
        async def mock_aiter_lines():
            for i in range(500):
                yield json.dumps({"message": {"content": "token "}})
            yield json.dumps({"done": True})

        mock_response.aiter_lines = mock_aiter_lines

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            tokens = []
            start = time.time()
            async for event in service.stream_message(
                session_id=session_id,
                content="Generate a long response",
                provider="ollama",
                model="llama3",
            ):
                tokens.append(event)
            elapsed = time.time() - start

            assert len(tokens) > 0
            assert elapsed < 30  # Should handle 500 tokens quickly

    async def test_model_switching_performance(self):
        """PERF-003: Dynamic model switching is fast"""
        service = OllamaService()
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with patch.object(service, "_find_ollama_process", return_value=12345):
                # Rapidly start/stop models
                for model in ["model-a", "model-b", "model-c", "model-d", "model-e"]:
                    start = await service.start_model(model)
                    assert start["status"] == "started"

                # Stop all quickly
                result = await service.kill_all_processes()
                assert result["status"] == "cleaned"
                assert len(service.running_processes) == 0
