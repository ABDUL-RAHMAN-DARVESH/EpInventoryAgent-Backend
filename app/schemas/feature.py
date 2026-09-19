import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class FeatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class UserFeatureUpdate(BaseModel):
    enabled: bool
