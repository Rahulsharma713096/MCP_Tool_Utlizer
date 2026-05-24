"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    # App
    APP_NAME: str = "AI Workspace"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENV: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ai_workspace.db"

    # Security
    SECRET_KEY: str = "change-this-to-a-secure-random-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    ENCRYPTION_KEY: Optional[str] = None

    # Ollama
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 300

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "..", "..", "configs")
    LOG_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "..", "..", "logs")
    MCP_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "..", "..", "mcps")
    DATA_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "..", "..", "data")

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate Limiting
    RATE_LIMIT: str = "100/minute"

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # Resource Limits
    MAX_CPU_PERCENT: float = 90.0
    MAX_RAM_PERCENT: float = 85.0
    MODEL_IDLE_TIMEOUT_MINUTES: int = 10

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()

# Ensure required directories exist
for dir_path in [settings.CONFIG_DIR, settings.LOG_DIR, settings.MCP_DIR, settings.DATA_DIR]:
    os.makedirs(dir_path, exist_ok=True)
