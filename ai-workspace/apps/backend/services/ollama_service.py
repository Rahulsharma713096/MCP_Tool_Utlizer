"""Ollama Runtime Manager - local LLM lifecycle control."""

import asyncio
import subprocess
import os
import signal
import sys
from typing import Optional
import httpx

import psutil

from config.settings import settings
from core.logging import log_manager

logger = log_manager.get_logger("ollama_service")


def _run_command(cmd: list[str], timeout: int = 30) -> tuple[str, str]:
    """Run a shell command synchronously via subprocess.run().
    
    Compatible with Python 3.14+ on all platforms (avoids asyncio.create_subprocess_exec issues on Windows).
    Call via asyncio.to_thread() from async methods.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        raise asyncio.TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from e
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Command not found: {cmd[0]}") from e


class OllamaService:
    """Manages Ollama installation detection, model lifecycle, and runtime monitoring."""

    def __init__(self):
        self.ollama_host = settings.OLLAMA_HOST
        self.running_processes: dict[str, int] = {}  # model_name -> pid

    async def detect_ollama(self) -> bool:
        """Check if Ollama is installed and accessible."""
        try:
            stdout, _ = await asyncio.to_thread(_run_command, ["ollama", "--version"], 10)
            version = stdout.strip()
            logger.info("ollama_detected", version=version)
            return True
        except (FileNotFoundError, asyncio.TimeoutError, subprocess.CalledProcessError) as e:
            logger.warning("ollama_not_detected", error=str(e))
            return False

    async def get_ollama_version(self) -> Optional[str]:
        """Get installed Ollama version."""
        try:
            stdout, _ = await asyncio.to_thread(_run_command, ["ollama", "--version"], 10)
            return stdout.strip()
        except Exception:
            return None

    async def list_models(self) -> list[dict]:
        """Fetch installed models from Ollama.
        
        Tries HTTP API first, then falls back to `ollama list` CLI command.
        """
        # Try HTTP API first
        models = await self._list_models_via_api()
        if models:
            return models

        # Fallback: parse `ollama list` CLI output
        logger.info("trying_cli_fallback")
        try:
            stdout, stderr = await asyncio.to_thread(_run_command, ["ollama", "list"], 15)
            output = stdout.strip()
            if not output or stderr.strip():
                logger.warning("ollama_list_no_output", stderr=stderr.strip())
                return []

            lines = output.split("\n")
            if len(lines) < 2:
                return []

            models = []
            for line in lines[1:]:  # Skip header line
                line = line.strip()
                if not line:
                    continue
                # Use maxsplit=3 so "3.2 GB" stays together as one token
                parts = line.split(maxsplit=3)
                if len(parts) >= 3:
                    # CLI returns human-readable dates like "2 days ago" —
                    # clear it since frontend expects ISO format
                    modified_at = ""

                    models.append({
                        "name": parts[0],
                        "size": self._parse_ollama_size(parts[2]) if parts[2] != "0" else 0,
                        "quantization": "unknown",
                        "modified_at": modified_at,
                    })

            logger.info("models_fetched_via_cli", count=len(models))
            return models
        except (FileNotFoundError, asyncio.TimeoutError, subprocess.CalledProcessError) as e:
            logger.warning("ollama_list_cli_failed", error=str(e))
            return []
        except Exception as e:
            logger.error("ollama_list_cli_error", error=str(e))
            return []

    async def _list_models_via_api(self) -> list[dict]:
        """Fetch installed models via Ollama HTTP API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.ollama_host}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model in data.get("models", []):
                        models.append({
                            "name": model.get("name"),
                            "size": model.get("size"),
                            "quantization": model.get("details", {}).get("quantization", "unknown"),
                            "modified_at": model.get("modified_at"),
                        })
                    if models:
                        logger.info("models_fetched_via_api", count=len(models))
                        return models
            return []
        except httpx.ConnectError:
            logger.warning("ollama_api_unreachable")
            return []
        except Exception as e:
            logger.error("fetch_models_api_error", error=str(e))
            return []

    @staticmethod
    def _parse_ollama_size(size_str: str) -> int:
        """Parse Ollama size string (e.g. '4.7GB', '356MB') to bytes."""
        try:
            size_str = size_str.upper().replace("B", "").strip()
            if size_str.endswith("G"):
                return int(float(size_str[:-1]) * 1024**3)
            elif size_str.endswith("M"):
                return int(float(size_str[:-1]) * 1024**2)
            elif size_str.endswith("K"):
                return int(float(size_str[:-1]) * 1024)
            else:
                return int(float(size_str))
        except (ValueError, IndexError):
            return 0

    async def start_model(self, model_name: str) -> dict:
        """Start a model runtime via Ollama API."""
        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={"model": model_name, "prompt": "", "stream": False},
                )
                if response.status_code == 200:
                    pid = self._find_ollama_process(model_name)
                    self.running_processes[model_name] = pid
                    log_manager.log_runtime_event("model_started", model=model_name, pid=pid)
                    return {"status": "started", "model": model_name, "pid": pid}
                else:
                    return {"status": "error", "message": response.text}
        except httpx.ConnectError:
            return {"status": "error", "message": "Ollama API not reachable"}
        except Exception as e:
            logger.error("start_model_error", model=model_name, error=str(e))
            return {"status": "error", "message": str(e)}

    async def stop_model(self, model_name: str) -> dict:
        """Stop a running model by killing its process."""
        pid = self.running_processes.get(model_name)
        if pid:
            try:
                process = psutil.Process(pid)
                process.terminate()
                process.wait(timeout=5)
                del self.running_processes[model_name]
                log_manager.log_runtime_event("model_stopped", model=model_name, pid=pid)
                return {"status": "stopped", "model": model_name}
            except psutil.NoSuchProcess:
                del self.running_processes[model_name]
                return {"status": "already_stopped", "model": model_name}
            except psutil.TimeoutExpired:
                process.kill()
                del self.running_processes[model_name]
                return {"status": "force_stopped", "model": model_name}
        else:
            # Model not tracked in running_processes
            return {"status": "not_found", "model": model_name}

    def _find_ollama_process(self, model_name: str) -> int:
        """Find the PID of an ollama process for the given model."""
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if "ollama" in proc.info["name"].lower():
                    # Check if this process is running the requested model
                    cmdline = proc.info.get("cmdline", [])
                    if not model_name or any(model_name in arg for arg in cmdline):
                        return proc.info["pid"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return 0

    async def _kill_ollama_process(self, model_name: str) -> dict:
        """Find and kill ollama processes."""
        killed = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if "ollama" in proc.info["name"].lower():
                    proc.kill()
                    killed.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if killed:
            return {"status": "killed", "pids": killed}
        return {"status": "not_found"}

    async def get_model_runtime_info(self, model_name: str) -> dict:
        """Get runtime metrics for a specific model."""
        info = {
            "name": model_name,
            "running": model_name in self.running_processes,
            "cpu_percent": 0.0,
            "ram_mb": 0.0,
            "pid": self.running_processes.get(model_name, 0),
        }
        pid = self.running_processes.get(model_name)
        if pid:
            try:
                proc = psutil.Process(pid)
                info["cpu_percent"] = proc.cpu_percent(interval=0.1)
                info["ram_mb"] = proc.memory_info().rss / (1024 * 1024)
            except psutil.NoSuchProcess:
                info["running"] = False
        return info

    async def kill_all_processes(self) -> dict:
        """Kill all running Ollama processes."""
        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if "ollama" in proc.info["name"].lower():
                    proc.kill()
                    killed.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self.running_processes.clear()
        log_manager.log_runtime_event("all_processes_killed", count=len(killed))
        return {"status": "cleaned", "killed_count": len(killed)}

    async def health_check(self) -> dict:
        """Check Ollama API health."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.ollama_host}/api/tags")
                return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception:
            return {"status": "unreachable"}
