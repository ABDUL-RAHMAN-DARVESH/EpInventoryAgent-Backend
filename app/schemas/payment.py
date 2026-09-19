import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod


class CustomerPaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod = PaymentMethod.CASH
    reference_number: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)


class CustomerPaymentUpdate(BaseModel):
    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod | None = None
    reference_number: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)


class CustomerPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    sale_id: uuid.UUID
    amount: Decimal
    payment_date: date
    method: PaymentMethod
    reference_number: str | None
    notes: str | None
    created_at: datetime


class PaymentFeedItem(BaseModel):
    """A single entry in the unified customer+manufacturer payment feed (GET /payments)."""

    id: uuid.UUID
    type: Literal["CUSTOMER", "MANUFACTURER"]
    party_id: uuid.UUID
    party_name: str
    reference_id: uuid.UUID  # sale_id for CUSTOMER, purchase_id for MANUFACTURER
    amount: Decimal
    payment_date: date
    method: PaymentMethod
    reference_number: str | None
    notes: str | None
    created_at: datetime


class ManufacturerPaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod = PaymentMethod.CASH
    reference_number: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)


class ManufacturerPaymentUpdate(BaseModel):
    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod | None = None
    reference_number: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)


class ManufacturerPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    manufacturer_id: uuid.UUID
    purchase_id: uuid.UUID
    amount: Decimal
    payment_date: date
    method: PaymentMethod
    reference_number: str | None
    notes: str | None
    created_at: datetime
