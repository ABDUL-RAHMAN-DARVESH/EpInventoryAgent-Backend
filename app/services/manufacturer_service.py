import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.exceptions import NotFoundError
from app.models.manufacturer import Manufacturer
from app.repositories import manufacturer as manufacturer_repo
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerUpdate


async def create_manufacturer(db: AsyncSession, owner_id: uuid.UUID, data: ManufacturerCreate) -> Manufacturer:
    manufacturer = Manufacturer(owner_id=owner_id, **data.model_dump())
    manufacturer = await manufacturer_repo.create(db, manufacturer)
    await db.commit()
    await db.refresh(manufacturer)
    return manufacturer


async def get_manufacturer(db: AsyncSession, owner_id: uuid.UUID, manufacturer_id: uuid.UUID) -> Manufacturer:
    manufacturer = await manufacturer_repo.get(db, owner_id, manufacturer_id)
    if manufacturer is None:
        raise NotFoundError(f"Manufacturer {manufacturer_id} not found")
    return manufacturer


async def list_manufacturers(
    db: AsyncSession, owner_id: uuid.UUID, *, is_active: bool | None = None, skip: int = 0, limit: int = 100
) -> list[Manufacturer]:
    return await manufacturer_repo.list_all(db, owner_id=owner_id, is_active=is_active, skip=skip, limit=limit)


async def update_manufacturer(
    db: AsyncSession, owner_id: uuid.UUID, manufacturer_id: uuid.UUID, data: ManufacturerUpdate
) -> Manufacturer:
    manufacturer = await get_manufacturer(db, owner_id, manufacturer_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(manufacturer, field, value)
    await db.commit()
    await db.refresh(manufacturer)
    return manufacturer


async def deactivate_manufacturer(db: AsyncSession, owner_id: uuid.UUID, manufacturer_id: uuid.UUID) -> Manufacturer:
    manufacturer = await get_manufacturer(db, owner_id, manufacturer_id)
    manufacturer.is_active = False
    await db.commit()
    await db.refresh(manufacturer)
    return manufacturer


async def upload_manufacturer_image(
    db: AsyncSession, owner_id: uuid.UUID, manufacturer_id: uuid.UUID, file_bytes: bytes, content_type: str
) -> Manufacturer:
    manufacturer = await get_manufacturer(db, owner_id, manufacturer_id)
    ext = storage.extension_for(content_type)
    manufacturer.image_url = await storage.upload_image(
        file_bytes, content_type, f"manufacturers/{owner_id}/{manufacturer_id}.{ext}"
    )
    await db.commit()
    await db.refresh(manufacturer)
    return manufacturer
