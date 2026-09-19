"""
Coverage for the startup guard that refuses to run with the dev-only
SECRET_KEY default outside local development (app/core/config.py).
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_refuses_insecure_default_secret_key_outside_local():
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="dev-only-insecure-secret-key-change-me")


def test_allows_insecure_default_secret_key_in_local():
    settings = Settings(app_env="local", secret_key="dev-only-insecure-secret-key-change-me")
    assert settings.secret_key == "dev-only-insecure-secret-key-change-me"


def test_allows_a_real_secret_key_outside_local():
    settings = Settings(app_env="production", secret_key="a-real-randomly-generated-secret")
    assert settings.secret_key == "a-real-randomly-generated-secret"
