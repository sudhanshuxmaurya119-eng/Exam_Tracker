"""Security utilities: password hashing (bcrypt), JWT token generation, and validation."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import get_settings


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with a random salt."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: str | int,
    role: str,
    username: str,
    expires_delta: Optional[timedelta] = None,
) -> Dict[str, Any]:
    """Generate a signed JWT access token with expiration metadata."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(subject),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "expires_in": int((expire - now).total_seconds()),
        "expires_at": expire.isoformat(),
    }


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token. Raises ValueError if invalid or expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        return payload
    except InvalidTokenError as exc:
        raise ValueError(f"Invalid or expired authentication token: {exc}") from exc
