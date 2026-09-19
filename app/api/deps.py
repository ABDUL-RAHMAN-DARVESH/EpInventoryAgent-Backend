import uuid
from datetime import datetime, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories import feature as feature_repo
from app.repositories import user as user_repo

__all__ = ["get_db", "get_current_user", "get_current_admin"]

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise UnauthorizedError("Invalid token")

    user = await user_repo.get(db, user_id)
    if user is None:
        raise UnauthorizedError("Invalid token")

    # Re-checked against the DB on every request, not just at login -- so
    # disabling a user or letting their license lapse takes effect immediately,
    # regardless of how long their access token still has left to live.
    if not user.is_active:
        raise UnauthorizedError("This account has been disabled. Contact your administrator.")
    if user.expires_at is not None and user.expires_at < datetime.now(timezone.utc).date():
        raise UnauthorizedError("This account's access has expired. Contact your administrator.")

    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    return current_user


def require_feature(feature_key: str):
    """Dependency factory for gating a feature-specific endpoint, e.g.
    `Depends(require_feature("barcode_scanner"))`. Admins always pass, since
    they manage the feature toggles themselves."""

    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.role == UserRole.ADMIN:
            return current_user

        feature = await feature_repo.get_by_key(db, feature_key)
        if feature is None:
            raise ForbiddenError(f"Feature '{feature_key}' is not available")
        link = await feature_repo.get_user_feature(db, current_user.id, feature.id)
        if link is None or not link.enabled:
            raise ForbiddenError(f"Feature '{feature_key}' is not enabled for this account")
        return current_user

    return _check
