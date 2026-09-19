import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    latest_version: str
    minimum_version: str
    updated_at: datetime


class AppVersionUpdate(BaseModel):
    latest_version: str = Field(..., min_length=1, max_length=30)
    minimum_version: str = Field(..., min_length=1, max_length=30)


class VersionCheckResponse(BaseModel):
    platform: str
    installed_version: str
    latest_version: str
    minimum_version: str
    update_available: bool
    force_update: bool
