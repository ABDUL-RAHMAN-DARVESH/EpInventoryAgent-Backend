from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_version import AppVersionConfig
from app.repositories import app_version as app_version_repo
from app.schemas.app_version import AppVersionUpdate, VersionCheckResponse


def _parse_version(version: str) -> tuple[int, ...]:
    """Best-effort dotted-version parse -- "1.2.0" -> (1, 2, 0). Any non-numeric
    suffix on a segment (e.g. "1.2.0-beta") is stripped rather than rejected,
    since this only needs to support simple ordering, not full semver."""
    parts = []
    for chunk in version.strip().split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def _is_older(a: str, b: str) -> bool:
    """True if version `a` is strictly older than version `b`."""
    ta, tb = _parse_version(a), _parse_version(b)
    length = max(len(ta), len(tb))
    ta = ta + (0,) * (length - len(ta))
    tb = tb + (0,) * (length - len(tb))
    return ta < tb


async def get_config(db: AsyncSession, platform: str) -> AppVersionConfig | None:
    return await app_version_repo.get_by_platform(db, platform)


async def list_configs(db: AsyncSession) -> list[AppVersionConfig]:
    return await app_version_repo.list_all(db)


async def upsert_config(db: AsyncSession, platform: str, data: AppVersionUpdate) -> AppVersionConfig:
    config = await app_version_repo.get_by_platform(db, platform)
    if config is None:
        config = AppVersionConfig(platform=platform, latest_version=data.latest_version, minimum_version=data.minimum_version)
        await app_version_repo.create(db, config)
    else:
        config.latest_version = data.latest_version
        config.minimum_version = data.minimum_version
    await db.commit()
    await db.refresh(config)
    return config


async def check_version(db: AsyncSession, platform: str, installed_version: str) -> VersionCheckResponse:
    config = await app_version_repo.get_by_platform(db, platform)
    if config is None:
        # No version policy configured for this platform yet -- never block the app.
        return VersionCheckResponse(
            platform=platform,
            installed_version=installed_version,
            latest_version=installed_version,
            minimum_version=installed_version,
            update_available=False,
            force_update=False,
        )

    return VersionCheckResponse(
        platform=platform,
        installed_version=installed_version,
        latest_version=config.latest_version,
        minimum_version=config.minimum_version,
        update_available=_is_older(installed_version, config.latest_version),
        force_update=_is_older(installed_version, config.minimum_version),
    )
