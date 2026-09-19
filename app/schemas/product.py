import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    brand: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=255)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(None, min_length=1, max_length=100)
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
