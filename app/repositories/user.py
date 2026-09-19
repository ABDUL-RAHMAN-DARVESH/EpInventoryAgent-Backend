import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.flush()
    return user


async def get(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
