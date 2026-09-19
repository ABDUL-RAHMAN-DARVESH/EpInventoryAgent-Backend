import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sale import Sale


async def create(db: AsyncSession, sale: Sale) -> Sale:
    db.add(sale)
    await db.flush()
    return sale


async def get(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID) -> Sale | None:
    stmt = (
        select(Sale)
        .where(Sale.id == sale_id, Sale.owner_id == owner_id)
        .options(selectinload(Sale.items))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete(db: AsyncSession, sale: Sale) -> None:
    await db.delete(sale)


async def get_for_update(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID) -> Sale | None:
    """Locks the sale row to keep balance calculations transaction-safe under concurrent payments."""
    stmt = (
        select(Sale)
        .where(Sale.id == sale_id, Sale.owner_id == owner_id)
        .options(selectinload(Sale.items))
        .with_for_update()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Sale]:
    stmt = select(Sale).where(Sale.owner_id == owner_id).options(selectinload(Sale.items))
    if customer_id is not None:
        stmt = stmt.where(Sale.customer_id == customer_id)
    stmt = stmt.order_by(Sale.sale_date.desc(), Sale.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
