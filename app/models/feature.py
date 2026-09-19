import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Feature(TimestampMixin, Base):
    """The catalog of togglable features -- admin-managed via the admin API,
    never hard-coded. `key` is what the app/backend checks against (e.g.
    "barcode_scanner"); `name`/`description` are just for the admin UI/API."""

    __tablename__ = "features"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class UserFeature(Base):
    """Per-user on/off toggle for one Feature. Absence of a row for a given
    (user, feature) pair means "not enabled" -- rows only need to be created
    when a feature is turned on for a user, not for every feature x every user."""

    __tablename__ = "user_features"
    __table_args__ = (UniqueConstraint("user_id", "feature_id", name="uq_user_features_user_feature"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="feature_links")
    feature: Mapped["Feature"] = relationship()
