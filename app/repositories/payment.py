import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.manufacturer import Manufacturer
from app.models.payment import CustomerPayment, ManufacturerPayment


async def create_customer_payment(db: AsyncSession, payment: CustomerPayment) -> CustomerPayment:
    db.add(payment)
    await db.flush()
    return payment


async def get_customer_payment(db: AsyncSession, owner_id: uuid.UUID, payment_id: uuid.UUID) -> CustomerPayment | None:
    stmt = select(CustomerPayment).where(CustomerPayment.id == payment_id, CustomerPayment.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_customer_payment(db: AsyncSession, payment: CustomerPayment) -> None:
    await db.delete(payment)


async def list_customer_payments_by_sale(db: AsyncSession, owner_id: uuid.UUID, sale_id: uuid.UUID) -> list[CustomerPayment]:
    stmt = (
        select(CustomerPayment)
        .where(CustomerPayment.owner_id == owner_id, CustomerPayment.sale_id == sale_id)
        .order_by(CustomerPayment.payment_date.desc(), CustomerPayment.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_customer_payments_by_customer(
    db: AsyncSession, owner_id: uuid.UUID, customer_id: uuid.UUID
) -> list[CustomerPayment]:
    stmt = (
        select(CustomerPayment)
        .where(CustomerPayment.owner_id == owner_id, CustomerPayment.customer_id == customer_id)
        .order_by(CustomerPayment.payment_date.desc(), CustomerPayment.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_recent_customer_payments(db: AsyncSession, owner_id: uuid.UUID, limit: int) -> list[tuple[CustomerPayment, str]]:
    stmt = (
        select(CustomerPayment, Customer.name)
        .join(Customer, Customer.id == CustomerPayment.customer_id)
        .where(CustomerPayment.owner_id == owner_id)
        .order_by(CustomerPayment.payment_date.desc(), CustomerPayment.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(row.CustomerPayment, row.name) for row in result]


async def list_recent_manufacturer_payments(
    db: AsyncSession, owner_id: uuid.UUID, limit: int
) -> list[tuple[ManufacturerPayment, str]]:
    stmt = (
        select(ManufacturerPayment, Manufacturer.name)
        .join(Manufacturer, Manufacturer.id == ManufacturerPayment.manufacturer_id)
        .where(ManufacturerPayment.owner_id == owner_id)
        .order_by(ManufacturerPayment.payment_date.desc(), ManufacturerPayment.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(row.ManufacturerPayment, row.name) for row in result]


async def create_manufacturer_payment(db: AsyncSession, payment: ManufacturerPayment) -> ManufacturerPayment:
    db.add(payment)
    await db.flush()
    return payment


async def get_manufacturer_payment(
    db: AsyncSession, owner_id: uuid.UUID, payment_id: uuid.UUID
) -> ManufacturerPayment | None:
    stmt = select(ManufacturerPayment).where(ManufacturerPayment.id == payment_id, ManufacturerPayment.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_manufacturer_payment(db: AsyncSession, payment: ManufacturerPayment) -> None:
    await db.delete(payment)


async def list_manufacturer_payments_by_purchase(
    db: AsyncSession, owner_id: uuid.UUID, purchase_id: uuid.UUID
) -> list[ManufacturerPayment]:
    stmt = (
        select(ManufacturerPayment)
        .where(ManufacturerPayment.owner_id == owner_id, ManufacturerPayment.purchase_id == purchase_id)
        .order_by(ManufacturerPayment.payment_date.desc(), ManufacturerPayment.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_manufacturer_payments_by_manufacturer(
    db: AsyncSession, owner_id: uuid.UUID, manufacturer_id: uuid.UUID
) -> list[ManufacturerPayment]:
    stmt = (
        select(ManufacturerPayment)
        .where(ManufacturerPayment.owner_id == owner_id, ManufacturerPayment.manufacturer_id == manufacturer_id)
        .order_by(ManufacturerPayment.payment_date.desc(), ManufacturerPayment.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
