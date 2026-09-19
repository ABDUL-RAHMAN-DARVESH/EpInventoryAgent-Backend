from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Must match the default below exactly -- this is what the startup check
# refuses to run with outside local development.
_INSECURE_DEFAULT_SECRET_KEY = "dev-only-insecure-secret-key-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PayBook"
    app_env: str = "local"
    debug: bool = True

    database_url: str = "postgresql+psycopg://inventory_agent:inventory_agent@localhost:5432/inventory_agent"

    cors_origins: str = "*"

    # Dev-only default -- MUST be overridden via the SECRET_KEY env var in any
    # environment other than local development (JWTs are only as secure as this key).
    secret_key: str = _INSECURE_DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = 60 * 24  # 24h
    refresh_token_expire_days: int = 30

    # Supabase Storage, for customer/manufacturer/shop images (see
    # app/core/storage.py). Only required once an image-upload endpoint is
    # actually called -- absent locally until image features are exercised.
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    supabase_storage_bucket: str = "app-images"

    @model_validator(mode="after")
    def _refuse_insecure_secret_outside_local(self) -> "Settings":
        if self.app_env != "local" and self.secret_key == _INSECURE_DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY is still set to the dev-only default while APP_ENV="
                f"'{self.app_env}'. Set a real SECRET_KEY env var before starting "
                "the app outside local development (e.g. `python -c \"import secrets; "
                "print(secrets.token_urlsafe(64))\"`)."
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
