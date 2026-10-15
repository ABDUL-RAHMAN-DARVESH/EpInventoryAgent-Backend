import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PartyNumberCounter(Base):
    __tablename__ = "party_number_counters"
    __table_args__ = (CheckConstraint("party_type IN ('customer', 'manufacturer')", name="ck_party_number_type"),)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    party_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
