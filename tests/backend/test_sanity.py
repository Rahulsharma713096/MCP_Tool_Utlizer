"""Comprehensive Sanity Check - validates ALL modules load, import, and initialize correctly.

This is the first line of defense against broken imports, missing dependencies,
circular imports, and initialization errors.

Tests cover:
- All service modules import without errors
- All API route modules import correctly
- All database models import correctly
- All config modules load correctly
- All core utilities import without errors
- All schemas import and validate
- Critical singletons initialize without errors
- No circular import dependencies
"""

import pytest
import sys
import os

# Add backend source to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'ai-workspace', 'apps', 'backend')


# ──────────────────────────────────────────────
# Import Health Checks
# ──────────────────────────────────────────────

class TestModuleImports:
    """Verify all modules import without errors."""

    def test_config_settings_imports(self):
        """Config settings module loads."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from config.settings import settings
        assert settings is not None
        assert hasattr(settings, "APP_NAME")
        assert hasattr(settings, "APP_VERSION")
        assert hasattr(settings, "DEBUG")
        assert hasattr(settings, "ENV")

    def test_core_logging_imports(self):
        """Core logging module loads."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from core.logging import log_manager
        assert log_manager is not None

    def test_core_security_imports(self):
        """Core security module loads and exposes key functions."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from core.security import (
            create_access_token,
            decode_access_token,
            verify_token,
            hash_password,
            verify_password,
            encrypt_api_key,
            decrypt_api_key,
            sanitize_command,
            validate_path,
            get_client_ip,
        )
        assert callable(create_access_token)
        assert callable(verify_token)
        assert callable(encrypt_api_key)
        assert callable(sanitize_command)

    def test_models_database_imports(self):
        """Database models load without errors."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from models.database import Model, MCP, Provider, Chat, Session, Log, Metric
        assert Model is not None
        assert MCP is not None
        assert Provider is not None
        assert Chat is not None

    def test_models_schemas_imports(self):
        """Pydantic schemas load without errors."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from models.schemas import (
            MCPCreate, MCPResponse, MCPUpdate,
            ProviderCreate, ProviderResponse,
            ChatMessage, ChatResponse,
            HealthResponse, RuntimeMetrics, SystemInfo,
            UISettings, RuntimeConfig,
            TokenResponse, LoginRequest,
            ModelStartRequest, ModelStopRequest,
        )
        assert MCPCreate is not None
        assert ProviderCreate is not None
        assert ChatMessage is not None
        assert HealthResponse is not None

    def test_services_all_import(self):
        """All service modules import without circular dependencies."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.ollama_service import OllamaService
        from services.mcp_service import MCPService
        from services.chat_service import ChatService
        from services.provider_service import (
            ProviderService, ProviderFactory,
            OpenAIProvider, OpenRouterProvider, GeminiProvider,
        )
        from services.runtime_service import RuntimeService

        assert OllamaService is not None
        assert MCPService is not None
        assert ChatService is not None
        assert ProviderService is not None
        assert RuntimeService is not None

    def test_api_routes_imports(self):
        """API routes module loads without errors."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from api.routes import router
        assert router is not None
        assert len(router.routes) > 0

    def test_main_app_imports(self):
        """Main FastAPI app module loads."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from main import app
        assert app is not None
        assert app.title == "AI Workspace Platform"


# ──────────────────────────────────────────────
# Singleton Initialization
# ──────────────────────────────────────────────

class TestSingletonInit:
    """Verify critical singletons initialize without errors."""

    def test_provider_service_singleton(self):
        """ProviderService global singleton initializes."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.provider_service import provider_service
        assert provider_service is not None
        assert hasattr(provider_service, "instances")
        assert hasattr(provider_service, "get_provider")

    def test_chat_service_singleton(self):
        """ChatService global singleton initializes."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.chat_service import chat_service
        assert chat_service is not None
        assert hasattr(chat_service, "sessions")

    def test_runtime_service_singleton(self):
        """RuntimeService global singleton initializes."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.runtime_service import runtime_service
        assert runtime_service is not None
        assert hasattr(runtime_service, "get_system_info")


# ──────────────────────────────────────────────
# Service Instantiation
# ──────────────────────────────────────────────

class TestServiceInstantiation:
    """Verify service classes can be instantiated."""

    def test_ollama_service_instantiation(self):
        """OllamaService can be instantiated."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.ollama_service import OllamaService
        svc = OllamaService()
        assert svc.ollama_host is not None
        assert svc.running_processes == {}

    def test_mcp_service_instantiation(self):
        """MCPService can be instantiated."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.mcp_service import MCPService
        svc = MCPService()
        assert svc.running_mcps == {}
        assert svc._mcp_info == {}
        assert svc._tool_cache == {}

    def test_chat_service_instantiation(self):
        """ChatService can be instantiated."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.chat_service import ChatService
        svc = ChatService()
        assert svc.sessions == {}
        assert svc.ollama_service is not None

    def test_provider_service_instantiation(self):
        """ProviderService can be instantiated."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.provider_service import ProviderService
        svc = ProviderService()
        assert svc.instances == {}

    def test_runtime_service_instantiation(self):
        """RuntimeService can be instantiated."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from services.runtime_service import RuntimeService
        svc = RuntimeService()
        assert svc._metrics_history == []


# ──────────────────────────────────────────────
# Schema Validation
# ──────────────────────────────────────────────

class TestSchemaValidation:
    """Verify Pydantic schemas validate correctly."""

    def test_mcp_create_valid(self):
        """MCPCreate validates correct data."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from models.schemas import MCPCreate

        mcp = MCPCreate(name="test", type="custom", command="python", args=["-m", "server"])
        assert mcp.name == "test"
        assert mcp.type == "custom"
        assert mcp.transport == "stdio"  # default

    def test_mcp_create_invalid_empty_name(self):
        """MCPCreate rejects empty name."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from models.schemas import MCPCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MCPCreate(name="", type="custom")

    def test_health_response_defaults(self):
        """HealthResponse has sensible defaults."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from models.schemas import HealthResponse

        health = HealthResponse()
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert health.ollama is False
        assert health.active_mcps == 0

    def test_ui_settings_defaults(self):
        """UISettings has sensible defaults."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from models.schemas import UISettings

        ui = UISettings()
        assert ui.theme == "neon"
        assert ui.sidebar_collapsed is False
        assert ui.font_size == 14

    def test_runtime_config_defaults(self):
        """RuntimeConfig has sensible defaults."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))
        from models.schemas import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.model_idle_timeout_minutes == 10
        assert cfg.max_cpu_percent == 90.0
        assert cfg.max_ram_percent == 85.0


# ──────────────────────────────────────────────
# No Circular Imports
# ──────────────────────────────────────────────

class TestNoCircularImports:
    """Verify there are no circular import dependencies."""

    def test_services_dont_import_each_other_circularly(self):
        """Services can be imported without causing circular imports."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))

        # Each service should be importable independently
        import importlib

        modules = [
            "services.ollama_service",
            "services.mcp_service",
            "services.provider_service",
            "services.chat_service",
            "services.runtime_service",
        ]

        for mod_name in modules:
            # Clear the module cache for this specific test
            for key in list(sys.modules.keys()):
                if key.startswith("services.") or key.startswith("api.") or key.startswith("models.") or key.startswith("core.") or key == "main" or key == "config.settings":
                    del sys.modules[key]

            # Now try importing
            mod = importlib.import_module(mod_name)
            assert mod is not None

    def test_api_routes_no_circular(self):
        """API routes module can be imported without circular imports."""
        sys.path.insert(0, os.path.abspath(BACKEND_DIR))

        for key in list(sys.modules.keys()):
            if key.startswith("services.") or key.startswith("api.") or key.startswith("models.") or key.startswith("core.") or key == "main" or key == "config.settings":
                del sys.modules[key]

        from api.routes import router
        assert router is not None
