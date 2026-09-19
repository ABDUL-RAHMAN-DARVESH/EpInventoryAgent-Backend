import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AppVersionConfig(Base, TimestampMixin):
    """One row per platform ("android", "ios", ...). `latest_version` drives the
    dismissible "Update available" prompt; `minimum_version` drives the
    blocking force-update screen. Versions are plain dotted strings (e.g.
    "1.2.0"), compared as dotted-integer tuples -- see app_version_service.py."""

    __tablename__ = "app_version_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    latest_version: Mapped[str] = mapped_column(String(30), nullable=False)
    minimum_version: Mapped[str] = mapped_column(String(30), nullable=False)
