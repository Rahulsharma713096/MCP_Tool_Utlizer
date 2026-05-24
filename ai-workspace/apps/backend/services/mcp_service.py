"""MCP Manager - Plugin ecosystem for Model Context Protocol servers.

Uses JSON-RPC 2.0 for MCP protocol communication:
  - tools/list  -> list available tools
  - tools/call  -> execute a tool with arguments
"""

import asyncio
import json
import subprocess
from typing import Optional, Any
from pathlib import Path

from models.database import MCP
from core.logging import log_manager

logger = log_manager.get_logger("mcp_service")

# Security: Allowed commands and paths for MCP execution
ALLOWED_COMMANDS = ["python", "node", "python3", "npx"]
ALLOWED_PATHS = ["/workspace", "/documents", "/home", "/tmp"]
BLOCKED_COMMANDS = ["rm", "del", "format", "dd", "mkfs", "sudo", "chmod", "shutdown"]

# JSON-RPC request ID counter
_rpc_id = 0


def _next_id() -> int:
    global _rpc_id
    _rpc_id += 1
    return _rpc_id


class MCPService:
    """Manages MCP server lifecycle - registration, execution, and monitoring."""

    def __init__(self):
        self.running_mcps: dict[int, subprocess.Popen] = {}
        self._mcp_info: dict[int, dict] = {}  # id -> {name, type, transport, tools: []}
        self._tool_cache: dict[int, list[dict]] = {}  # id -> cached tool list

    # ────────── JSON-RPC Helpers ──────────

    async def _send_request(self, mcp_id: int, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC 2.0 request to an MCP server and read the response."""
        process = self.running_mcps.get(mcp_id)
        if not process or not process.stdin or not process.stdout:
            return {"jsonrpc": "2.0", "error": {"code": -32000, "message": "MCP process not available"}, "id": None}

        request = {
            "jsonrpc": "2.0",
            "id": _next_id(),
            "method": method,
            "params": params or {},
        }

        try:
            payload = json.dumps(request) + "\n"
            process.stdin.write(payload.encode())
            await process.stdin.drain()

            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30)
            response = json.loads(response_line.decode().strip())
            return response
        except asyncio.TimeoutError:
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Request timed out"}, "id": None}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return {"jsonrpc": "2.0", "error": {"code": -32002, "message": f"Invalid response: {e}"}, "id": None}
        except Exception as e:
            logger.error("mcp_request_error", mcp_id=mcp_id, method=method, error=str(e))
            return {"jsonrpc": "2.0", "error": {"code": -32003, "message": str(e)}, "id": None}

    # ────────── Tool Discovery ──────────

    async def list_tools(self, mcp_id: int) -> list[dict]:
        """List available tools from a specific MCP server.

        Returns list of tool definitions in OpenAI-compatible format:
          [{"name": "...", "description": "...", "input_schema": {...}}]
        """
        # Return cached tools if available
        if mcp_id in self._tool_cache:
            return self._tool_cache[mcp_id]

        response = await self._send_request(mcp_id, "tools/list")
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            # Normalize: ensure each tool has name, description, input_schema
            normalized = []
            for tool in tools:
                normalized.append({
                    "name": tool.get("name", "unknown"),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("inputSchema", tool.get("input_schema", {})),
                })
            self._tool_cache[mcp_id] = normalized
            return normalized

        return []

    async def get_all_enabled_tools(self) -> list[dict]:
        """Collect tool definitions from all running MCP servers.

        Returns flattened list of tools in OpenAI function-calling format.
        Each tool has a name prefixed by its MCP server name to avoid collisions.
        """
        all_tools = []
        for mcp_id, process in list(self.running_mcps.items()):
            if process.returncode is not None:
                # Process died, remove it
                del self.running_mcps[mcp_id]
                self._tool_cache.pop(mcp_id, None)
                continue

            info = self._mcp_info.get(mcp_id, {})
            mcp_name = info.get("name", f"mcp-{mcp_id}")

            tools = await self.list_tools(mcp_id)
            for tool in tools:
                # Prefix tool name with MCP name to avoid collisions
                qualified_name = f"{mcp_name}__{tool['name']}"
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": qualified_name,
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                    "_mcp_id": mcp_id,
                    "_mcp_name": mcp_name,
                    "_raw_name": tool["name"],
                })

        return all_tools

    async def execute_tool(self, mcp_id: int, tool_name: str, args: dict[str, Any]) -> dict:
        """Execute a tool call on an MCP server using JSON-RPC 2.0.

        Args:
            mcp_id: MCP server ID
            tool_name: The raw tool name (without MCP prefix)
            args: Tool arguments
        """
        if mcp_id not in self.running_mcps:
            return {"status": "error", "message": "MCP not running"}

        response = await self._send_request(mcp_id, "tools/call", {
            "name": tool_name,
            "arguments": args,
        })

        if "result" in response:
            result = response["result"]
            log_manager.log_mcp_event("tool_executed", mcp_id=mcp_id, tool=tool_name)
            return {"status": "success", "result": result.get("content", str(result))}
        elif "error" in response:
            err = response["error"]
            return {"status": "error", "message": err.get("message", "Unknown error")}
        else:
            return {"status": "error", "message": "Invalid response from MCP"}

    # ────────── Lifecycle ──────────

    async def register_mcp(self, mcp_data: dict) -> dict:
        """Register a new MCP server."""
        try:
            # Validate command safety
            if mcp_data.get("command"):
                cmd = mcp_data["command"].lower().split()[0] if isinstance(mcp_data["command"], str) else mcp_data["command"]
                if cmd in BLOCKED_COMMANDS:
                    return {"status": "error", "message": f"Command '{cmd}' is blocked for security reasons"}

            # Validate transport
            valid_transports = ["stdio", "sse", "http"]
            if mcp_data.get("transport", "stdio") not in valid_transports:
                return {"status": "error", "message": f"Invalid transport. Must be one of: {valid_transports}"}

            log_manager.log_mcp_event("mcp_registered", mcp_name=mcp_data.get("name"))
            return {"status": "registered", "mcp": mcp_data}
        except Exception as e:
            logger.error("register_mcp_error", error=str(e))
            return {"status": "error", "message": str(e)}

    async def delete_mcp(self, mcp_id: int) -> dict:
        """Delete an MCP server and stop it if running."""
        if mcp_id in self.running_mcps:
            await self.stop_mcp(mcp_id)
        self._mcp_info.pop(mcp_id, None)
        self._tool_cache.pop(mcp_id, None)
        log_manager.log_mcp_event("mcp_deleted", mcp_name=str(mcp_id))
        return {"status": "deleted", "id": mcp_id}

    async def enable_mcp(self, mcp: MCP) -> dict:
        """Enable and start an MCP server."""
        try:
            if mcp.id in self.running_mcps:
                return {"status": "already_running", "id": mcp.id}

            command = mcp.command or ""
            if not command:
                return {"status": "error", "message": "No command configured for MCP"}

            # Security check
            cmd_name = command.split()[0] if isinstance(command, str) else command
            if cmd_name not in ALLOWED_COMMANDS:
                logger.warning("mcp_command_not_allowed", command=cmd_name, mcp=mcp.name)
                return {"status": "error", "message": f"Command '{cmd_name}' is not in the allowed list: {ALLOWED_COMMANDS}"}

            args = json.loads(mcp.args) if isinstance(mcp.args, str) else (mcp.args or [])
            cmd_parts = [command] + list(args)

            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self.running_mcps[mcp.id] = process
            self._mcp_info[mcp.id] = {
                "name": mcp.name,
                "type": mcp.type,
                "transport": mcp.transport,
                "command": command,
            }

            # Give the MCP server a moment to initialize
            await asyncio.sleep(0.5)

            # Discover available tools
            try:
                tools = await self.list_tools(mcp.id)
                logger.info("mcp_tools_discovered", mcp_name=mcp.name, tool_count=len(tools))
            except Exception as e:
                logger.warning("mcp_tools_discovery_failed", mcp_name=mcp.name, error=str(e))

            log_manager.log_mcp_event("mcp_enabled", mcp_name=mcp.name, pid=process.pid)
            return {"status": "started", "id": mcp.id, "pid": process.pid}

        except FileNotFoundError:
            return {"status": "error", "message": f"Command not found: {mcp.command}"}
        except Exception as e:
            logger.error("enable_mcp_error", mcp=mcp.name, error=str(e))
            return {"status": "error", "message": str(e)}

    async def disable_mcp(self, mcp: MCP) -> dict:
        """Disable and stop an MCP server."""
        return await self.stop_mcp(mcp.id)

    async def stop_mcp(self, mcp_id: int) -> dict:
        """Stop a running MCP server."""
        process = self.running_mcps.get(mcp_id)
        if not process:
            return {"status": "not_running", "id": mcp_id}

        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            del self.running_mcps[mcp_id]
            self._tool_cache.pop(mcp_id, None)
            self._mcp_info.pop(mcp_id, None)
            return {"status": "stopped", "id": mcp_id}
        except Exception as e:
            logger.error("stop_mcp_error", mcp_id=mcp_id, error=str(e))
            return {"status": "error", "message": str(e)}

    async def test_mcp(self, mcp: MCP) -> dict:
        """Test MCP connectivity/health."""
        if mcp.transport == "http" and mcp.endpoint:
            import httpx
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(mcp.endpoint)
                    return {"status": "healthy" if response.status_code < 500 else "unhealthy", "code": response.status_code}
            except Exception as e:
                return {"status": "unreachable", "error": str(e)}
        elif mcp.transport == "stdio":
            return {"status": "healthy"} if mcp.id in self.running_mcps else {"status": "inactive"}
        return {"status": "unknown"}

    async def get_mcp_logs(self, mcp_id: int, lines: int = 50) -> list[str]:
        """Get recent logs from an MCP server."""
        process = self.running_mcps.get(mcp_id)
        if not process or not process.stdout:
            return ["MCP not running"]

        try:
            output = await asyncio.wait_for(process.stdout.read(), timeout=2)
            text = output.decode().strip()
            return text.split("\n")[-lines:] if text else ["No output"]
        except asyncio.TimeoutError:
            return ["Log output timeout"]
        except Exception as e:
            return [f"Error reading logs: {str(e)}"]

    async def cleanup_all(self):
        """Stop all running MCP processes."""
        for mcp_id in list(self.running_mcps.keys()):
            await self.stop_mcp(mcp_id)
        self._tool_cache.clear()
        self._mcp_info.clear()
        logger.info("all_mcps_cleaned")
