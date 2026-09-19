from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.shop_profile import ShopProfileUpdate
from app.schemas.user import UserRead
from app.services import shop_profile_service

router = APIRouter(prefix="/shop-profile", tags=["shop-profile"])


@router.patch("", response_model=UserRead)
async def update_shop_profile(
    data: ShopProfileUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await shop_profile_service.update_shop_profile(db, current_user, data)


@router.post("/logo", response_model=UserRead)
async def upload_shop_logo(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    file_bytes = await file.read()
    return await shop_profile_service.upload_shop_logo(db, current_user, file_bytes, file.content_type)


@router.post("/image", response_model=UserRead)
async def upload_shop_image(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    file_bytes = await file.read()
    return await shop_profile_service.upload_shop_image(db, current_user, file_bytes, file.content_type)
