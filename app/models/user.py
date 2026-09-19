import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.STAFF)

    # Admin-controlled account gate: a disabled user is rejected on every
    # request regardless of how fresh their JWT is (see api/deps.get_current_user).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # License expiry -- None means no expiry. Same re-check-on-every-request
    # enforcement as is_active.
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    feature_links: Mapped[list["UserFeature"]] = relationship(back_populates="user", cascade="all, delete-orphan")
