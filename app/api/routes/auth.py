from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserRead, UserWithFeatures
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, data.email, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh(db, data.refresh_token)


@router.get("/me", response_model=UserWithFeatures)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    features = await user_service.get_user_features(db, current_user.id)
    return UserWithFeatures(**UserRead.model_validate(current_user).model_dump(), features=features)
