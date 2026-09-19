import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.customer import Customer
from app.repositories import customer as customer_repo
from app.schemas.customer import CustomerCreate, CustomerUpdate


async def create_customer(db: AsyncSession, owner_id: uuid.UUID, data: CustomerCreate) -> Customer:
    customer = Customer(owner_id=owner_id, **data.model_dump())
    customer = await customer_repo.create(db, customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def get_customer(db: AsyncSession, owner_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
    customer = await customer_repo.get(db, owner_id, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    return customer


async def list_customers(
    db: AsyncSession, owner_id: uuid.UUID, *, is_active: bool | None = None, skip: int = 0, limit: int = 100
) -> list[Customer]:
    return await customer_repo.list_all(db, owner_id=owner_id, is_active=is_active, skip=skip, limit=limit)


async def update_customer(db: AsyncSession, owner_id: uuid.UUID, customer_id: uuid.UUID, data: CustomerUpdate) -> Customer:
    customer = await get_customer(db, owner_id, customer_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer


async def deactivate_customer(db: AsyncSession, owner_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
    customer = await get_customer(db, owner_id, customer_id)
    customer.is_active = False
    await db.commit()
    await db.refresh(customer)
    return customer
