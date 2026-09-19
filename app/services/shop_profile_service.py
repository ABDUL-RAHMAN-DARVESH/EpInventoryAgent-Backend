from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.user import User
from app.schemas.shop_profile import ShopProfileUpdate


async def update_shop_profile(db: AsyncSession, user: User, data: ShopProfileUpdate) -> User:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def upload_shop_logo(db: AsyncSession, user: User, file_bytes: bytes, content_type: str) -> User:
    ext = storage.extension_for(content_type)
    user.shop_logo_url = await storage.upload_image(file_bytes, content_type, f"shop/{user.id}/logo.{ext}")
    await db.commit()
    await db.refresh(user)
    return user


async def upload_shop_image(db: AsyncSession, user: User, file_bytes: bytes, content_type: str) -> User:
    ext = storage.extension_for(content_type)
    user.shop_image_url = await storage.upload_image(file_bytes, content_type, f"shop/{user.id}/image.{ext}")
    await db.commit()
    await db.refresh(user)
    return user
