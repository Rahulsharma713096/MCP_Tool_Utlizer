"""MCP Manager - Cross-platform MCP server lifecycle management.

Supports Windows, Linux, and macOS with proper process spawning,
validation, and detailed error reporting.
"""

import asyncio
import json
import subprocess
import sys
import shutil
import os
from typing import Optional, Any
from pathlib import Path

from models.database import MCP
from core.logging import log_manager

logger = log_manager.get_logger("mcp_service")

# Security: Allowed commands and paths for MCP execution
ALLOWED_COMMANDS = ["python", "node", "python3", "npx"]
BLOCKED_COMMANDS = ["rm", "del", "format", "dd", "mkfs", "sudo", "chmod", "shutdown"]

# JSON-RPC request ID counter
_rpc_id = 0

IS_WINDOWS = sys.platform == "win32"


def _next_id() -> int:
    global _rpc_id
    _rpc_id += 1
    return _rpc_id


def _resolve_command(command: str) -> str:
    """Resolve a command to its full path on the current platform.

    On Windows, resolves 'npx' to 'npx.cmd', 'node' to 'node.exe', etc.
    On Unix, uses shutil.which() for PATH resolution.
    """
    if not command:
        return command

    base_name = os.path.basename(command).replace(".exe", "").replace(".cmd", "").replace(".bat", "").lower()

    if IS_WINDOWS:
        # On Windows, npx is actually npx.cmd, node is node.exe
        extensions = [".cmd", ".exe", ".bat", ""]
        for ext in extensions:
            resolved = shutil.which(f"{base_name}{ext}")
            if resolved:
                return resolved
        # Fallback: return as-is and let subprocess handle it
        return command
    else:
        resolved = shutil.which(base_name)
        return resolved or command


def _get_executable_name(command: str) -> str:
    """Extract the base executable name from a command path."""
    raw = os.path.basename(command) if command else ""
    return raw.replace(".exe", "").replace(".cmd", "").replace(".bat", "").lower()


# MCP lifecycle states
MCP_STATE_STARTING = "starting"
MCP_STATE_CONNECTED = "connected"
MCP_STATE_DISCONNECTED = "disconnected"
MCP_STATE_FAILED = "failed"
MCP_STATE_RESTARTING = "restarting"


class MCPService:
    """Manages MCP server lifecycle - registration, execution, and monitoring."""

    def __init__(self):
        self.running_mcps: dict[int, subprocess.Popen] = {}
        self._mcp_info: dict[int, dict] = {}
        self._tool_cache: dict[int, list[dict]] = {}
        self._log_buffers: dict[int, list[str]] = {}
        self._mcp_lifecycle: dict[int, str] = {}  # mcp_id -> state string

    # ────────── Validation ──────────

    async def validate_mcp_config(self, config: dict) -> dict:
        """Validate an MCP configuration before enabling.

        Returns {"valid": bool, "errors": list[str], "warnings": list[str]}.
        """
        errors: list[str] = []
        warnings: list[str] = []
        transport = config.get("transport", "stdio")

        if transport in ("http", "sse"):
            endpoint = config.get("endpoint", "")
            if not endpoint:
                errors.append("HTTP/SSE transport requires an 'endpoint' URL")
            elif not endpoint.startswith(("http://", "https://")):
                errors.append(f"Endpoint must be a valid URL starting with http:// or https://, got: {endpoint}")
            return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

        # stdio transport validation
        command = config.get("command", "")
        if not command:
            errors.append("No command specified. Provide a command like 'npx', 'node', or 'python'")
            return {"valid": False, "errors": errors, "warnings": warnings}

        cmd_name = _get_executable_name(command)
        if cmd_name in BLOCKED_COMMANDS:
            errors.append(f"Command '{command}' is blocked for security reasons")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check if the command exists on the system
        resolved = _resolve_command(cmd_name)
        if not resolved and cmd_name not in ALLOWED_COMMANDS:
            warnings.append(f"Command '{cmd_name}' not found in PATH — it may still work if installed")

        # Check for npx-specific prerequisites
        if cmd_name == "npx":
            node_path = shutil.which("node") or shutil.which("node.exe")
            npm_path = shutil.which("npm") or shutil.which("npm.cmd")
            npx_path = shutil.which("npx") or shutil.which("npx.cmd")
            if not node_path:
                errors.append("Node.js is not installed or not in PATH. Install from https://nodejs.org")
            if not npm_path:
                warnings.append("npm not found in PATH — required for npx package resolution")
            if not npx_path and not resolved:
                errors.append("npx not found in PATH. Install Node.js from https://nodejs.org")

        args = config.get("args", [])
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip().startswith("[") else args.split()
            except (json.JSONDecodeError, ValueError):
                args = [args]
        if not args:
            if cmd_name == "npx":
                warnings.append("No args provided — npx requires at least a package name (e.g. '-y', '@scope/package')")
        elif cmd_name == "npx":
            # Validate npm package names for security
            import re
            for arg in args:
                if arg.startswith("@"):
                    # Scoped package: @scope/package
                    if not re.match(r'^@[a-z0-9][\w.-]*/[a-z0-9][\w.-]*$', arg):
                        errors.append(f"Invalid npm package name: '{arg}'")
                elif not arg.startswith("-"):
                    # Regular package or path, ensure no shell metacharacters
                    if re.search(r'[;&|`$()\n]', arg):
                        errors.append(f"Security: package name contains shell metacharacters: '{arg[:30]}'")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    async def check_prerequisites(self) -> dict:
        """Check system prerequisites for running MCP servers."""
        results: dict[str, Any] = {"node": None, "npm": None, "npx": None, "python": None}

        for tool in ["node", "npm", "npx", "python"]:
            paths_to_check = [tool]
            if IS_WINDOWS:
                paths_to_check = [f"{tool}.exe", f"{tool}.cmd", tool]
            found = False
            for p in paths_to_check:
                if shutil.which(p):
                    found = True
                    break
            results[tool] = found

        return results

    # ────────── JSON-RPC Helpers ──────────

    async def _send_jsonrpc(self, mcp_id: int, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC 2.0 request (public alias for internal use)."""
        return await self._send_request(mcp_id, method, params)

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
        """List available tools from a specific MCP server."""
        if mcp_id in self._tool_cache:
            return self._tool_cache[mcp_id]

        response = await self._send_request(mcp_id, "tools/list")
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
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
        """Collect tool definitions from all running MCP servers."""
        all_tools = []
        for mcp_id in list(self.running_mcps.keys()):
            process = self.running_mcps.get(mcp_id)
            if process is None:
                continue
            if process.returncode is not None:
                del self.running_mcps[mcp_id]
                self._tool_cache.pop(mcp_id, None)
                self._mcp_info.pop(mcp_id, None)
                self._mcp_lifecycle[mcp_id] = MCP_STATE_DISCONNECTED
                continue
            # Skip MCPs still initializing
            if self._mcp_lifecycle.get(mcp_id) == MCP_STATE_STARTING:
                continue

            info = self._mcp_info.get(mcp_id, {})
            mcp_name = info.get("name", f"mcp-{mcp_id}")

            tools = await self.list_tools(mcp_id)
            for tool in tools:
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
        """Execute a tool call on an MCP server using JSON-RPC 2.0."""
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
            if mcp_data.get("command"):
                cmd = mcp_data["command"].lower().split()[0] if isinstance(mcp_data["command"], str) else mcp_data["command"]
                if cmd in BLOCKED_COMMANDS:
                    return {"status": "error", "message": f"Command '{cmd}' is blocked for security reasons"}

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
        """Enable and start an MCP server with full validation and logging."""
        mcp_name = mcp.name or f"mcp-{mcp.id}"
        logger.info("mcp_enable_start", mcp_name=mcp_name, transport=mcp.transport, command=mcp.command)

        try:
            if mcp.id in self.running_mcps:
                logger.info("mcp_already_running", mcp_name=mcp_name, mcp_id=mcp.id)
                return {"status": "already_running", "id": mcp.id}

            self._mcp_lifecycle[mcp.id] = MCP_STATE_STARTING

            # Handle HTTP/SSE transport
            if mcp.transport in ("http", "sse"):
                reachable = await self._test_http_endpoint(mcp.endpoint)
                self._mcp_info[mcp.id] = {
                    "name": mcp_name,
                    "type": mcp.type,
                    "transport": mcp.transport,
                    "endpoint": mcp.endpoint,
                }
                logger.info("mcp_enabled_http", mcp_name=mcp_name, endpoint=mcp.endpoint, reachable=reachable)
                self._mcp_lifecycle[mcp.id] = MCP_STATE_CONNECTED if reachable else MCP_STATE_DISCONNECTED
                result = {"status": "started", "id": mcp.id, "transport": mcp.transport}
                if not reachable:
                    result["warning"] = f"Endpoint not reachable: {mcp.endpoint}"
                return result

            # stdio transport: spawn subprocess
            command = mcp.command or ""
            if not command:
                self._mcp_lifecycle.pop(mcp.id, None)
                return {"status": "error", "message": "No command configured for MCP"}

            cmd_name = _get_executable_name(command)
            if cmd_name not in ALLOWED_COMMANDS:
                logger.warning("mcp_command_not_allowed", command=command, mcp=mcp_name)
                self._mcp_lifecycle.pop(mcp.id, None)
                return {"status": "error", "message": f"Command '{cmd_name}' is not in the allowed list: {ALLOWED_COMMANDS}"}

            args = mcp.args
            if isinstance(args, str):
                try:
                    parsed = json.loads(args)
                    args = parsed if isinstance(parsed, list) else [parsed]
                except (json.JSONDecodeError, ValueError):
                    args = args.split() if ' ' in args else [args]
            args = args or []
            if not args:
                self._mcp_lifecycle.pop(mcp.id, None)
                return {
                    "status": "error",
                    "message": f"No arguments configured for '{command}'. "
                    f"MCP '{mcp_name}' needs package args (e.g. '-y', '@scope/package'). "
                    f"Example: npx -y @openbnb/mcp-server-airbnb",
                }

            # Resolve command for cross-platform compatibility
            resolved_cmd = _resolve_command(cmd_name)
            cmd_parts = [resolved_cmd] + list(args)

            logger.info("mcp_spawning", mcp_name=mcp_name, command=resolved_cmd, args=args)

            # On Windows, .cmd files need shell=True to execute properly
            use_shell = IS_WINDOWS and resolved_cmd.lower().endswith('.cmd')
            if use_shell:
                shell_cmd = f'"{resolved_cmd}" {" ".join(str(a) for a in args)}'
                process = await asyncio.create_subprocess_shell(
                    shell_cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "FORCE_COLOR": "0"},
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd_parts,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "FORCE_COLOR": "0"},
                )

            logger.info("mcp_process_started", mcp_name=mcp_name, pid=process.pid)

            # Wait for process to initialize (longer for npx which may need to install packages)
            init_waits = [0.5, 1.0, 2.0, 3.0, 5.0]
            process_stayed_alive = False
            for delay in init_waits:
                await asyncio.sleep(delay)
                if process.returncode is not None:
                    break
                process_stayed_alive = True

            if process.returncode is not None:
                stderr_output = ""
                try:
                    stderr_data = await asyncio.wait_for(process.stderr.read(), timeout=3)
                    stderr_output = stderr_data.decode().strip()[:500]
                except (asyncio.TimeoutError, Exception):
                    pass

                error_msg = f"MCP '{mcp_name}' exited immediately (code {process.returncode})"
                if stderr_output:
                    error_msg += f": {stderr_output}"

                suggestions = []
                if cmd_name == "npx":
                    suggestions.extend([
                        "Install Node.js from https://nodejs.org",
                        "Verify npx works: open a terminal and run 'npx -v'",
                        "Try running the command manually: " + " ".join(cmd_parts),
                    ])
                elif cmd_name in ("python", "python3"):
                    suggestions.extend([
                        "Verify Python is installed: 'python --version'",
                        "Try running the command manually: " + " ".join(cmd_parts),
                    ])
                elif cmd_name == "node":
                    suggestions.extend([
                        "Install Node.js from https://nodejs.org",
                        "Verify node works: 'node -v'",
                    ])

                self._mcp_lifecycle[mcp.id] = MCP_STATE_FAILED
                logger.error("mcp_start_failed", mcp_name=mcp_name, exit_code=process.returncode, stderr=stderr_output)
                return {
                    "status": "error",
                    "message": error_msg,
                    "suggestions": suggestions,
                    "command": " ".join(cmd_parts),
                    "exit_code": process.returncode,
                }

            self.running_mcps[mcp.id] = process
            self._mcp_info[mcp.id] = {
                "name": mcp_name,
                "type": mcp.type,
                "transport": mcp.transport,
                "command": command,
            }
            self._log_buffers[mcp.id] = []

            # Start background log collection
            async def _collect_logs(pid: int, proc: asyncio.subprocess.Process):
                try:
                    while proc.returncode is None:
                        line = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
                        if not line:
                            break
                        text = line.decode().strip()
                        if text:
                            self._log_buffers.setdefault(pid, []).append(text)
                            if len(self._log_buffers[pid]) > 200:
                                self._log_buffers[pid] = self._log_buffers[pid][-200:]
                except (asyncio.TimeoutError, Exception):
                    pass
            asyncio.create_task(_collect_logs(mcp.id, process))

            # Send MCP initialize request to validate server is working
            try:
                init_response = await self._send_jsonrpc(mcp.id, "initialize", {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {"name": "ai-workspace", "version": "1.0.0"},
                })
                if "error" in init_response:
                    logger.warning("mcp_init_failed", mcp_name=mcp_name, error=init_response["error"].get("message", ""))
                    # Still mark as connected (some MCPs don't support initialize)
                    self._mcp_lifecycle[mcp.id] = MCP_STATE_CONNECTED
                else:
                    self._mcp_lifecycle[mcp.id] = MCP_STATE_CONNECTED
                    logger.info("mcp_initialized", mcp_name=mcp_name)
            except Exception as e:
                logger.warning("mcp_init_exception", mcp_name=mcp_name, error=str(e))
                self._mcp_lifecycle[mcp.id] = MCP_STATE_CONNECTED  # Treat as connected even if init fails

            # Discover available tools
            try:
                tools = await self.list_tools(mcp.id)
                logger.info("mcp_tools_discovered", mcp_name=mcp_name, tool_count=len(tools))
            except Exception as e:
                logger.warning("mcp_tools_discovery_failed", mcp_name=mcp_name, error=str(e))

            log_manager.log_mcp_event("mcp_enabled", mcp_name=mcp_name, pid=process.pid)
            return {
                "status": "started",
                "id": mcp.id,
                "pid": process.pid,
                "lifecycle": self._mcp_lifecycle.get(mcp.id, MCP_STATE_CONNECTED),
            }

        except FileNotFoundError:
            error_msg = f"Command not found: {mcp.command}"
            suggestions = [
                f"Ensure '{cmd_name}' is installed and in your PATH",
                "Restart the application after installing",
                f"Verify: run '{cmd_name} -v' in a terminal",
            ]
            if cmd_name == "npx":
                suggestions.insert(0, "Install Node.js from https://nodejs.org")
            self._mcp_lifecycle[mcp.id] = MCP_STATE_FAILED
            logger.error("mcp_command_not_found", mcp_name=mcp_name, command=mcp.command)
            return {"status": "error", "message": error_msg, "suggestions": suggestions}
        except Exception as e:
            self._mcp_lifecycle[mcp.id] = MCP_STATE_FAILED
            logger.error("enable_mcp_error", mcp=mcp_name, error=str(e))
            return {"status": "error", "message": f"Failed to start MCP '{mcp_name}': {str(e)}"}

    async def disable_mcp(self, mcp: MCP) -> dict:
        """Disable and stop an MCP server."""
        return await self.stop_mcp(mcp.id)

    async def stop_mcp(self, mcp_id: int) -> dict:
        """Stop a running MCP server."""
        process = self.running_mcps.get(mcp_id)
        if not process:
            self._mcp_lifecycle[mcp_id] = MCP_STATE_DISCONNECTED
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
            mcp_name = self._mcp_info.get(mcp_id, {}).get("name", str(mcp_id))
            self._mcp_info.pop(mcp_id, None)
            self._log_buffers.pop(mcp_id, None)
            self._mcp_lifecycle[mcp_id] = MCP_STATE_DISCONNECTED
            logger.info("mcp_stopped", mcp_name=mcp_name, mcp_id=mcp_id)
            return {"status": "stopped", "id": mcp_id}
        except Exception as e:
            logger.error("stop_mcp_error", mcp_id=mcp_id, error=str(e))
            return {"status": "error", "message": str(e)}

    async def _test_http_endpoint(self, endpoint: str | None) -> bool:
        """Test if an HTTP endpoint is reachable."""
        if not endpoint:
            return False
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Try HEAD first (lighter), fall back to GET
                try:
                    response = await client.head(endpoint)
                except httpx.HTTPError:
                    response = await client.get(endpoint)
                return response.status_code < 500
        except Exception:
            return False

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
        # First check the log buffer (most reliable)
        buffer = self._log_buffers.get(mcp_id, [])
        if buffer:
            return buffer[-lines:]

        # Fallback: try reading from stdout directly (one-shot)
        process = self.running_mcps.get(mcp_id)
        if not process or not process.stdout:
            return ["MCP not running"]

        try:
            output = await asyncio.wait_for(process.stdout.read(), timeout=2)
            text = output.decode().strip()
            return text.split("\n")[-lines:] if text else ["No output"]
        except asyncio.TimeoutError:
            return ["No new log output"]
        except Exception as e:
            return [f"Error reading logs: {str(e)}"]

    async def cleanup_all(self):
        """Stop all running MCP processes."""
        for mcp_id in list(self.running_mcps.keys()):
            await self.stop_mcp(mcp_id)
        self._tool_cache.clear()
        self._mcp_info.clear()
        self._mcp_lifecycle.clear()
        logger.info("all_mcps_cleaned")
