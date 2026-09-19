import uuid
from datetime import date, datetime, timezone

import jwt

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User
from app.repositories import user as user_repo
from app.schemas.auth import TokenResponse


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _assert_account_usable(user: User) -> None:
    """Shared by login and every authenticated request (via api/deps.get_current_user)
    -- re-checked against the DB every time, never trusted from a token claim, so
    admin disabling a user or a license lapsing takes effect on the user's very
    next request."""
    if not user.is_active:
        raise UnauthorizedError("This account has been disabled. Contact your administrator.")
    if user.expires_at is not None and user.expires_at < _today():
        raise UnauthorizedError("This account's access has expired. Contact your administrator.")


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await user_repo.get_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    _assert_account_usable(user)
    return user


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def login(db: AsyncSession, email: str, password: str) -> TokenResponse:
    user = await authenticate_user(db, email, password)
    return _issue_tokens(user)


async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise UnauthorizedError("Invalid refresh token")
    user = await user_repo.get(db, user_id)
    if user is None:
        raise UnauthorizedError("Invalid refresh token")
    _assert_account_usable(user)
    return _issue_tokens(user)
