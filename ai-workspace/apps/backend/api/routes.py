"""API Routes - All REST endpoints for the AI Workspace Platform."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json

from models.schemas import (
    ModelStartRequest, ModelStopRequest, ModelResponse,
    MCPCreate, MCPUpdate, MCPResponse,
    ProviderCreate, ProviderUpdate, ProviderResponse,
    ChatMessage, ChatResponse, HealthResponse,
    RuntimeMetrics, SystemInfo,
    UISettings, RuntimeConfig, LoginRequest, TokenResponse,
)
from services.ollama_service import OllamaService
from services.mcp_service import MCPService
from services.provider_service import ProviderService, provider_service, ProviderFactory
from services.chat_service import chat_service
from services.runtime_service import runtime_service
from core.security import create_access_token
from core.logging import log_manager

router = APIRouter()
logger = log_manager.get_logger("api")

# Instantiate services
ollama_service = OllamaService()
mcp_service = MCPService()

# Wire MCP service into chat service for tool integration
chat_service.mcp_service = mcp_service

# ============== Health & System ==============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint."""
    ollama_status = await ollama_service.health_check()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        ollama=ollama_status.get("status") == "healthy",
        database=True,
        active_mcps=len(mcp_service.running_mcps),
        active_providers=len(provider_service.instances),
        uptime_seconds=0.0,
    )


@router.get("/health/runtime")
async def runtime_health():
    """Runtime health check."""
    return await runtime_service.get_current_metrics()


@router.get("/health/mcp")
async def mcp_health():
    """MCP subsystem health."""
    return {
        "active_mcps": len(mcp_service.running_mcps),
        "status": "healthy",
    }


@router.get("/health/providers")
async def provider_health():
    """Provider subsystem health."""
    return {
        "active_providers": len(provider_service.instances),
        "status": "healthy",
    }


@router.get("/system/info")
async def system_info():
    """Get system information."""
    return await runtime_service.get_system_info()


@router.get("/system/metrics")
async def system_metrics():
    """Get current system metrics."""
    return await runtime_service.get_current_metrics()


@router.get("/system/metrics/history")
async def metrics_history(minutes: int = Query(5, ge=1, le=60)):
    """Get metrics history."""
    return await runtime_service.get_metrics_history(minutes)


# ============== Ollama Models ==============

@router.get("/ollama/detect")
async def detect_ollama():
    """Detect Ollama installation."""
    detected = await ollama_service.detect_ollama()
    version = await ollama_service.get_ollama_version() if detected else None
    return {"installed": detected, "version": version}


@router.get("/ollama/models")
async def list_models():
    """List installed Ollama models."""
    models = await ollama_service.list_models()
    return {"models": models, "count": len(models)}


@router.post("/ollama/models/start")
async def start_model(request: ModelStartRequest):
    """Start a model runtime."""
    result = await ollama_service.start_model(request.name)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/ollama/models/stop")
async def stop_model(request: ModelStopRequest):
    """Stop a model runtime."""
    return await ollama_service.stop_model(request.name)


@router.get("/ollama/models/{model_name}/runtime")
async def model_runtime_info(model_name: str):
    """Get runtime info for a specific model."""
    return await ollama_service.get_model_runtime_info(model_name)


@router.post("/ollama/kill-all")
async def kill_all_processes():
    """Kill all running Ollama processes."""
    return await ollama_service.kill_all_processes()


# ============== MCP Management ==============

@router.post("/mcps", response_model=dict)
async def register_mcp(mcp: MCPCreate):
    """Register a new MCP server."""
    result = await mcp_service.register_mcp(mcp.model_dump())
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.delete("/mcps/{mcp_id}")
async def delete_mcp(mcp_id: int):
    """Delete an MCP server."""
    return await mcp_service.delete_mcp(mcp_id)


@router.post("/mcps/{mcp_id}/enable")
async def enable_mcp(mcp_id: int, config: MCPCreate):
    """Enable an MCP server.
    Accepts the full MCP configuration (command, args, transport) to start the process.
    """
    from models.database import MCP
    mcp = MCP(
        id=mcp_id,
        name=config.name,
        command=config.command or "",
        args=config.args,
        transport=config.transport,
        type=config.type,
        endpoint=config.endpoint,
        enabled=True,
    )
    return await mcp_service.enable_mcp(mcp)


@router.post("/mcps/{mcp_id}/disable")
async def disable_mcp(mcp_id: int):
    """Disable an MCP server."""
    return await mcp_service.stop_mcp(mcp_id)


@router.get("/mcps/{mcp_id}/status")
async def mcp_status(mcp_id: int):
    """Get detailed MCP server status including lifecycle state."""
    is_running = mcp_id in mcp_service.running_mcps
    info = mcp_service._mcp_info.get(mcp_id, {})
    lifecycle = mcp_service._mcp_lifecycle.get(mcp_id, "inactive")
    tool_count = len(mcp_service._tool_cache.get(mcp_id, []))
    process = mcp_service.running_mcps.get(mcp_id)
    return {
        "id": mcp_id,
        "running": is_running,
        "lifecycle": lifecycle,
        "tool_count": tool_count,
        "pid": process.pid if process and process.returncode is None else None,
        "info": info,
    }


@router.get("/mcps/{mcp_id}/test")
async def test_mcp(mcp_id: int):
    """Test MCP connectivity."""
    from models.database import MCP
    info = mcp_service._mcp_info.get(mcp_id, {})
    mcp = MCP(
        id=mcp_id,
        name=info.get("name", f"mcp-{mcp_id}"),
        command=info.get("command", ""),
        args=[],
        transport=info.get("transport", "stdio"),
        type=info.get("type", "custom"),
        endpoint=info.get("endpoint"),
    )
    return await mcp_service.test_mcp(mcp)


@router.get("/mcps/{mcp_id}/logs")
async def mcp_logs(mcp_id: int, lines: int = Query(50, ge=10, le=500)):
    """Get MCP server logs."""
    return {"logs": await mcp_service.get_mcp_logs(mcp_id, lines)}


@router.get("/mcps/config")
async def get_mcp_config():
    """Get MCP configurations from registry file."""
    import json, os
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "configs", "mcp_registry.json")
    try:
        with open(config_path) as f:
            data = json.load(f)
        return data
    except Exception:
        return {"mcps": []}


@router.post("/mcps/validate")
async def validate_mcp(config: dict):
    """Validate an MCP configuration before enabling."""
    return await mcp_service.validate_mcp_config(config)


@router.get("/mcps/prerequisites")
async def mcp_prerequisites():
    """Check system prerequisites for running MCP servers."""
    return await mcp_service.check_prerequisites()


# ============== Provider Management ==============

@router.post("/providers", response_model=dict)
async def add_provider(provider: ProviderCreate):
    """Add or update an AI provider.
    The API key is stored in the provider instance in memory (not persisted to disk).
    If the provider already exists, its config (URL, API key) is updated.
    The API key is only overwritten if a non-empty value is provided.
    """
    existing = provider_service._find_instance(provider.name)
    if existing:
        # Update existing provider config
        existing.base_url = provider.base_url.rstrip("/")
        # Only overwrite API key if a new one was actually provided
        if provider.api_key:
            existing.api_key = provider.api_key
            existing._setup_auth()
        log_manager.log_event("provider_updated", level="info", provider=provider.name)
        return {"status": "updated", "name": provider.name}
    provider_service.get_provider(
        provider_type=provider.name.lower(),
        name=provider.name,
        base_url=provider.base_url,
        api_key=provider.api_key,
    )
    log_manager.log_event("provider_added", level="info", provider=provider.name)
    return {"status": "added", "name": provider.name}


@router.delete("/providers/{provider_name}")
async def delete_provider(provider_name: str):
    """Delete an AI provider."""
    provider_service.remove_provider(provider_name)
    return {"status": "deleted", "name": provider_name}


@router.post("/providers/test")
async def test_provider(provider: ProviderCreate):
    """Test a provider connection. Uses stored API key if available."""
    # Look up existing provider instance to get the API key
    existing = provider_service._find_instance(provider.name)
    api_key = provider.api_key or (existing.api_key if existing else "")
    return await provider_service.test_connection(
        provider_type=provider.name.lower(),
        base_url=provider.base_url,
        api_key=api_key,
    )


@router.get("/providers/config")
async def get_providers_config():
    """Get provider configurations from config file (includes models)."""
    import json, os
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "configs", "providers.json")
    try:
        with open(config_path) as f:
            data = json.load(f)
        return data
    except Exception:
        return {"providers": []}


@router.get("/providers")
async def list_providers():
    """List all configured providers."""
    return {
        "providers": [
            {
                "name": name,
                "active": hasattr(inst, "api_key") and bool(inst.api_key),
            }
            for name, inst in provider_service.instances.items()
        ]
    }


@router.get("/providers/{provider_name}/models")
async def list_provider_models(provider_name: str):
    """List available models for a provider."""
    inst = provider_service._find_instance(provider_name)
    if not inst:
        raise HTTPException(status_code=404, detail="Provider not found")
    models = await inst.list_models()
    return {"provider": provider_name, "models": models}


@router.post("/providers/fetch-models")
async def fetch_provider_models(body: ProviderCreate):
    """Fetch available models from a provider using its API."""
    return await provider_service.fetch_models(
        provider_type=body.name.lower(),
        base_url=body.base_url,
        api_key=body.api_key or "",
    )


@router.post("/providers/test-chat")
async def test_provider_chat(provider: ProviderCreate):
    """Test a provider with a sample chat message.
    Validates the provider, API key, builds a sample request, and returns the response.
    """
    # Validate provider
    if not provider.name:
        raise HTTPException(status_code=400, detail="Provider name is required")
    if not provider.base_url:
        raise HTTPException(status_code=400, detail="Base URL is required")

    # Get API key from request or stored instance
    existing = provider_service._find_instance(provider.name)
    api_key = provider.api_key or (existing.api_key if existing else "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required for test chat")

    # Create a temporary provider instance for the test
    test_prov = ProviderFactory.create(provider.name.lower(), provider.name, provider.base_url, api_key)

    # Send a simple chat request
    try:
        test_messages = [{"role": "user", "content": "Say hello in one sentence."}]
        result = await test_prov.chat(model=provider.selected_model or "openai/gpt-4o-mini", messages=test_messages)
        # Parse OpenAI-style response
        content = ""
        if "choices" in result and result["choices"]:
            content = result["choices"][0].get("message", {}).get("content", "")
        elif "error" in result:
            raise HTTPException(status_code=502, detail=f"Provider error: {result['error'].get('message', str(result['error']))}")
        else:
            content = str(result)
        return {"success": True, "response": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_chat_error", provider=provider.name, error=str(e))
        raise HTTPException(status_code=502, detail=f"Chat test failed: {str(e)}")


@router.post("/providers/validate")
async def validate_provider(provider: ProviderCreate):
    """Validate provider configuration (API key, URL, connectivity)."""
    if not provider.base_url:
        return {"valid": False, "errors": ["Base URL is required"]}
    if not provider.base_url.startswith(("http://", "https://")):
        return {"valid": False, "errors": ["Base URL must start with http:// or https://"]}
    result = await provider_service.test_connection(
        provider_type=provider.name.lower(),
        base_url=provider.base_url,
        api_key=provider.api_key or "",
    )
    return {
        "valid": result.get("status") == "healthy",
        "status": result.get("status"),
        "latency_ms": result.get("latency_ms"),
        "message": result.get("message"),
    }


# ============== Chat ==============

@router.post("/chat/session")
async def create_chat_session():
    """Create a new chat session."""
    session_id = chat_service.create_session()
    return {"session_id": session_id}


@router.post("/chat/send")
async def send_chat_message(message: ChatMessage):
    """Send a chat message and get response."""
    result = await chat_service.send_message(
        session_id=message.session_id,
        content=message.content,
        provider=message.provider or "ollama",
        model=message.model,
    )
    return result


@router.get("/chat/history/{session_id}")
async def chat_history(session_id: str):
    """Get chat session history."""
    messages = chat_service.get_session_history(session_id)
    return {"session_id": session_id, "messages": messages}


@router.delete("/chat/session/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    chat_service.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()
    session_id = chat_service.create_session()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            async for event in chat_service.stream_message(
                session_id=session_id,
                content=message.get("content", ""),
                provider=message.get("provider", "ollama"),
                model=message.get("model"),
            ):
                await websocket.send_text(event)

    except WebSocketDisconnect:
        logger.info("websocket_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))


# ============== Runtime & Resources ==============

@router.post("/runtime/cleanup")
async def cleanup_processes():
    """Clean up zombie processes."""
    return await runtime_service.cleanup_zombie_processes()


@router.get("/runtime/resource-check")
async def resource_check():
    """Check resource limits."""
    return await runtime_service.check_resource_limits()


@router.post("/runtime/monitoring/start")
async def start_monitoring(interval: int = Query(5, ge=1)):
    """Start background monitoring."""
    await runtime_service.start_monitoring(interval)
    return {"status": "started", "interval": interval}


@router.post("/runtime/monitoring/stop")
async def stop_monitoring():
    """Stop background monitoring."""
    runtime_service.stop_monitoring()
    return {"status": "stopped"}


# ============== Config ==============

@router.get("/config/ui")
async def get_ui_config():
    """Get UI configuration."""
    return UISettings()


@router.post("/config/ui")
async def update_ui_config(config: UISettings):
    """Update UI configuration."""
    return config


@router.get("/config/runtime")
async def get_runtime_config():
    """Get runtime configuration."""
    return RuntimeConfig()


@router.post("/config/runtime")
async def update_runtime_config(config: RuntimeConfig):
    """Update runtime configuration."""
    return config


# ============== Auth ==============

@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """Authenticate and get access token."""
    # In production, validate against database
    token = create_access_token({"sub": credentials.username})
    return TokenResponse(access_token=token)


@router.post("/auth/verify")
async def verify_token(token: str):
    """Verify an access token."""
    from core.security import verify_token as verify
    return {"valid": verify(token)}
