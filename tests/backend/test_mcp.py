"""Unit tests for MCPService - MCP server lifecycle, JSON-RPC, tool discovery, security.

All service methods are async def — tests use @pytest.mark.asyncio + async def + await.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import json
import asyncio


@pytest.fixture
def mcp_service():
    from services.mcp_service import MCPService
    svc = MCPService()
    svc.running_mcps = {}
    svc._mcp_info = {}
    svc._tool_cache = {}
    return svc


@pytest.fixture
def mock_process():
    proc = MagicMock()
    proc.pid = 54321
    proc.returncode = None
    proc.stdin = AsyncMock()
    proc.stdout = AsyncMock()
    proc.stderr = AsyncMock()
    return proc


# ──────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────

class TestRegistration:
    """Test MCP server registration."""

    @pytest.mark.asyncio
    async def test_register_mcp_success(self, mcp_service):
        """register_mcp returns registered status with valid data."""
        result = await mcp_service.register_mcp({
            "name": "test-mcp",
            "type": "custom",
            "command": "python",
            "args": ["-m", "server"],
            "transport": "stdio",
        })
        assert result["status"] == "registered"
        assert result["mcp"]["name"] == "test-mcp"

    @pytest.mark.asyncio
    async def test_register_mcp_blocked_command(self, mcp_service):
        """register_mcp blocks dangerous commands."""
        result = await mcp_service.register_mcp({
            "name": "evil-mcp",
            "type": "custom",
            "command": "rm -rf /",
        })
        assert result["status"] == "error"
        assert "blocked" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_register_mcp_blocked_sudo(self, mcp_service):
        """register_mcp blocks sudo command."""
        result = await mcp_service.register_mcp({
            "name": "sudo-mcp",
            "type": "custom",
            "command": "sudo",
        })
        assert result["status"] == "error"
        assert "blocked" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_register_mcp_invalid_transport(self, mcp_service):
        """register_mcp rejects invalid transport."""
        result = await mcp_service.register_mcp({
            "name": "bad-transport",
            "type": "custom",
            "command": "python",
            "transport": "invalid",
        })
        assert result["status"] == "error"
        assert "transport" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_register_mcp_valid_transports(self, mcp_service):
        """register_mcp accepts all valid transports."""
        for transport in ["stdio", "sse", "http"]:
            result = await mcp_service.register_mcp({
                "name": f"mcp-{transport}",
                "type": "custom",
                "command": "python",
                "transport": transport,
            })
            assert result["status"] == "registered", f"Failed for transport: {transport}"


# ──────────────────────────────────────────────
# Enable/Disable Lifecycle
# ──────────────────────────────────────────────

class TestLifecycle:
    """Test MCP server enable/disable lifecycle."""

    @pytest.mark.asyncio
    async def test_enable_mcp_success(self, mcp_service):
        """enable_mcp starts the process and returns PID."""
        from models.database import MCP

        mock_proc = MagicMock()
        mock_proc.pid = 54321
        mock_proc.returncode = None
        mock_proc.stdin = AsyncMock()
        mock_proc.stdout = AsyncMock()

        with patch("services.mcp_service.asyncio.create_subprocess_exec") as mock_subprocess:
            mock_subprocess.return_value = mock_proc
            mcp = MCP(id=1, name="test-mcp", type="custom", command="python",
                      args='["-m", "server"]', transport="stdio")

            with patch.object(mcp_service, "list_tools", AsyncMock(return_value=[{"name": "greet"}])):
                result = await mcp_service.enable_mcp(mcp)

        assert result["status"] == "started"
        assert result["id"] == 1
        assert result["pid"] == 54321
        assert 1 in mcp_service.running_mcps
        assert mcp_service._mcp_info[1]["name"] == "test-mcp"

    @pytest.mark.asyncio
    async def test_enable_mcp_already_running(self, mcp_service):
        """enable_mcp returns already_running if already enabled."""
        from models.database import MCP

        mcp_service.running_mcps[1] = MagicMock()
        mcp = MCP(id=1, name="test-mcp", type="custom", command="python", args=[])

        result = await mcp_service.enable_mcp(mcp)
        assert result["status"] == "already_running"

    @pytest.mark.asyncio
    async def test_enable_mcp_no_command(self, mcp_service):
        """enable_mcp returns error if no command configured."""
        from models.database import MCP

        mcp = MCP(id=1, name="test-mcp", type="custom", command="", args=[])
        result = await mcp_service.enable_mcp(mcp)
        assert result["status"] == "error"
        assert "No command" in result["message"]

    @pytest.mark.asyncio
    async def test_enable_mcp_command_not_allowed(self, mcp_service):
        """enable_mcp rejects commands not in ALLOWED_COMMANDS."""
        from models.database import MCP

        mcp = MCP(id=1, name="test-mcp", type="custom", command="ruby", args=["-e", "puts 1"])
        result = await mcp_service.enable_mcp(mcp)
        assert result["status"] == "error"
        assert "not in the allowed list" in result["message"]

    @pytest.mark.asyncio
    async def test_enable_mcp_file_not_found(self, mcp_service):
        """enable_mcp handles FileNotFoundError gracefully."""
        from models.database import MCP

        with patch("services.mcp_service.asyncio.create_subprocess_exec") as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError("python not found")
            mcp = MCP(id=1, name="test-mcp", type="custom", command="python", args=["-m", "server"])
            result = await mcp_service.enable_mcp(mcp)

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_disable_mcp_success(self, mcp_service):
        """stop_mcp stops a running MCP."""
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.pid = 54321
        mcp_service.running_mcps[1] = mock_proc
        mcp_service._tool_cache[1] = [{"name": "greet"}]
        mcp_service._mcp_info[1] = {"name": "test-mcp"}

        result = await mcp_service.stop_mcp(1)
        assert result["status"] == "stopped"
        assert 1 not in mcp_service.running_mcps
        assert 1 not in mcp_service._tool_cache
        mock_proc.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_disable_mcp_not_running(self, mcp_service):
        """stop_mcp returns not_running if MCP isn't enabled."""
        result = await mcp_service.stop_mcp(999)
        assert result["status"] == "not_running"


# ──────────────────────────────────────────────
# JSON-RPC Communication
# ──────────────────────────────────────────────

class TestJSONRPC:
    """Test JSON-RPC request/response handling."""

    @pytest.mark.asyncio
    async def test_send_request_success(self, mcp_service, mock_process):
        """_send_request sends JSON-RPC and parses response."""
        mcp_service.running_mcps[1] = mock_process
        mock_process.stdout.readline = AsyncMock(
            return_value=b'{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"greet"}]}}\n'
        )

        response = await mcp_service._send_request(1, "tools/list")
        assert "result" in response
        assert response["result"]["tools"][0]["name"] == "greet"

        written_data = mock_process.stdin.write.call_args[0][0]
        sent = json.loads(written_data.decode())
        assert sent["jsonrpc"] == "2.0"
        assert sent["method"] == "tools/list"

    @pytest.mark.asyncio
    async def test_send_request_not_available(self, mcp_service):
        """_send_request returns error when process not available."""
        response = await mcp_service._send_request(999, "tools/list")
        assert "error" in response
        assert "MCP process not available" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_send_request_timeout(self, mcp_service, mock_process):
        """_send_request returns timeout error when request times out."""
        mcp_service.running_mcps[1] = mock_process

        async def timeout_readline():
            raise asyncio.TimeoutError()

        mock_process.stdout.readline = AsyncMock(side_effect=timeout_readline)

        response = await mcp_service._send_request(1, "tools/call", {"name": "test"})
        assert "error" in response
        assert "timed out" in response["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_send_request_json_decode_error(self, mcp_service, mock_process):
        """_send_request handles invalid JSON response."""
        mcp_service.running_mcps[1] = mock_process
        mock_process.stdout.readline = AsyncMock(return_value=b"not-json\n")

        response = await mcp_service._send_request(1, "tools/list")
        assert "error" in response


# ──────────────────────────────────────────────
# Tool Discovery & Execution
# ──────────────────────────────────────────────

class TestTools:
    """Test tool discovery and execution."""

    @pytest.mark.asyncio
    async def test_list_tools_new(self, mcp_service):
        """list_tools fetches tools from MCP server."""
        with patch.object(mcp_service, "_send_request") as mock_send:
            mock_send.return_value = {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {"name": "greet", "description": "Say hello", "inputSchema": {"type": "object"}},
                    ]
                }
            }
            mcp_service.running_mcps[1] = MagicMock()

            tools = await mcp_service.list_tools(1)
            assert len(tools) == 1
            assert tools[0]["name"] == "greet"
            assert tools[0]["description"] == "Say hello"
            assert tools[0]["input_schema"] == {"type": "object"}

    @pytest.mark.asyncio
    async def test_list_tools_cached(self, mcp_service):
        """list_tools returns cached tools without calling server."""
        mcp_service._tool_cache[1] = [{"name": "cached-tool", "description": "", "input_schema": {}}]
        mcp_service.running_mcps[1] = MagicMock()

        with patch.object(mcp_service, "_send_request") as mock_send:
            tools = await mcp_service.list_tools(1)
            assert len(tools) == 1
            assert tools[0]["name"] == "cached-tool"
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_tools_empty_on_error(self, mcp_service):
        """list_tools returns empty list on RPC error."""
        with patch.object(mcp_service, "_send_request") as mock_send:
            mock_send.return_value = {"jsonrpc": "2.0", "error": {"code": -32000, "message": "Error"}}
            mcp_service.running_mcps[1] = MagicMock()

            tools = await mcp_service.list_tools(1)
            assert tools == []

    @pytest.mark.asyncio
    async def test_get_all_enabled_tools(self, mcp_service):
        """get_all_enabled_tools collects tools from all running MCPs."""
        with patch.object(mcp_service, "list_tools") as mock_list_tools:
            mock_list_tools.return_value = [
                {"name": "greet", "description": "Say hello", "input_schema": {}}
            ]
            mock_proc = MagicMock()
            mock_proc.returncode = None
            mcp_service.running_mcps[1] = mock_proc
            mcp_service._mcp_info[1] = {"name": "my-mcp"}

            all_tools = await mcp_service.get_all_enabled_tools()
            assert len(all_tools) == 1
            assert all_tools[0]["function"]["name"] == "my-mcp__greet"
            assert all_tools[0]["_mcp_id"] == 1
            assert all_tools[0]["_raw_name"] == "greet"

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, mcp_service):
        """execute_tool runs tool and returns success."""
        with patch.object(mcp_service, "_send_request") as mock_send:
            mock_send.return_value = {
                "jsonrpc": "2.0",
                "result": {"content": [{"type": "text", "text": "Hello!"}]}
            }
            mock_proc = MagicMock()
            mock_proc.returncode = None
            mcp_service.running_mcps[1] = mock_proc

            result = await mcp_service.execute_tool(1, "greet", {"name": "World"})
            assert result["status"] == "success"

            sent_method = mock_send.call_args[0][1]
            assert sent_method == "tools/call"

    @pytest.mark.asyncio
    async def test_execute_tool_not_running(self, mcp_service):
        """execute_tool returns error if MCP not running."""
        result = await mcp_service.execute_tool(999, "greet", {})
        assert result["status"] == "error"
        assert "not running" in result["message"].lower()


# ──────────────────────────────────────────────
# Testing & Logs
# ──────────────────────────────────────────────

class TestMCPDiagnostics:
    """Test MCP test and log endpoints."""

    @pytest.mark.asyncio
    async def test_test_mcp_inactive(self, mcp_service):
        """test_mcp returns inactive for disabled stdio MCP."""
        from models.database import MCP

        mcp = MCP(id=1, name="test", type="custom", command="python", args=[], transport="stdio")
        result = await mcp_service.test_mcp(mcp)
        assert result["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_test_mcp_http_healthy(self, mcp_service):
        """test_mcp tests HTTP transport and returns healthy."""
        from models.database import MCP

        with patch("services.mcp_service.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_httpx.return_value = mock_client

            mcp = MCP(id=1, name="test", type="custom", command="", args=[],
                      transport="http", endpoint="http://localhost:3001")
            result = await mcp_service.test_mcp(mcp)
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_test_mcp_http_unreachable(self, mcp_service):
        """test_mcp returns unreachable for HTTP transport failure."""
        from models.database import MCP

        with patch("services.mcp_service.httpx.AsyncClient") as mock_httpx:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection refused")
            mock_httpx.return_value = mock_client

            mcp = MCP(id=1, name="test", type="custom", command="", args=[],
                      transport="http", endpoint="http://localhost:3001")
            result = await mcp_service.test_mcp(mcp)
            assert result["status"] == "unreachable"

    def test_get_mcp_logs_not_running(self, mcp_service):
        """get_mcp_logs returns message when MCP not running."""
        logs = mcp_service.get_mcp_logs(999)
        assert logs == ["MCP not running"]


# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────

class TestCleanup:
    """Test cleanup all MCPs on shutdown."""

    @pytest.mark.asyncio
    async def test_cleanup_all(self, mcp_service):
        """cleanup_all stops all running MCPs."""
        mock1 = MagicMock()
        mock2 = MagicMock()
        mcp_service.running_mcps[1] = mock1
        mcp_service.running_mcps[2] = mock2

        await mcp_service.cleanup_all()

        assert mcp_service.running_mcps == {}
        assert mcp_service._mcp_info == {}
        assert mcp_service._tool_cache == {}

    @pytest.mark.asyncio
    async def test_delete_mcp_removes_all_traces(self, mcp_service):
        """delete_mcp removes running process, info, and cache."""
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mcp_service.running_mcps[1] = mock_proc
        mcp_service._mcp_info[1] = {"name": "test-mcp"}
        mcp_service._tool_cache[1] = [{"name": "tool1"}]

        result = await mcp_service.delete_mcp(1)
        assert result["status"] == "deleted"
        assert 1 not in mcp_service.running_mcps
        assert 1 not in mcp_service._mcp_info
        assert 1 not in mcp_service._tool_cache
