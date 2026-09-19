import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaymentMethod


class CustomerPayment(Base):
    __tablename__ = "customer_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method_enum"), nullable=False, default=PaymentMethod.CASH
    )
    reference_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="payments")
    sale: Mapped["Sale"] = relationship(back_populates="payments")


class ManufacturerPayment(Base):
    __tablename__ = "manufacturer_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("manufacturers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method_enum"), nullable=False, default=PaymentMethod.CASH
    )
    reference_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="payments")
    purchase: Mapped["Purchase"] = relationship(back_populates="payments")
