import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod, PaymentStatus


class SaleItemCreate(BaseModel):
    product_id: uuid.UUID
    unit_price: Decimal = Field(..., gt=0, decimal_places=2)
    quantity: int = Field(..., gt=0)


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class InitialPayment(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod = PaymentMethod.CASH
    reference_number: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)


class SaleCreate(BaseModel):
    customer_id: uuid.UUID
    sale_date: date | None = None
    due_date: date | None = None
    items: list[SaleItemCreate] = Field(..., min_length=1)
    notes: str | None = Field(None, max_length=1000)
    initial_payment: InitialPayment | None = None


class SaleUpdate(BaseModel):
    due_date: date | None = None
    notes: str | None = Field(None, max_length=1000)
    items: list[SaleItemCreate] | None = Field(None, min_length=1)


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    sale_date: date
    due_date: date | None
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    payment_status: PaymentStatus
    notes: str | None
    items: list[SaleItemRead]
    created_at: datetime
    updated_at: datetime
