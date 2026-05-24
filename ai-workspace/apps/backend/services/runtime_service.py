"""Runtime Service - System resource monitoring and process management."""

import asyncio
import platform
import shutil
from typing import Optional
from datetime import datetime, timezone

import psutil

from config.settings import settings
from core.logging import log_manager

logger = log_manager.get_logger("runtime_service")


class RuntimeService:
    """Monitors system resources and manages runtime processes."""

    def __init__(self):
        self._metrics_history: list[dict] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def get_system_info(self) -> dict:
        """Get comprehensive system information."""
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "cpus": psutil.cpu_count(),
            "total_ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_ram_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "total_disk_gb": 0,
            "free_disk_gb": 0,
            "gpu_available": False,
            "gpu_name": None,
        }

        # Disk info
        try:
            disk = shutil.disk_usage("/")
            info["total_disk_gb"] = round(disk.total / (1024**3), 2)
            info["free_disk_gb"] = round(disk.free / (1024**3), 2)
        except Exception:
            pass

        # GPU detection
        gpu_info = await self._detect_gpu()
        info.update(gpu_info)

        return info

    async def get_current_metrics(self) -> dict:
        """Get current system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()

            metrics = {
                "cpu_percent": cpu_percent,
                "ram_percent": round(ram.percent, 2),
                "ram_used_gb": round(ram.used / (1024**3), 2),
                "ram_total_gb": round(ram.total / (1024**3), 2),
                "gpu_percent": None,
                "vram_used_gb": None,
                "active_models": 0,
                "active_mcps": 0,
                "token_throughput": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # GPU metrics
            gpu_metrics = await self._get_gpu_metrics()
            metrics.update(gpu_metrics)

            # Count active processes
            metrics["active_models"] = self._count_processes("ollama")
            metrics["active_mcps"] = self._count_mcp_processes()

            self._metrics_history.append(metrics)
            if len(self._metrics_history) > 1000:
                self._metrics_history = self._metrics_history[-500:]

            return metrics
        except Exception as e:
            logger.error("metrics_error", error=str(e))
            return {
                "cpu_percent": 0,
                "ram_percent": 0,
                "ram_used_gb": 0,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def get_metrics_history(self, minutes: int = 5) -> list[dict]:
        """Get metrics history for the last N minutes."""
        cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)
        return [
            m for m in self._metrics_history
            if m.get("timestamp") and self._parse_timestamp(m["timestamp"]) >= cutoff
        ]

    def _parse_timestamp(self, ts: str) -> float:
        try:
            return datetime.fromisoformat(ts).timestamp()
        except Exception:
            return 0

    async def _detect_gpu(self) -> dict:
        """Detect GPU availability."""
        try:
            # Try nvidia-smi
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi", "--query-gpu=name", "--format=csv,noheader",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            gpu_name = stdout.decode().strip()
            if gpu_name:
                return {"gpu_available": True, "gpu_name": gpu_name}
        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            pass

        # Try torch
        try:
            import torch
            if torch.cuda.is_available():
                return {"gpu_available": True, "gpu_name": torch.cuda.get_device_name(0)}
        except ImportError:
            pass

        return {"gpu_available": False, "gpu_name": None}

    async def _get_gpu_metrics(self) -> dict:
        """Get GPU metrics if available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            parts = stdout.decode().strip().split(", ")
            if len(parts) >= 2:
                return {
                    "gpu_percent": float(parts[0]),
                    "vram_used_gb": float(parts[1]) / 1024 if parts[1] else None,
                }
        except Exception:
            pass
        return {}

    def _count_processes(self, name: str) -> int:
        """Count processes matching a name."""
        count = 0
        for proc in psutil.process_iter(["name"]):
            try:
                if name.lower() in proc.info["name"].lower():
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return count

    def _count_mcp_processes(self) -> int:
        """Count active MCP-related processes."""
        count = 0
        mcp_keywords = ["mcp", "python", "node"]
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if any(kw in cmdline.lower() for kw in mcp_keywords):
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return count

    async def cleanup_zombie_processes(self) -> dict:
        """Find and terminate zombie processes."""
        zombies = []
        for proc in psutil.process_iter(["pid", "name", "status"]):
            try:
                if proc.info["status"] == "zombie":
                    proc.kill()
                    zombies.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if zombies:
            logger.info("zombies_cleaned", count=len(zombies), pids=zombies)
        return {"cleaned": len(zombies), "pids": zombies}

    async def check_resource_limits(self) -> dict:
        """Check if any resource limits are exceeded."""
        metrics = await self.get_current_metrics()
        warnings = []

        if metrics["cpu_percent"] > settings.MAX_CPU_PERCENT:
            warnings.append(f"CPU usage {metrics['cpu_percent']}% exceeds limit {settings.MAX_CPU_PERCENT}%")

        if metrics["ram_percent"] > settings.MAX_RAM_PERCENT:
            warnings.append(f"RAM usage {metrics['ram_percent']}% exceeds limit {settings.MAX_RAM_PERCENT}%")

        return {
            "safe": len(warnings) == 0,
            "warnings": warnings,
            "metrics": metrics,
        }

    async def start_monitoring(self, interval: int = 5):
        """Start background metrics monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("monitoring_started", interval=interval)

    def stop_monitoring(self):
        """Stop background metrics monitoring."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        logger.info("monitoring_stopped")

    async def _monitor_loop(self, interval: int):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                await self.get_current_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("monitor_loop_error", error=str(e))
                await asyncio.sleep(interval)


# Global runtime service instance
runtime_service = RuntimeService()
