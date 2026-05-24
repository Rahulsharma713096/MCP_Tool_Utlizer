"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ============== Model Schemas ==============

class ModelBase(BaseModel):
    name: str
    provider: str = "ollama"
    size: Optional[str] = None
    quantization: Optional[str] = None


class ModelCreate(ModelBase):
    pass


class ModelResponse(ModelBase):
    id: int
    active: bool = False
    runtime_pid: Optional[int] = None
    cpu_usage: float = 0.0
    ram_usage: float = 0.0
    vram_usage: Optional[float] = None
    tokens_per_second: Optional[float] = None
    last_active: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelStartRequest(BaseModel):
    name: str
    provider: str = "ollama"


class ModelStopRequest(BaseModel):
    name: str


# ============== MCP Schemas ==============

class MCPBase(BaseModel):
    name: str
    type: str
    transport: str = "stdio"
    endpoint: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list[str]] = None
    auth_type: Optional[str] = None
    capabilities: Optional[list[str]] = None
    config: Optional[dict[str, Any]] = None


class MCPCreate(MCPBase):
    pass


class MCPUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    transport: Optional[str] = None
    endpoint: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list[str]] = None
    config: Optional[dict[str, Any]] = None


class MCPResponse(MCPBase):
    id: int
    enabled: bool = True
    status: str = "inactive"
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============== Provider Schemas ==============

class ProviderBase(BaseModel):
    name: str
    base_url: str
    api_key: Optional[str] = None
    models: Optional[list[str]] = None
    selected_model: Optional[str] = None


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[list[str]] = None
    selected_model: Optional[str] = None


class ProviderResponse(BaseModel):
    id: int
    name: str
    enabled: bool
    base_url: str
    models: Optional[list[str]] = None
    selected_model: Optional[str] = None
    latency_ms: Optional[float] = None
    status: str = "inactive"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============== Chat Schemas ==============

class ChatMessage(BaseModel):
    session_id: str
    role: str = "user"
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None


class ChatResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class ChatStreamEvent(BaseModel):
    type: str  # token, tool_call, done, error
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict[str, Any]] = None
    tool_result: Optional[str] = None
    error: Optional[str] = None


# ============== Runtime Schemas ==============

class RuntimeMetrics(BaseModel):
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    gpu_percent: Optional[float] = None
    vram_used_gb: Optional[float] = None
    active_models: int = 0
    active_mcps: int = 0
    token_throughput: Optional[float] = None


class SystemInfo(BaseModel):
    python_version: str
    node_version: Optional[str] = None
    ollama_installed: bool
    ollama_version: Optional[str] = None
    gpu_available: bool
    gpu_name: Optional[str] = None
    total_ram_gb: float
    available_ram_gb: float
    total_disk_gb: float
    free_disk_gb: float


# ============== Health Schemas ==============

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    ollama: bool = False
    database: bool = False
    active_mcps: int = 0
    active_providers: int = 0
    uptime_seconds: float = 0.0


# ============== Config Schemas ==============

class UISettings(BaseModel):
    theme: str = "neon"
    sidebar_collapsed: bool = False
    font_size: int = 14
    show_metrics: bool = True


class RuntimeConfig(BaseModel):
    model_idle_timeout_minutes: int = 10
    max_cpu_percent: float = 90.0
    max_ram_percent: float = 85.0
    auto_unload_idle: bool = True
    enable_gpu_monitoring: bool = True


# ============== Auth Schemas ==============

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


class LoginRequest(BaseModel):
    username: str
    password: str
