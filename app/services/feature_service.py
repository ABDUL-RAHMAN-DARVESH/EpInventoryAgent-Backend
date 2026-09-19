from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.feature import Feature
from app.repositories import feature as feature_repo
from app.schemas.feature import FeatureCreate


async def create_feature(db: AsyncSession, data: FeatureCreate) -> Feature:
    existing = await feature_repo.get_by_key(db, data.key)
    if existing is not None:
        raise ConflictError(f"A feature with key '{data.key}' already exists")

    feature = Feature(**data.model_dump())
    feature = await feature_repo.create(db, feature)
    await db.commit()
    await db.refresh(feature)
    return feature


async def list_features(db: AsyncSession) -> list[Feature]:
    return await feature_repo.list_all(db)
