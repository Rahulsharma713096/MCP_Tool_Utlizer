"""Sanity Tests - Covers SAN test cases from test.txt.
Minimal verification after build deployment."""

import pytest
import sys
import os
from pathlib import Path


class TestAppSanity:
    """SAN-001 to SAN-010: Core sanity verification"""

    def test_app_launches(self):
        """SAN-001: App launches - Verify main app module can be imported"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        try:
            from main import app
            assert app is not None
            assert app.title == "AI Workspace"
        except ImportError as e:
            pytest.fail(f"App import failed: {e}")

    def test_app_title(self):
        """SAN-001: App has correct title"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from main import app
        assert app.title == "AI Workspace"

    def test_app_version(self):
        """SAN-001: App has version"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from main import app
        assert app.version == "1.0.0"

    def test_api_router_exists(self):
        """SAN-003: Dashboard/API routes load"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from main import app
        routes = [r.path for r in app.routes]
        assert "/api/v1/health" in routes
        assert "/api/v1/system/info" in routes
        assert "/api/v1/system/metrics" in routes

    def test_ollama_service_exists(self):
        """SAN-004: Ollama detection works"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from services.ollama_service import OllamaService
        service = OllamaService()
        assert service is not None
        assert service.ollama_host == "http://localhost:11434"

    def test_chat_service_exists(self):
        """SAN-005: Chat sends message"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from services.chat_service import ChatService
        service = ChatService()
        assert service is not None
        session_id = service.create_session()
        assert session_id is not None

    def test_mcp_service_exists(self):
        """SAN-006: MCP list loads"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from services.mcp_service import MCPService
        service = MCPService()
        assert service is not None

    def test_provider_service_exists(self):
        """SAN-007: Provider config opens"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from services.provider_service import ProviderService
        service = ProviderService()
        assert service is not None

    def test_runtime_service_exists(self):
        """SAN-008: Runtime monitor loads"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from services.runtime_service import RuntimeService
        service = RuntimeService()
        assert service is not None

    def test_logging_exists(self):
        """SAN-009: Logs page accessible"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from core.logging import LogManager, log_manager
        assert log_manager is not None
        assert hasattr(log_manager, 'log_event')

    def test_security_module_exists(self):
        """SAN-010: Security module loads"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from core.security import (
            create_access_token,
            verify_token,
            hash_password,
            encrypt_api_key,
        )
        assert create_access_token is not None
        assert verify_token is not None
        assert hash_password is not None
        assert encrypt_api_key is not None

    def test_config_loaded(self):
        """Config files exist and are valid"""
        config_dir = Path(__file__).parents[2] / "configs"
        assert (config_dir / "providers.json").exists()
        assert (config_dir / "runtime.json").exists()
        assert (config_dir / "ui.json").exists()
        assert (config_dir / "mcp_registry.json").exists()

    def test_run_scripts_exist(self):
        """Deployment scripts exist"""
        root_dir = Path(__file__).parents[2]
        assert (root_dir / "run.bat").exists() or (root_dir / "run.sh").exists()

    def test_database_schema(self):
        """Database schema is defined"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
        from models.database import Model, MCP, Provider, Chat, Session, Log, Metric
        assert Model is not None
        assert MCP is not None
        assert Provider is not None
        assert Chat is not None
        assert Metric is not None
