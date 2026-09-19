import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.product import Product
from app.repositories import product as product_repo
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate


def _to_read(product: Product, stats: dict[uuid.UUID, dict[str, int]]) -> ProductRead:
    s = stats.get(product.id, {"purchased": 0, "sold": 0})
    return ProductRead(
        id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        total_purchased=s["purchased"],
        total_sold=s["sold"],
        available_quantity=s["purchased"] - s["sold"],
    )


async def _get_or_404(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    product = await product_repo.get(db, owner_id, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    return product


async def create_product(db: AsyncSession, owner_id: uuid.UUID, data: ProductCreate) -> ProductRead:
    product = Product(owner_id=owner_id, **data.model_dump())
    product = await product_repo.create(db, product)
    await db.commit()
    await db.refresh(product)
    return _to_read(product, {})  # brand new -- no purchase/sale history yet


async def get_product(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID) -> ProductRead:
    product = await _get_or_404(db, owner_id, product_id)
    stats = await product_repo.get_quantity_stats(db, [product_id])
    return _to_read(product, stats)


async def list_products(
    db: AsyncSession, owner_id: uuid.UUID, *, is_active: bool | None = None, skip: int = 0, limit: int = 100
) -> list[ProductRead]:
    products = await product_repo.list_all(db, owner_id=owner_id, is_active=is_active, skip=skip, limit=limit)
    stats = await product_repo.get_quantity_stats(db, [p.id for p in products])
    return [_to_read(p, stats) for p in products]


async def update_product(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID, data: ProductUpdate) -> ProductRead:
    product = await _get_or_404(db, owner_id, product_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    stats = await product_repo.get_quantity_stats(db, [product_id])
    return _to_read(product, stats)


async def delete_product(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID) -> None:
    product = await _get_or_404(db, owner_id, product_id)
    if await product_repo.is_referenced(db, product_id):
        raise ConflictError(f"'{product.name}' has sales or purchase history and cannot be deleted.")
    await product_repo.delete(db, product)
    await db.commit()
