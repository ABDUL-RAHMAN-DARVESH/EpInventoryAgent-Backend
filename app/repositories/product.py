import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


async def create(db: AsyncSession, product: Product) -> Product:
    db.add(product)
    await db.flush()
    return product


async def get(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID) -> Product | None:
    stmt = select(Product).where(Product.id == product_id, Product.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_sku(db: AsyncSession, owner_id: uuid.UUID, sku: str) -> Product | None:
    stmt = select(Product).where(Product.owner_id == owner_id, Product.sku == sku)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession, *, owner_id: uuid.UUID, is_active: bool | None = None, skip: int = 0, limit: int = 100
) -> list[Product]:
    stmt = select(Product).where(Product.owner_id == owner_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    stmt = stmt.order_by(Product.name).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
