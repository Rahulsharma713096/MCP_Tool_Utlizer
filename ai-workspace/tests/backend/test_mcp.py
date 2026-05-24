"""MCP Service Tests - Covers MCPAPI test cases from test.txt."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json

from services.mcp_service import MCPService
from models.database import MCP


@pytest.fixture
def mcp_service():
    return MCPService()


@pytest.fixture
def sample_mcp():
    return MCP(
        id=1,
        name="test-mcp",
        type="python",
        enabled=True,
        transport="stdio",
        command="python",
        args=json.dumps(["-c", "print('hello')"]),
    )


@pytest.mark.asyncio
class TestMCPRegistration:
    """MCPAPI-001 to MCPAPI-006: MCP lifecycle tests"""

    async def test_register_mcp_success(self, mcp_service):
        """MCPAPI-001: Positive - Register MCP"""
        mcp_data = {
            "name": "test-mcp",
            "type": "python",
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "print('hello')"],
        }
        result = await mcp_service.register_mcp(mcp_data)
        assert result["status"] == "registered"
        assert result["mcp"]["name"] == "test-mcp"

    async def test_register_mcp_blocked_command(self, mcp_service):
        """MCPAPI-004: Negative - Invalid transport rejected"""
        mcp_data = {
            "name": "dangerous-mcp",
            "type": "shell",
            "transport": "stdio",
            "command": "rm -rf /",
        }
        result = await mcp_service.register_mcp(mcp_data)
        assert result["status"] == "error"
        assert "blocked" in result["message"].lower()

    async def test_register_mcp_invalid_transport(self, mcp_service):
        """MCPAPI-004: Negative - Invalid transport rejected"""
        mcp_data = {
            "name": "bad-transport",
            "type": "test",
            "transport": "invalid",
            "command": "python",
        }
        result = await mcp_service.register_mcp(mcp_data)
        assert result["status"] == "error"

    async def test_delete_mcp(self, mcp_service):
        """MCPAPI-002: Positive - Delete MCP"""
        result = await mcp_service.delete_mcp(1)
        assert result["status"] == "deleted"
        assert result["id"] == 1

    async def test_enable_mcp_no_command(self, mcp_service):
        """MCPAPI-007: Negative - Disabled MCP cannot execute"""
        mcp = MCP(id=2, name="no-cmd", type="python", enabled=True, transport="stdio", command="", args=None)
        result = await mcp_service.enable_mcp(mcp)
        assert result["status"] == "error"

    async def test_enable_mcp_not_allowed_command(self, mcp_service):
        """MCPAPI-004: Negative - Invalid command rejected"""
        mcp = MCP(id=3, name="bad-cmd", type="shell", enabled=True, transport="stdio", command="rm", args=["-rf", "/"])
        result = await mcp_service.enable_mcp(mcp)
        assert result["status"] == "error"

    async def test_disable_mcp(self, mcp_service, sample_mcp):
        """MCPAPI-002: Positive - Disable MCP"""
        # First enable
        mock_process = AsyncMock()
        mock_process.pid = 12345
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await mcp_service.enable_mcp(sample_mcp)

        result = await mcp_service.disable_mcp(sample_mcp)
        assert result["status"] == "stopped"


@pytest.mark.asyncio
class TestMCPExecution:
    """MCPAPI-005: MCP healthcheck tests"""

    async def test_mcp_healthcheck_http(self, mcp_service):
        """MCPAPI-005: Positive - HTTP healthcheck"""
        mcp = MCP(id=5, name="http-mcp", type="http", enabled=True, transport="http", endpoint="http://localhost:8080", command="", args=None)
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await mcp_service.test_mcp(mcp)
            assert result["status"] == "healthy"

    async def test_mcp_healthcheck_timeout(self, mcp_service):
        """MCPAPI-005: Negative - Healthcheck timeout"""
        mcp = MCP(id=6, name="timeout-mcp", type="http", enabled=True, transport="http", endpoint="http://localhost:9999", command="", args=None)

        with patch("httpx.AsyncClient.get", side_effect=Exception("Timeout")):
            result = await mcp_service.test_mcp(mcp)
            assert result["status"] == "unreachable"

    async def test_get_mcp_logs_not_running(self, mcp_service):
        """Test logs when MCP not running"""
        logs = await mcp_service.get_mcp_logs(999)
        assert logs == ["MCP not running"]

    async def test_cleanup_all(self, mcp_service, sample_mcp):
        """Test cleanup of all MCPs"""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await mcp_service.enable_mcp(sample_mcp)
            assert len(mcp_service.running_mcps) == 1

        await mcp_service.cleanup_all()
        assert len(mcp_service.running_mcps) == 0
