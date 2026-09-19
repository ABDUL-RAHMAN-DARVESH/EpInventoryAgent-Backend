import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.purchase import PurchaseItem
from app.models.sale import SaleItem


async def create(db: AsyncSession, product: Product) -> Product:
    db.add(product)
    await db.flush()
    return product


async def get(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID) -> Product | None:
    stmt = select(Product).where(Product.id == product_id, Product.owner_id == owner_id)
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


async def is_referenced(db: AsyncSession, product_id: uuid.UUID) -> bool:
    """True if this product appears in any sale or purchase -- such a product
    can never be hard-deleted (sale_items/purchase_items.product_id is
    ON DELETE RESTRICT) without destroying that transaction's history."""
    in_a_sale = await db.scalar(select(SaleItem.id).where(SaleItem.product_id == product_id).limit(1))
    if in_a_sale is not None:
        return True
    in_a_purchase = await db.scalar(select(PurchaseItem.id).where(PurchaseItem.product_id == product_id).limit(1))
    return in_a_purchase is not None


async def delete(db: AsyncSession, product: Product) -> None:
    await db.delete(product)


async def get_quantity_stats(db: AsyncSession, product_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    """Total purchased/sold quantity per product, derived live from purchase/
    sale line items -- not a stored counter, so it can never drift out of
    sync with the actual transaction history. `product_ids` is expected to
    already be scoped to the caller's own products (see product_service.py),
    so no owner filter is needed here."""
    stats = {pid: {"purchased": 0, "sold": 0} for pid in product_ids}
    if not product_ids:
        return stats

    purchased_rows = (
        await db.execute(
            select(PurchaseItem.product_id, func.sum(PurchaseItem.quantity))
            .where(PurchaseItem.product_id.in_(product_ids))
            .group_by(PurchaseItem.product_id)
        )
    ).all()
    for product_id, total in purchased_rows:
        stats[product_id]["purchased"] = int(total)

    sold_rows = (
        await db.execute(
            select(SaleItem.product_id, func.sum(SaleItem.quantity))
            .where(SaleItem.product_id.in_(product_ids))
            .group_by(SaleItem.product_id)
        )
    ).all()
    for product_id, total in sold_rows:
        stats[product_id]["sold"] = int(total)

    return stats
