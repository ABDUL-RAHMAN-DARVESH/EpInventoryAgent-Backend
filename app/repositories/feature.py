import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.feature import Feature, UserFeature


async def create(db: AsyncSession, feature: Feature) -> Feature:
    db.add(feature)
    await db.flush()
    return feature


async def get(db: AsyncSession, feature_id: uuid.UUID) -> Feature | None:
    return await db.get(Feature, feature_id)


async def get_by_key(db: AsyncSession, key: str) -> Feature | None:
    stmt = select(Feature).where(Feature.key == key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[Feature]:
    stmt = select(Feature).order_by(Feature.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[UserFeature]:
    stmt = select(UserFeature).where(UserFeature.user_id == user_id).options(selectinload(UserFeature.feature))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_user_feature(db: AsyncSession, user_id: uuid.UUID, feature_id: uuid.UUID) -> UserFeature | None:
    stmt = select(UserFeature).where(UserFeature.user_id == user_id, UserFeature.feature_id == feature_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_user_feature(db: AsyncSession, user_id: uuid.UUID, feature_id: uuid.UUID, enabled: bool) -> UserFeature:
    link = await get_user_feature(db, user_id, feature_id)
    if link is None:
        link = UserFeature(user_id=user_id, feature_id=feature_id, enabled=enabled)
        db.add(link)
    else:
        link.enabled = enabled
    await db.flush()
    return link
