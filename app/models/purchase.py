import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import PaymentStatus


class Purchase(TimestampMixin, Base):
    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("manufacturers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    balance_due: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status_enum"), nullable=False, default=PaymentStatus.PENDING
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="purchases")
    items: Mapped[list["PurchaseItem"]] = relationship(back_populates="purchase", cascade="all, delete-orphan")
    payments: Mapped[list["ManufacturerPayment"]] = relationship(back_populates="purchase")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    purchase: Mapped["Purchase"] = relationship(back_populates="items")
