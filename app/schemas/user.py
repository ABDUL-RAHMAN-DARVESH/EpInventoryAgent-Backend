import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Admin-only: there is no public self-signup endpoint."""

    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = Field(None, max_length=255)
    role: UserRole = UserRole.STAFF
    expires_at: date | None = None


class UserUpdate(BaseModel):
    """Admin-only: enable/disable, extend/clear expiry, change role or name,
    or reset a password (e.g. rotating the bootstrap admin's known default)."""

    full_name: str | None = Field(None, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    expires_at: date | None = None
    password: str | None = Field(None, min_length=8, max_length=255)


class FeatureFlag(BaseModel):
    key: str
    name: str
    enabled: bool


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    expires_at: date | None
    created_at: datetime
    updated_at: datetime

    # Presence of shop_name is what the frontend treats as "onboarding done" --
    # see RootNavigator.js. All four are None until first-login setup completes.
    shop_name: str | None
    shop_address: str | None
    shop_phone: str | None
    shop_logo_url: str | None
    shop_image_url: str | None


class UserWithFeatures(UserRead):
    features: list[FeatureFlag]
