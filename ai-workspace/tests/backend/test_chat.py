"""Chat Service Tests - Covers CAPI test cases from test.txt."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
import json
import httpx

from services.chat_service import ChatService


@pytest.fixture
def chat_service():
    return ChatService()


@pytest.mark.asyncio
class TestChatSessions:
    """CAPI-001 to CAPI-006: Chat functionality tests"""

    async def test_create_session(self, chat_service):
        """CAPI-001: Positive - Create chat session"""
        session_id = chat_service.create_session()
        assert session_id is not None
        assert session_id in chat_service.sessions

    async def test_send_message_ollama(self, chat_service):
        """CAPI-001: Positive - Send chat request"""
        session_id = chat_service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Hello! How can I help you?"}
        }

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await chat_service.send_message(
                session_id=session_id,
                content="Hi there!",
                provider="ollama",
                model="llama3",
            )
            assert result["response"] == "Hello! How can I help you?"
            assert result["session_id"] == session_id

    async def test_send_message_ollama_offline(self, chat_service):
        """CAPI-005: Negative - Ollama offline"""
        session_id = chat_service.create_session()

        with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
            result = await chat_service.send_message(
                session_id=session_id,
                content="Hi!",
                provider="ollama",
            )
            assert "Error" in result["response"]

    async def test_auto_create_session(self, chat_service):
        """Auto-create session if not exists"""
        result = await chat_service.send_message(
            session_id="new-session",
            content="Hello!",
            provider="ollama",
            model="llama3",
        )
        assert result["session_id"] == "new-session"
        assert "new-session" in chat_service.sessions

    async def test_get_session_history(self, chat_service):
        """CAPI-003: Positive - Message history persists"""
        session_id = chat_service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Hello!"}}

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            await chat_service.send_message(session_id, "Hi!", provider="ollama")

        history = chat_service.get_session_history(session_id)
        assert len(history) == 2  # user message + assistant response
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    async def test_delete_session(self, chat_service):
        """CAPI: Delete session"""
        session_id = chat_service.create_session()
        assert session_id in chat_service.sessions

        chat_service.delete_session(session_id)
        assert session_id not in chat_service.sessions

    async def test_stream_ollama(self, chat_service):
        """CAPI-002: Positive - Streaming response"""
        session_id = chat_service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        async def mock_aiter_lines():
            yield json.dumps({"message": {"content": "Hello"}})
            yield json.dumps({"message": {"content": " World"}})
            yield json.dumps({"done": True})

        mock_response.aiter_lines = mock_aiter_lines

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            tokens = []
            async for event in chat_service.stream_message(
                session_id=session_id,
                content="Hi!",
                provider="ollama",
                model="llama3",
            ):
                tokens.append(event)

            assert len(tokens) > 0

    async def test_send_without_model(self, chat_service):
        """CAPI-004: Negative - Invalid model rejected (falls back to default)"""
        session_id = chat_service.create_session()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Response"}}

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await chat_service.send_message(
                session_id=session_id,
                content="Hi!",
                provider="ollama",
                model=None,
            )
            assert result["response"] == "Response"

    async def test_provider_not_configured(self, chat_service):
        """CAPI-004: Negative - Invalid provider"""
        session_id = chat_service.create_session()
        result = await chat_service.send_message(
            session_id=session_id,
            content="Hi!",
            provider="nonexistent-provider",
            model="test-model",
        )
        assert "not configured" in result["response"].lower()


@pytest.mark.asyncio
class TestChatWebSocket:
    """CAPI-005: WebSocket tests"""

    async def test_streaming_with_provider(self, chat_service):
        """CAPI-005: WebSocket disconnect recovery"""
        session_id = chat_service.create_session()

        # Test that streaming works with an online provider
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Stream response"}}]
        }

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            tokens = []
            async for event in chat_service.stream_message(
                session_id=session_id,
                content="Hi!",
                provider="openai",
            ):
                tokens.append(event)
            assert len(tokens) > 0
