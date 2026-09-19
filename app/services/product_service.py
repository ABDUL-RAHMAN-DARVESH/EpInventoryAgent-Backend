import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.product import Product
from app.repositories import product as product_repo
from app.schemas.product import ProductCreate, ProductUpdate


async def create_product(db: AsyncSession, owner_id: uuid.UUID, data: ProductCreate) -> Product:
    existing = await product_repo.get_by_sku(db, owner_id, data.sku)
    if existing is not None:
        raise ConflictError(f"Product with SKU '{data.sku}' already exists")
    product = Product(owner_id=owner_id, **data.model_dump())
    product = await product_repo.create(db, product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_product(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    product = await product_repo.get(db, owner_id, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    return product


async def list_products(
    db: AsyncSession, owner_id: uuid.UUID, *, is_active: bool | None = None, skip: int = 0, limit: int = 100
) -> list[Product]:
    return await product_repo.list_all(db, owner_id=owner_id, is_active=is_active, skip=skip, limit=limit)


async def update_product(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID, data: ProductUpdate) -> Product:
    product = await get_product(db, owner_id, product_id)
    updates = data.model_dump(exclude_unset=True)
    if "sku" in updates and updates["sku"] != product.sku:
        existing = await product_repo.get_by_sku(db, owner_id, updates["sku"])
        if existing is not None:
            raise ConflictError(f"Product with SKU '{updates['sku']}' already exists")
    for field, value in updates.items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


async def deactivate_product(db: AsyncSession, owner_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    product = await get_product(db, owner_id, product_id)
    product.is_active = False
    await db.commit()
    await db.refresh(product)
    return product
