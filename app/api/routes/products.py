import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
async def create_product(
    data: ProductCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await product_service.create_product(db, current_user.id, data)


@router.get("", response_model=list[ProductRead])
async def list_products(
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.list_products(db, current_user.id, is_active=is_active, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await product_service.get_product(db, current_user.id, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.update_product(db, current_user.id, product_id, data)


@router.delete("/{product_id}", response_model=ProductRead)
async def deactivate_product(
    product_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await product_service.deactivate_product(db, current_user.id, product_id)
