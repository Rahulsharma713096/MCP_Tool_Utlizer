"""Database models for AI Workspace Platform."""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import json
import os

from config.settings import settings

Base = declarative_base()

# Async engine for production use
async_engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

# Sync engine for scripts
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+aiosqlite", ""),
    echo=settings.DEBUG
)
SyncSessionLocal = sessionmaker(bind=sync_engine)


class Model(Base):
    """Tracks AI models and their runtime state."""
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    provider = Column(String(100), default="ollama")
    size = Column(String(50), nullable=True)
    quantization = Column(String(50), nullable=True)
    active = Column(Boolean, default=False)
    runtime_pid = Column(Integer, nullable=True)
    cpu_usage = Column(Float, default=0.0)
    ram_usage = Column(Float, default=0.0)
    vram_usage = Column(Float, nullable=True)
    tokens_per_second = Column(Float, nullable=True)
    last_active = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class MCP(Base):
    """MCP (Model Context Protocol) server registry."""
    __tablename__ = "mcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    transport = Column(String(50), default="stdio")  # stdio, sse, http
    endpoint = Column(String(500), nullable=True)
    command = Column(String(500), nullable=True)
    args = Column(JSON, nullable=True)
    auth_type = Column(String(50), nullable=True)
    capabilities = Column(JSON, nullable=True)
    status = Column(String(50), default="inactive")  # active, inactive, error
    error_message = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Provider(Base):
    """Online AI provider configuration."""
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    models = Column(JSON, nullable=True)  # List of available models
    selected_model = Column(String(255), nullable=True)
    latency_ms = Column(Float, nullable=True)
    status = Column(String(50), default="inactive")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Chat(Base):
    """Chat session storage."""
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    model = Column(String(255), nullable=True)
    provider = Column(String(100), nullable=True)
    tool_calls = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    extra_metadata = Column(JSON, nullable=True)


class Session(Base):
    """User session management."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    active_provider = Column(String(100), nullable=True)
    active_model = Column(String(255), nullable=True)
    theme = Column(String(50), default="neon")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Log(Base):
    """Structured logging storage."""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)
    logger = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(100), nullable=True)
    pid = Column(Integer, nullable=True)
    log_metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Metric(Base):
    """Runtime metrics storage."""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    cpu_percent = Column(Float, default=0.0)
    ram_percent = Column(Float, default=0.0)
    ram_used_gb = Column(Float, default=0.0)
    gpu_percent = Column(Float, nullable=True)
    vram_used_gb = Column(Float, nullable=True)
    active_models = Column(Integer, default=0)
    active_mcps = Column(Integer, default=0)
    token_throughput = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


async def init_db():
    """Initialize database and create all tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_sync_db():
    """Initialize database synchronously (for scripts)."""
    Base.metadata.create_all(bind=sync_engine)
