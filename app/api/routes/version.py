from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.app_version import VersionCheckResponse
from app.services import app_version_service

router = APIRouter(prefix="/version", tags=["version"])


@router.get("/check", response_model=VersionCheckResponse)
async def check_version(platform: str, version: str, db: AsyncSession = Depends(get_db)):
    """Public/unauthenticated on purpose -- a very old or broken client may not
    be able to log in at all, but still needs to be told to update."""
    return await app_version_service.check_version(db, platform, version)
