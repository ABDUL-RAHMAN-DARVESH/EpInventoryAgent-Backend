import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase import Purchase


async def create(db: AsyncSession, purchase: Purchase) -> Purchase:
    db.add(purchase)
    await db.flush()
    return purchase


async def get(db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID) -> Purchase | None:
    stmt = (
        select(Purchase)
        .where(Purchase.id == purchase_id, Purchase.owner_id == owner_id)
        .options(selectinload(Purchase.items))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete(db: AsyncSession, purchase: Purchase) -> None:
    await db.delete(purchase)


async def get_for_update(db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID) -> Purchase | None:
    """Locks the purchase row to keep balance calculations transaction-safe under concurrent payments."""
    stmt = (
        select(Purchase)
        .where(Purchase.id == purchase_id, Purchase.owner_id == owner_id)
        .options(selectinload(Purchase.items))
        .with_for_update()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    manufacturer_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Purchase]:
    stmt = select(Purchase).where(Purchase.owner_id == owner_id).options(selectinload(Purchase.items))
    if manufacturer_id is not None:
        stmt = stmt.where(Purchase.manufacturer_id == manufacturer_id)
    stmt = stmt.order_by(Purchase.purchase_date.desc(), Purchase.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
