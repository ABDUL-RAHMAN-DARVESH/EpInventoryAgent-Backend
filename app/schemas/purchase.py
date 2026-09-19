import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod, PaymentStatus


class PurchaseItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    unit_price: Decimal | None = Field(None, gt=0, decimal_places=2)
    line_total: Decimal | None = Field(None, gt=0, decimal_places=2)


class PurchaseItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    unit_price: Decimal | None
    quantity: int
    line_total: Decimal


class InitialPayment(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod = PaymentMethod.CASH
    reference_number: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)


class PurchaseCreate(BaseModel):
    manufacturer_id: uuid.UUID
    purchase_date: date | None = None
    due_date: date | None = None
    items: list[PurchaseItemCreate] = Field(..., min_length=1)
    notes: str | None = Field(None, max_length=1000)
    initial_payment: InitialPayment | None = None


class PurchaseUpdate(BaseModel):
    due_date: date | None = None
    notes: str | None = Field(None, max_length=1000)
    items: list[PurchaseItemCreate] | None = Field(None, min_length=1)


class PurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    manufacturer_id: uuid.UUID
    purchase_date: date
    due_date: date | None
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    payment_status: PaymentStatus
    notes: str | None
    items: list[PurchaseItemRead]
    created_at: datetime
    updated_at: datetime
