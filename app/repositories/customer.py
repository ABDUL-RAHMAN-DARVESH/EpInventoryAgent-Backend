import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


async def create(db: AsyncSession, customer: Customer) -> Customer:
    db.add(customer)
    await db.flush()
    return customer


async def get(db: AsyncSession, owner_id: uuid.UUID, customer_id: uuid.UUID) -> Customer | None:
    stmt = select(Customer).where(Customer.id == customer_id, Customer.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession, *, owner_id: uuid.UUID, is_active: bool | None = None, skip: int = 0, limit: int = 100
) -> list[Customer]:
    stmt = select(Customer).where(Customer.owner_id == owner_id)
    if is_active is not None:
        stmt = stmt.where(Customer.is_active == is_active)
    stmt = stmt.order_by(Customer.name).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
