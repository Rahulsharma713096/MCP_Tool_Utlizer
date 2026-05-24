"""Unified structured logging system for the AI Workspace Platform."""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import structlog
from loguru import logger as loguru_logger

from config.settings import settings


class LogManager:
    """Enterprise log manager with structured logging and rotation."""

    def __init__(self):
        self.log_dir = Path(settings.LOG_DIR)
        self._setup_directories()
        self._configure_structlog()
        self._configure_loguru()

    def _setup_directories(self):
        """Create log directory structure."""
        log_dirs = [
            self.log_dir / "backend",
            self.log_dir / "frontend",
            self.log_dir / "runtime",
            self.log_dir / "mcp",
            self.log_dir / "security",
            self.log_dir / "api",
            self.log_dir / "system",
        ]
        for d in log_dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _configure_structlog(self):
        """Configure structlog for structured logging."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _configure_loguru(self):
        """Configure loguru for file-based logging with rotation."""
        # Remove default handler
        loguru_logger.remove()

        # Console handler
        loguru_logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG" if settings.DEBUG else "INFO",
            colorize=True,
        )

        # App log
        loguru_logger.add(
            str(self.log_dir / "backend" / "app.log"),
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            format="{time} | {level} | {name}:{function}:{line} | {message}",
            level="INFO",
        )

        # Runtime log
        loguru_logger.add(
            str(self.log_dir / "runtime" / "runtime.log"),
            rotation="10 MB",
            retention="7 days",
            format="{time} | {level} | {message}",
            level="INFO",
        )

        # MCP log
        loguru_logger.add(
            str(self.log_dir / "mcp" / "mcp.log"),
            rotation="5 MB",
            retention="7 days",
            format="{time} | {level} | {message}",
            level="INFO",
        )

        # Security log
        loguru_logger.add(
            str(self.log_dir / "security" / "security.log"),
            rotation="10 MB",
            retention="90 days",
            format="{time} | {level} | {message}",
            level="WARNING",
        )

        # API log
        loguru_logger.add(
            str(self.log_dir / "api" / "api.log"),
            rotation="10 MB",
            retention="14 days",
            format="{time} | {level} | {message}",
            level="INFO",
        )

        # Crash log
        loguru_logger.add(
            str(self.log_dir / "system" / "crash.log"),
            rotation="50 MB",
            retention="365 days",
            format="{time} | {level} | {message}",
            level="ERROR",
        )

    def get_logger(self, module: str = "app"):
        """Get a structured logger for a specific module."""
        try:
            return structlog.get_logger(module)
        except Exception:
            # Fallback: return loguru logger directly
            return loguru_logger.bind(module=module)

    def log_event(self, event: str, level: str = "info", **kwargs):
        """Log a structured event."""
        log_method = getattr(loguru_logger, level.lower(), loguru_logger.info)
        extra = {k: v for k, v in kwargs.items() if not k.startswith("_")}
        log_method(f"{event} | {json.dumps(extra) if extra else ''}")

    def log_security_event(self, event: str, user: Optional[str] = None, **kwargs):
        """Log a security-related event."""
        extra = {"user": user, **kwargs}
        loguru_logger.warning(f"SECURITY: {event} | {json.dumps(extra)}")

    def log_runtime_event(self, event: str, model: Optional[str] = None, pid: Optional[int] = None, **kwargs):
        """Log a runtime event (model start/stop)."""
        extra = {"model": model, "pid": pid, **kwargs}
        loguru_logger.info(f"RUNTIME: {event} | {json.dumps(extra)}")

    def log_mcp_event(self, event: str, mcp_name: Optional[str] = None, **kwargs):
        """Log an MCP event."""
        extra = {"mcp": mcp_name, **kwargs}
        loguru_logger.info(f"MCP: {event} | {json.dumps(extra)}")


# Global log manager instance
log_manager = LogManager()
logger = log_manager.get_logger()


def get_logger(module: str = "app"):
    """Get a safe logger for any module."""
    return log_manager.get_logger(module)
