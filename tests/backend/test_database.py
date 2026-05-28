"""Unit tests for database models and schema.

Tests cover:
- Model fields and defaults
- MCP model fields and serialization
- Provider model fields and API key encryption
- Chat/Session/Log/Metric models
- Table name conventions
- DateTime default values
"""

import pytest
from datetime import datetime, timezone


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def db_models():
    """Import database models module."""
    from models.database import (
        Model, MCP, Provider, Chat, Session, Log, Metric,
        Base, init_sync_db,
    )
    return {
        "Model": Model,
        "MCP": MCP,
        "Provider": Provider,
        "Chat": Chat,
        "Session": Session,
        "Log": Log,
        "Metric": Metric,
        "Base": Base,
    }


# ──────────────────────────────────────────────
# Model Fields & Defaults
# ──────────────────────────────────────────────

class TestModelModel:
    """Test the AI Model database model."""

    def test_table_name(self, db_models):
        """Model table name is 'models'."""
        assert db_models["Model"].__tablename__ == "models"

    def test_has_required_fields(self, db_models):
        """Model has all required fields defined."""
        cols = db_models["Model"].__table__.columns
        assert "id" in cols
        assert "name" in cols
        assert "provider" in cols
        assert "active" in cols
        assert "created_at" in cols

    def test_name_unique_constraint(self, db_models):
        """Model name has unique constraint."""
        name_col = db_models["Model"].__table__.columns["name"]
        assert name_col.unique is True

    def test_defaults(self, db_models):
        """Model has correct default values."""
        cols = db_models["Model"].__table__.columns
        assert cols["active"].default.arg is False
        assert cols["provider"].default.arg == "ollama"
        assert cols["cpu_usage"].default.arg == 0.0
        assert cols["ram_usage"].default.arg == 0.0


# ──────────────────────────────────────────────
# MCP Model
# ──────────────────────────────────────────────

class TestMCPModel:
    """Test the MCP server database model."""

    def test_table_name(self, db_models):
        """MCP table name is 'mcps'."""
        assert db_models["MCP"].__tablename__ == "mcps"

    def test_has_all_fields(self, db_models):
        """MCP has all required and optional fields."""
        cols = db_models["MCP"].__table__.columns
        required_fields = ["id", "name", "type", "transport"]
        optional_fields = ["endpoint", "command", "args", "github_repo",
                          "github_ref", "root", "exclude", "status"]
        for field in required_fields + optional_fields:
            assert field in cols, f"Missing field: {field}"

    def test_default_transport(self, db_models):
        """MCP transport defaults to 'stdio'."""
        cols = db_models["MCP"].__table__.columns
        assert cols["transport"].default.arg == "stdio"

    def test_default_status(self, db_models):
        """MCP status defaults to 'inactive'."""
        cols = db_models["MCP"].__table__.columns
        assert cols["status"].default.arg == "inactive"

    def test_default_github_ref(self, db_models):
        """MCP github_ref defaults to 'main'."""
        cols = db_models["MCP"].__table__.columns
        assert cols["github_ref"].default.arg == "main"


# ──────────────────────────────────────────────
# Provider Model
# ──────────────────────────────────────────────

class TestProviderModel:
    """Test the Provider database model."""

    def test_table_name(self, db_models):
        """Provider table name is 'providers'."""
        assert db_models["Provider"].__tablename__ == "providers"

    def test_has_required_fields(self, db_models):
        """Provider has all required fields."""
        cols = db_models["Provider"].__table__.columns
        assert "id" in cols
        assert "name" in cols
        assert "base_url" in cols
        assert "api_key_encrypted" in cols
        assert "status" in cols

    def test_name_unique(self, db_models):
        """Provider name has unique constraint."""
        name_col = db_models["Provider"].__table__.columns["name"]
        assert name_col.unique is True


# ──────────────────────────────────────────────
# Chat, Session, Log, Metric Models
# ──────────────────────────────────────────────

class TestSecondaryModels:
    """Test Chat, Session, Log, and Metric models."""

    def test_chat_table(self, db_models):
        """Chat table name and fields."""
        model = db_models["Chat"]
        assert model.__tablename__ == "chats"
        cols = model.__table__.columns
        assert "session_id" in cols
        assert cols["session_id"].index is True
        assert "role" in cols
        assert "content" in cols

    def test_session_table(self, db_models):
        """Session table name and unique constraint."""
        model = db_models["Session"]
        assert model.__tablename__ == "sessions"
        cols = model.__table__.columns
        assert cols["session_id"].unique is True
        assert cols["theme"].default.arg == "neon"

    def test_log_table(self, db_models):
        """Log table name and required fields."""
        model = db_models["Log"]
        assert model.__tablename__ == "logs"
        cols = model.__table__.columns
        assert "level" in cols
        assert "logger" in cols
        assert "message" in cols

    def test_metric_table(self, db_models):
        """Metric table name and default values."""
        model = db_models["Metric"]
        assert model.__tablename__ == "metrics"
        cols = model.__table__.columns
        assert cols["cpu_percent"].default.arg == 0.0
        assert cols["active_models"].default.arg == 0
        assert cols["active_mcps"].default.arg == 0
        assert "timestamp" in cols


# ──────────────────────────────────────────────
# DateTime Defaults
# ──────────────────────────────────────────────

class TestDateTimeDefaults:
    """Test datetime default values create valid timestamps."""

    def _call_default(self, col):
        """Get datetime default value from a column, handling SQLAlchemy's default wrapping."""
        default = col.default
        if default is None:
            return None
        arg = default.arg if hasattr(default, 'arg') else default
        if callable(arg):
            return arg()
        return arg

    def test_model_created_at_is_datetime(self, db_models):
        """Model created_at default produces datetime."""
        result = self._call_default(db_models["Model"].__table__.columns["created_at"])
        assert isinstance(result, datetime)
        if result is not None and result.tzinfo is not None:
            assert result.tzinfo is not None

    def test_mcp_created_at_is_datetime(self, db_models):
        """MCP created_at default produces datetime."""
        result = self._call_default(db_models["MCP"].__table__.columns["created_at"])
        assert isinstance(result, datetime)

    def test_chat_timestamp_is_datetime(self, db_models):
        """Chat timestamp default produces datetime."""
        result = self._call_default(db_models["Chat"].__table__.columns["timestamp"])
        assert isinstance(result, datetime)
