import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories import feature as feature_repo
from app.repositories import user as user_repo
from app.schemas.feature import FeatureRead
from app.schemas.user import FeatureFlag, UserCreate, UserUpdate


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await user_repo.get_by_email(db, data.email)
    if existing is not None:
        raise ConflictError(f"A user with email {data.email} already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        expires_at=data.expires_at,
    )
    user = await user_repo.create(db, user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await user_repo.get(db, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


async def list_users(db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[User]:
    return await user_repo.list_all(db, skip=skip, limit=limit)


async def update_user(db: AsyncSession, user_id: uuid.UUID, data: UserUpdate) -> User:
    """Admin-only. `expires_at` follows normal PATCH-semantics: omit it to leave
    unchanged, send `null` to clear it, send a date to set/extend it. `password`
    (if present) resets the account's password -- this is the only way to
    rotate one, including the bootstrap admin's known default."""
    user = await get_user(db, user_id)
    updates = data.model_dump(exclude_unset=True)
    new_password = updates.pop("password", None)
    for field, value in updates.items():
        setattr(user, field, value)
    if new_password:
        user.hashed_password = hash_password(new_password)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_features(db: AsyncSession, user_id: uuid.UUID) -> list[FeatureFlag]:
    all_features = await feature_repo.list_all(db)
    links = await feature_repo.list_for_user(db, user_id)
    enabled_by_feature_id = {link.feature_id: link.enabled for link in links}
    return [
        FeatureFlag(key=f.key, name=f.name, enabled=enabled_by_feature_id.get(f.id, False))
        for f in all_features
    ]


async def set_user_feature(db: AsyncSession, user_id: uuid.UUID, feature_key: str, enabled: bool) -> FeatureRead:
    await get_user(db, user_id)  # 404 if the user doesn't exist
    feature = await feature_repo.get_by_key(db, feature_key)
    if feature is None:
        raise NotFoundError(f"Feature '{feature_key}' not found")
    await feature_repo.upsert_user_feature(db, user_id, feature.id, enabled)
    await db.commit()
    return FeatureRead.model_validate(feature)
