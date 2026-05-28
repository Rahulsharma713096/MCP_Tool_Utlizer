"""Unit tests for core.security - authentication, encryption, input validation.

Tests cover:
- JWT token creation, decoding, verification
- Token expiration handling
- Password hashing and verification
- API key encryption/decryption (Fernet)
- Command sanitization
- Path validation
- Client IP extraction
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────
# JWT Authentication
# ──────────────────────────────────────────────

class TestJWTAuth:
    """Test JWT token creation, decoding, and verification."""

    def test_create_access_token_returns_string(self):
        """create_access_token returns a string token."""
        from core.security import create_access_token
        token = create_access_token({"sub": "admin"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """decode_access_token returns payload for valid token."""
        from core.security import create_access_token, decode_access_token
        token = create_access_token({"sub": "testuser", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"

    def test_decode_invalid_token(self):
        """decode_access_token returns None for invalid token."""
        from core.security import decode_access_token
        payload = decode_access_token("invalid-token")
        assert payload is None

    def test_decode_expired_token(self):
        """decode_access_token returns None for expired token."""
        from core.security import create_access_token, decode_access_token
        token = create_access_token(
            {"sub": "testuser"},
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        payload = decode_access_token(token)
        assert payload is None

    def test_verify_valid_token(self):
        """verify_token returns True for valid token."""
        from core.security import create_access_token, verify_token
        token = create_access_token({"sub": "admin"})
        assert verify_token(token) is True

    def test_verify_invalid_token(self):
        """verify_token returns False for invalid token."""
        from core.security import verify_token
        assert verify_token("invalid") is False

    def test_create_token_with_custom_expiry(self):
        """create_access_token accepts custom expiration time."""
        from core.security import create_access_token, decode_access_token
        token = create_access_token(
            {"sub": "admin"},
            expires_delta=timedelta(hours=48),
        )
        payload = decode_access_token(token)
        assert payload is not None


# ──────────────────────────────────────────────
# Password Hashing
# ──────────────────────────────────────────────

class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_string(self):
        """hash_password returns a hash string."""
        from core.security import hash_password
        hashed = hash_password("my-secret-password")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        """verify_password returns True for matching password."""
        from core.security import hash_password, verify_password
        hashed = hash_password("my-password")
        assert verify_password("my-password", hashed) is True

    def test_verify_incorrect_password(self):
        """verify_password returns False for wrong password."""
        from core.security import hash_password, verify_password
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes(self):
        """hash_password produces different hashes for the same password (salt)."""
        from core.security import hash_password
        hash1 = hash_password("same-password")
        hash2 = hash_password("same-password")
        assert hash1 != hash2  # Different due to random salt


# ──────────────────────────────────────────────
# API Key Encryption
# ──────────────────────────────────────────────

class TestAPIKeyEncryption:
    """Test API key encryption and decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        """encrypt_api_key then decrypt_api_key returns original."""
        from core.security import encrypt_api_key, decrypt_api_key
        original = "sk-test-api-key-12345"
        encrypted = encrypt_api_key(original)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original

    def test_encrypted_value_is_different(self):
        """encrypt_api_key produces different string from input."""
        from core.security import encrypt_api_key
        original = "sk-test-key"
        encrypted = encrypt_api_key(original)
        assert encrypted != original

    def test_decrypt_invalid_raises_error(self):
        """decrypt_api_key raises error for invalid encrypted value."""
        from core.security import decrypt_api_key
        with pytest.raises(Exception):
            decrypt_api_key("not-encrypted")


# ──────────────────────────────────────────────
# Input Validation
# ──────────────────────────────────────────────

class TestInputValidation:
    """Test command sanitization and path validation."""

    def test_sanitize_safe_command(self):
        """sanitize_command returns True for safe commands."""
        from core.security import sanitize_command
        assert sanitize_command("python script.py") is True
        assert sanitize_command("npx -y @modelcontextprotocol/server") is True
        assert sanitize_command("ls -la") is True

    def test_sanitize_dangerous_rm(self):
        """sanitize_command returns False for rm commands."""
        from core.security import sanitize_command
        assert sanitize_command("rm -rf /") is False

    def test_sanitize_dangerous_sudo(self):
        """sanitize_command returns False for sudo commands."""
        from core.security import sanitize_command
        assert sanitize_command("sudo rm -rf") is False

    def test_sanitize_dangerous_shell_operators(self):
        """sanitize_command returns False for shell operators."""
        from core.security import sanitize_command
        assert sanitize_command("ls | grep test") is False
        assert sanitize_command("cmd1 && cmd2") is False
        assert sanitize_command("cmd1 || cmd2") is False

    def test_sanitize_dangerous_shutdown(self):
        """sanitize_command returns False for shutdown commands."""
        from core.security import sanitize_command
        assert sanitize_command("shutdown -h now") is False

    def test_validate_path_allowed(self):
        """validate_path returns True for paths within allowed dirs."""
        from core.security import validate_path
        import os
        # Use temp dir to be cross-platform (Windows vs Linux paths)
        allowed = os.path.normpath(os.path.abspath("/tmp"))
        test_path = os.path.join(allowed, "test")
        assert validate_path(test_path, [allowed]) is True

    def test_validate_path_not_allowed(self):
        """validate_path returns False for paths outside allowed dirs."""
        from core.security import validate_path
        import os
        allowed = os.path.normpath(os.path.abspath("/workspace"))
        assert validate_path("/etc/passwd", [allowed]) is False
        assert validate_path(os.path.normpath(os.path.abspath("/etc/passwd")), [allowed]) is False


# ──────────────────────────────────────────────
# Client IP
# ──────────────────────────────────────────────

class TestClientIP:
    """Test client IP extraction."""

    def test_get_client_ip_from_forwarded(self):
        """get_client_ip uses X-Forwarded-For header first."""
        from core.security import get_client_ip
        request = MagicMock()
        request.headers.get.return_value = "203.0.113.1, 10.0.0.1"
        ip = get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_from_request(self):
        """get_client_ip falls back to request.client.host."""
        from core.security import get_client_ip
        request = MagicMock()
        request.headers.get.return_value = None
        request.client.host = "192.168.1.1"
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_unknown(self):
        """get_client_ip returns 'unknown' when no info available."""
        from core.security import get_client_ip
        request = MagicMock()
        request.headers.get.return_value = None
        request.client = None
        ip = get_client_ip(request)
        assert ip == "unknown"
