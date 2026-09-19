import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_token(subject: uuid.UUID, expires_delta: timedelta, token_type: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    return _create_token(user_id, timedelta(minutes=settings.access_token_expire_minutes), "access")


def create_refresh_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    return _create_token(user_id, timedelta(days=settings.refresh_token_expire_days), "refresh")


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError (or a subclass) on an invalid/expired token -- callers
    translate that into an UnauthorizedError; this module stays HTTP-agnostic."""
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
