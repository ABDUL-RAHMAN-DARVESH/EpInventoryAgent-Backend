import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    brand: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=255)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    brand: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Derived from purchase/sale line-item history, not stored columns --
    # always computed fresh (see product_service.py), so it can never drift
    # out of sync with the actual sales/purchases on record.
    total_purchased: int
    total_sold: int
    available_quantity: int
