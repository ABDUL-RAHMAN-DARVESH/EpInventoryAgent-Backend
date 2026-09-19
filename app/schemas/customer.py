import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    area: str | None = Field(None, max_length=255)
    landmark: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    area: str | None = Field(None, max_length=255)
    landmark: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
