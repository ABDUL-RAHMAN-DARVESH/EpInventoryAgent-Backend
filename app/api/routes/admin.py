import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.schemas.app_version import AppVersionRead, AppVersionUpdate
from app.schemas.feature import FeatureCreate, FeatureRead, UserFeatureUpdate
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserWithFeatures
from app.services import app_version_service, feature_service, user_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


# --- Users ---------------------------------------------------------------


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await user_service.create_user(db, data)


@router.get("/users", response_model=list[UserRead])
async def list_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await user_service.list_users(db, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=UserWithFeatures)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user(db, user_id)
    features = await user_service.get_user_features(db, user_id)
    return UserWithFeatures(**UserRead.model_validate(user).model_dump(), features=features)


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: uuid.UUID, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Covers enable/disable (`is_active`) and license expiry (`expires_at`) in one endpoint."""
    return await user_service.update_user(db, user_id, data)


# --- Feature catalog + per-user toggles -----------------------------------


@router.get("/features", response_model=list[FeatureRead])
async def list_features(db: AsyncSession = Depends(get_db)):
    return await feature_service.list_features(db)


@router.post("/features", response_model=FeatureRead, status_code=201)
async def create_feature(data: FeatureCreate, db: AsyncSession = Depends(get_db)):
    return await feature_service.create_feature(db, data)


@router.patch("/users/{user_id}/features/{feature_key}", response_model=FeatureRead)
async def set_user_feature(user_id: uuid.UUID, feature_key: str, data: UserFeatureUpdate, db: AsyncSession = Depends(get_db)):
    return await user_service.set_user_feature(db, user_id, feature_key, data.enabled)


# --- App version config ----------------------------------------------------


@router.get("/app-versions", response_model=list[AppVersionRead])
async def list_app_versions(db: AsyncSession = Depends(get_db)):
    return await app_version_service.list_configs(db)


@router.put("/app-versions/{platform}", response_model=AppVersionRead)
async def set_app_version(platform: str, data: AppVersionUpdate, db: AsyncSession = Depends(get_db)):
    return await app_version_service.upsert_config(db, platform, data)
