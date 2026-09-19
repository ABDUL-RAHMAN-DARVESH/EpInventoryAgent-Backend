from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_version import AppVersionConfig


async def get_by_platform(db: AsyncSession, platform: str) -> AppVersionConfig | None:
    stmt = select(AppVersionConfig).where(AppVersionConfig.platform == platform)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[AppVersionConfig]:
    stmt = select(AppVersionConfig).order_by(AppVersionConfig.platform)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, config: AppVersionConfig) -> AppVersionConfig:
    db.add(config)
    await db.flush()
    return config
