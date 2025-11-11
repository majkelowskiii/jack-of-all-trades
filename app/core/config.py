"""Application configuration objects."""

from __future__ import annotations

import os


class BaseConfig:
    """Base configuration shared across environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = True
    CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")


class DevelopmentConfig(BaseConfig):
    """Config for local development."""

    DEBUG = True


class ProductionConfig(BaseConfig):
    """Config for production deployments."""

    DEBUG = False


__all__ = ["BaseConfig", "DevelopmentConfig", "ProductionConfig"]
