import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationAppError

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_MAX_BYTES = 5 * 1024 * 1024  # 5MB


def extension_for(content_type: str) -> str:
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValidationAppError(
            f"Unsupported image type '{content_type}'. Allowed: {', '.join(_ALLOWED_CONTENT_TYPES)}."
        )
    return _ALLOWED_CONTENT_TYPES[content_type]


async def upload_image(file_bytes: bytes, content_type: str, path: str) -> str:
    """Uploads to Supabase Storage and returns the object's public URL.

    `path` is the full object key within the bucket (e.g.
    "customers/<owner_id>/<customer_id>.jpg") -- callers own path uniqueness.
    `x-upsert: true` lets re-uploading for the same entity simply overwrite
    the previous image instead of erroring on conflict.
    """
    extension_for(content_type)  # raises before validating size, on the cheaper check first
    if len(file_bytes) > _MAX_BYTES:
        raise ValidationAppError(f"Image is too large (max {_MAX_BYTES // (1024 * 1024)}MB).")

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValidationAppError(
            "Image storage is not configured on this server (SUPABASE_URL / SUPABASE_SERVICE_KEY missing)."
        )

    upload_url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(
            upload_url,
            content=file_bytes,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
    if response.status_code >= 400:
        raise ValidationAppError(f"Image upload failed: {response.text}")

    return f"{settings.supabase_url}/storage/v1/object/public/{settings.supabase_storage_bucket}/{path}"
