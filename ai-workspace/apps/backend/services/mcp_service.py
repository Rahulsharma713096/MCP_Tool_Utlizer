"""MCP Manager - Plugin ecosystem for Model Context Protocol servers."""

import asyncio
import json
import subprocess
from typing import Optional, Any
from pathlib import Path
import signal

from models.database import MCP
from core.logging import log_manager

logger = log_manager.get_logger("mcp_service")

# Security: Allowed commands and paths for MCP execution
ALLOWED_COMMANDS = ["python", "node", "python3", "npx"]
ALLOWED_PATHS = ["/workspace", "/documents", "/home", "/tmp"]
BLOCKED_COMMANDS = ["rm", "del", "format", "dd", "mkfs", "sudo", "chmod", "shutdown"]


class MCPService:
    """Manages MCP server lifecycle - registration, execution, and monitoring."""

    def __init__(self):
        self.running_mcps: dict[int, subprocess.Popen] = {}

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
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self.running_mcps[mcp.id] = process
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

    async def execute_tool(self, mcp: MCP, tool_name: str, args: dict[str, Any]) -> dict:
        """Execute a tool call on an MCP server."""
        if not mcp.enabled:
            return {"status": "error", "message": "MCP is disabled"}

        if mcp.id not in self.running_mcps:
            result = await self.enable_mcp(mcp)
            if result["status"] != "started":
                return {"status": "error", "message": f"Cannot start MCP: {result.get('message')}"}

        process = self.running_mcps.get(mcp.id)
        if not process:
            return {"status": "error", "message": "MCP process not available"}

        try:
            tool_call = json.dumps({"tool": tool_name, "args": args}) + "\n"
            if process.stdin:
                process.stdin.write(tool_call.encode())
                await process.stdin.drain()

                response = await asyncio.wait_for(process.stdout.readline(), timeout=30)
                result = json.loads(response.decode())
                log_manager.log_mcp_event("tool_executed", mcp_name=mcp.name, tool=tool_name)
                return {"status": "success", "result": result}
        except asyncio.TimeoutError:
            return {"status": "error", "message": "Tool execution timeout"}
        except Exception as e:
            logger.error("execute_tool_error", mcp=mcp.name, tool=tool_name, error=str(e))
            return {"status": "error", "message": str(e)}

    async def cleanup_all(self):
        """Stop all running MCP processes."""
        for mcp_id in list(self.running_mcps.keys()):
            await self.stop_mcp(mcp_id)
        logger.info("all_mcps_cleaned")
