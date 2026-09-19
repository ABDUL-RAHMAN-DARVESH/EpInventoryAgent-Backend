import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manufacturer import Manufacturer


async def create(db: AsyncSession, manufacturer: Manufacturer) -> Manufacturer:
    db.add(manufacturer)
    await db.flush()
    return manufacturer


async def get(db: AsyncSession, owner_id: uuid.UUID, manufacturer_id: uuid.UUID) -> Manufacturer | None:
    stmt = select(Manufacturer).where(Manufacturer.id == manufacturer_id, Manufacturer.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession, *, owner_id: uuid.UUID, is_active: bool | None = None, skip: int = 0, limit: int = 100
) -> list[Manufacturer]:
    stmt = select(Manufacturer).where(Manufacturer.owner_id == owner_id)
    if is_active is not None:
        stmt = stmt.where(Manufacturer.is_active == is_active)
    stmt = stmt.order_by(Manufacturer.name).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
