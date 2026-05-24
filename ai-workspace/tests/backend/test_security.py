"""Security Tests - Covers SEC test cases from test.txt."""

import pytest
from datetime import datetime, timedelta, timezone

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
)


class TestJWTAuthentication:
    """SEC-001 to SEC-003: Authentication tests"""

    def test_create_access_token(self):
        """SEC-001: Positive - Create valid JWT"""
        token = create_access_token({"sub": "testuser"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_decode_valid_token(self):
        """SEC-001: Positive - Decode valid JWT"""
        token = create_access_token({"sub": "testuser"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"

    def test_verify_valid_token(self):
        """SEC-001: Positive - Verify valid JWT"""
        token = create_access_token({"sub": "testuser"})
        assert verify_token(token) is True

    def test_decode_invalid_token(self):
        """SEC-001: Negative - Invalid JWT blocked"""
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_verify_invalid_token(self):
        """SEC-001: Negative - Verify invalid JWT"""
        assert verify_token("invalid.token.here") is False

    def test_decode_expired_token(self):
        """SEC-002: Negative - Expired session"""
        token = create_access_token(
            {"sub": "testuser"},
            expires_delta=timedelta(seconds=-1),  # Expired
        )
        payload = decode_access_token(token)
        assert payload is None


class TestPasswordHashing:
    """SEC: Password security tests"""

    def test_hash_password(self):
        """SEC-007: Positive - Hash password"""
        hashed = hash_password("secure_password_123")
        assert hashed is not None
        assert hashed != "secure_password_123"

    def test_verify_correct_password(self):
        """SEC-007: Positive - Verify correct password"""
        hashed = hash_password("secure_password_123")
        assert verify_password("secure_password_123", hashed) is True

    def test_verify_wrong_password(self):
        """SEC-007: Negative - Wrong password rejected"""
        hashed = hash_password("secure_password_123")
        assert verify_password("wrong_password", hashed) is False

    def test_unique_hashes(self):
        """SEC-007: Each hash should be unique"""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert hash1 != hash2


class TestAPIKeyEncryption:
    """SEC-007 to SEC-009: API key encryption tests"""

    def test_encrypt_api_key(self):
        """SEC-007: Positive - Encrypt API key"""
        encrypted = encrypt_api_key("sk-test-api-key-12345")
        assert encrypted is not None
        assert encrypted != "sk-test-api-key-12345"

    def test_decrypt_api_key(self):
        """SEC-007: Positive - Decrypt API key"""
        original = "sk-test-api-key-12345"
        encrypted = encrypt_api_key(original)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original

    def test_encryption_different_outputs(self):
        """SEC-007: Same key encrypts differently each time"""
        key = "sk-test-key"
        enc1 = encrypt_api_key(key)
        enc2 = encrypt_api_key(key)
        assert enc1 != enc2  # Fernet uses random IVs

    def test_decrypt_invalid_ciphertext(self):
        """SEC-007: Negative - Invalid ciphertext"""
        with pytest.raises(Exception):
            decrypt_api_key("invalid-encrypted-data")


class TestInputSanitization:
    """SEC-004 to SEC-005: Injection prevention tests"""

    def test_sanitize_safe_command(self):
        """SEC-005: Positive - Safe command allowed"""
        assert sanitize_command("python script.py") is True
        assert sanitize_command("node app.js") is True

    def test_sanitize_dangerous_command(self):
        """SEC-005: Negative - Dangerous command blocked"""
        assert sanitize_command("rm -rf /") is False
        assert sanitize_command("sudo rm") is False
        assert sanitize_command("shutdown now") is False

    def test_sanitize_command_injection(self):
        """SEC-005: Negative - Command injection blocked"""
        assert sanitize_command("python; rm -rf /") is False
        assert sanitize_command("python | cat /etc/passwd") is False

    def test_validate_allowed_path(self):
        """SEC-006: Positive - Valid path within allowed dirs"""
        import os
        # Use a path that works cross-platform: the current directory
        cwd = os.getcwd()
        assert validate_path(os.path.join(cwd, "file.txt"), [cwd]) is True

    def test_validate_blocked_path(self):
        """SEC-006: Negative - Path outside allowed dirs"""
        assert validate_path("/etc/passwd", ["/workspace", "/documents"]) is False


class TestSecurityIntegration:
    """SEC: Security integration tests"""

    def test_full_auth_flow(self):
        """Test complete authentication flow"""
        # Login
        hashed = hash_password("password123")

        # Create token
        token = create_access_token({"sub": "user123"})
        assert verify_token(token) is True

        # Decode and verify
        payload = decode_access_token(token)
        assert payload["sub"] == "user123"

    def test_encrypted_storage_flow(self):
        """Test complete encrypted storage flow"""
        api_key = "sk-very-secret-key-12345"

        # Store
        encrypted = encrypt_api_key(api_key)

        # Retrieve
        decrypted = decrypt_api_key(encrypted)

        # Verify
        assert decrypted == api_key

    def test_security_headers_format(self):
        """SEC-008: Token format validation"""
        token = create_access_token({"sub": "admin"})
        parts = token.split(".")
        assert len(parts) == 3

        # Header should be valid base64url
        import base64
        try:
            header = base64.urlsafe_b64decode(parts[0] + "==")
            assert b"alg" in header
        except Exception:
            pytest.fail("Invalid token header format")
