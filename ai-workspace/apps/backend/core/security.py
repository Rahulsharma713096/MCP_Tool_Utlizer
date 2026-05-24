"""Security module: JWT authentication, encryption, and authorization."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import os

from jose import JWTError, jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============== JWT Authentication ==============

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> bool:
    """Verify if a token is valid."""
    return decode_access_token(token) is not None


# ============== Password Hashing ==============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ============== API Key Encryption ==============

def _get_fernet() -> Fernet:
    """Get or create a Fernet encryption instance."""
    key = settings.ENCRYPTION_KEY
    if not key:
        # Generate a deterministic key from the secret key
        key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = Fernet.generate_key()
        # Use base64-encoded hash as the key
        from base64 import urlsafe_b64encode
        key = urlsafe_b64encode(key_bytes)
    return Fernet(key if isinstance(key, bytes) else key.encode())


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for secure storage."""
    fernet = _get_fernet()
    return fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    fernet = _get_fernet()
    return fernet.decrypt(encrypted_key.encode()).decode()


# ============== Input Validation ==============

def sanitize_command(command: str) -> bool:
    """Check if a command is safe to execute."""
    dangerous_commands = [
        "rm", "del", "format", "dd", "mkfs",
        ">", ">>", "|", ";", "&&", "||",
        "sudo", "su", "chmod", "chown",
        "shutdown", "reboot", "init"
    ]
    command_lower = command.lower()
    return not any(dc in command_lower for dc in dangerous_commands)


def validate_path(path: str, allowed_paths: list[str]) -> bool:
    """Check if a path is within allowed directories."""
    normalized = os.path.normpath(os.path.abspath(path))
    return any(normalized.startswith(os.path.normpath(ap)) for ap in allowed_paths)


# ============== Rate Limiting Helper ==============

def get_client_ip(request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
