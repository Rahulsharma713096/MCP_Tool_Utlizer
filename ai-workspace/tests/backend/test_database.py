"""Database Tests - Covers DB test cases from test.txt."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Model, MCP, Provider, Chat, Session, Log, Metric


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


class TestModelCRUD:
    """DB-001 to DB-003: Model CRUD tests"""

    def test_insert_model(self, db_session):
        """DB-001: Insert model"""
        model = Model(name="llama3", provider="ollama", size="4.7GB", quantization="Q4_K_M")
        db_session.add(model)
        db_session.commit()

        saved = db_session.query(Model).filter_by(name="llama3").first()
        assert saved is not None
        assert saved.name == "llama3"
        assert saved.provider == "ollama"
        assert saved.size == "4.7GB"

    def test_update_model(self, db_session):
        """DB-002: Update model"""
        model = Model(name="llama3", provider="ollama", active=False)
        db_session.add(model)
        db_session.commit()

        model.active = True
        model.runtime_pid = 12345
        db_session.commit()

        updated = db_session.query(Model).filter_by(name="llama3").first()
        assert updated.active is True
        assert updated.runtime_pid == 12345

    def test_delete_model(self, db_session):
        """DB-003: Delete model"""
        model = Model(name="mistral", provider="ollama")
        db_session.add(model)
        db_session.commit()

        db_session.delete(model)
        db_session.commit()

        deleted = db_session.query(Model).filter_by(name="mistral").first()
        assert deleted is None

    def test_model_defaults(self, db_session):
        """Test model default values"""
        model = Model(name="test-model", provider="ollama")
        db_session.add(model)
        db_session.commit()

        assert model.active is False
        assert model.cpu_usage == 0.0
        assert model.ram_usage == 0.0
        assert model.created_at is not None
        assert model.updated_at is not None


class TestMCPCRUD:
    """DB-004: MCP CRUD tests"""

    def test_insert_mcp(self, db_session):
        """DB-004: Insert MCP"""
        mcp = MCP(
            name="filesystem",
            type="filesystem",
            enabled=True,
            transport="stdio",
            command="python",
            args=["filesystem_mcp.py"],
        )
        db_session.add(mcp)
        db_session.commit()

        saved = db_session.query(MCP).filter_by(name="filesystem").first()
        assert saved is not None
        assert saved.enabled is True
        assert saved.transport == "stdio"

    def test_update_mcp(self, db_session):
        """Update MCP config"""
        mcp = MCP(name="test-mcp", type="test", enabled=False)
        db_session.add(mcp)
        db_session.commit()

        mcp.enabled = True
        mcp.endpoint = "http://localhost:8080"
        db_session.commit()

        updated = db_session.query(MCP).filter_by(name="test-mcp").first()
        assert updated.enabled is True
        assert updated.endpoint == "http://localhost:8080"


class TestProviderCRUD:
    """DB-005: Provider CRUD tests"""

    def test_insert_provider(self, db_session):
        """DB-005: Insert provider"""
        provider = Provider(
            name="OpenRouter",
            enabled=True,
            base_url="https://openrouter.ai/api/v1",
            selected_model="mistral-large",
        )
        db_session.add(provider)
        db_session.commit()

        saved = db_session.query(Provider).filter_by(name="OpenRouter").first()
        assert saved is not None
        assert saved.base_url == "https://openrouter.ai/api/v1"


class TestDataIntegrity:
    """DBI-001 to DBI-004: Data integrity tests"""

    def test_unique_model_name(self, db_session):
        """DBI-002: Duplicate model prevented"""
        model1 = Model(name="llama3", provider="ollama")
        model2 = Model(name="llama3", provider="ollama")
        db_session.add(model1)
        db_session.commit()

        with pytest.raises(Exception):
            db_session.add(model2)
            db_session.commit()
        db_session.rollback()

    def test_unique_mcp_name(self, db_session):
        """DBI-002: Duplicate MCP prevented"""
        mcp1 = MCP(name="unique-mcp", type="test")
        mcp2 = MCP(name="unique-mcp", type="test")
        db_session.add(mcp1)
        db_session.commit()

        with pytest.raises(Exception):
            db_session.add(mcp2)
            db_session.commit()
        db_session.rollback()

    def test_null_values_handling(self, db_session):
        """DBI-003: Null values validation"""
        model = Model(name="test", provider="ollama", runtime_pid=None)
        db_session.add(model)
        db_session.commit()

        saved = db_session.query(Model).filter_by(name="test").first()
        assert saved.runtime_pid is None

    def test_json_field_serialization(self, db_session):
        """DBI-004: Config JSON validation"""
        config_data = {"key": "value", "nested": {"foo": "bar"}}
        mcp = MCP(name="json-mcp", type="test", config=config_data)
        db_session.add(mcp)
        db_session.commit()

        saved = db_session.query(MCP).filter_by(name="json-mcp").first()
        assert saved.config == config_data
        assert saved.config["key"] == "value"
        assert saved.config["nested"]["foo"] == "bar"


class TestChatAndSessions:
    """DB-006: Session persistence tests"""

    def test_insert_chat_message(self, db_session):
        """DB-006: Session persistence"""
        chat = Chat(
            session_id="session-123",
            role="user",
            content="Hello!",
            model="llama3",
            provider="ollama",
        )
        db_session.add(chat)
        db_session.commit()

        saved = db_session.query(Chat).filter_by(session_id="session-123").first()
        assert saved is not None
        assert saved.role == "user"
        assert saved.content == "Hello!"
        assert saved.model == "llama3"

    def test_chat_session_messages(self, db_session):
        """Multiple messages in a session"""
        session_id = "test-session"
        messages = [
            Chat(session_id=session_id, role="user", content="Hi"),
            Chat(session_id=session_id, role="assistant", content="Hello!"),
            Chat(session_id=session_id, role="user", content="How are you?"),
        ]
        for msg in messages:
            db_session.add(msg)
        db_session.commit()

        saved = db_session.query(Chat).filter_by(session_id=session_id).all()
        assert len(saved) == 3


class TestMetrics:
    """Metrics storage tests"""

    def test_insert_metric(self, db_session):
        metric = Metric(
            cpu_percent=45.5,
            ram_percent=62.3,
            ram_used_gb=8.2,
            active_models=2,
            active_mcps=3,
        )
        db_session.add(metric)
        db_session.commit()

        saved = db_session.query(Metric).first()
        assert saved.cpu_percent == 45.5
        assert saved.ram_percent == 62.3
        assert saved.active_models == 2
        assert saved.active_mcps == 3


class TestRollback:
    """DB-007: Rollback on failure"""

    def test_rollback_on_failure(self, db_session):
        """DB-007: Rollback on constraint violation"""
        # Insert first model
        model1 = Model(name="unique-model", provider="ollama")
        db_session.add(model1)
        db_session.commit()

        # Try to insert duplicate
        model2 = Model(name="unique-model", provider="ollama")
        db_session.add(model2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

        # Verify only one model exists
        count = db_session.query(Model).count()
        assert count == 1
