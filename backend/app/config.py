"""Application configuration loaded from environment variables."""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def parse_origins(raw: str) -> list[str]:
    """Split a comma-separated origin list, trimming whitespace and trailing slashes.

    A browser's Origin header never ends in "/", so a configured
    "https://example.app/" would never match and every request would fail CORS.
    """
    origins = []
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if origin:
            origins.append(origin)
    return origins


class Config:
    # Core
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///tender_hands_dev.db"
    )
    # Heroku/Vercel Postgres gives postgres://, SQLAlchemy 1.4+ needs postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    # Pin the driver to psycopg2, the package listed in requirements.txt.
    # SQLAlchemy 2.0.36+ resolves a bare "postgresql://" to psycopg 3, which
    # is not installed and fails at import time with ModuleNotFoundError.
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # CORS – comma-separated list of allowed origins
    CORS_ORIGINS = parse_origins(
        os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    )

    # M-Pesa (Daraja)
    MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "174379")  # sandbox default
    MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.environ.get(
        "MPESA_CALLBACK_URL", "https://your-domain.com/api/mpesa/callback"
    )
    MPESA_ENV = os.environ.get("MPESA_ENV", "sandbox")  # "sandbox" | "production"
    # Class-demo switch: record a donation as paid without contacting Safaricom.
    # Off unless explicitly enabled; every demo donation is labelled as such.
    MPESA_DEMO_MODE = os.environ.get("MPESA_DEMO_MODE", "").lower() in (
        "1",
        "true",
        "yes",
    )

    # Shared secret for the external scheduler that triggers POST /api/recurring/run-due
    CRON_SECRET = os.environ.get("CRON_SECRET", "")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    # Tests must never take the demo shortcut, whatever the developer's .env says.
    MPESA_DEMO_MODE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    pass


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
