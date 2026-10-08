"""Settings read from environment variables. Secrets never live in code."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env during local development; no-op on Render


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_expire_minutes: int
    cors_origins: list[str]
    app_env: str

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
    if "*" in origins:
        raise RuntimeError("CORS_ORIGINS must list exact origins, never '*'")

    secret = _require("JWT_SECRET")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")

    return Settings(
        database_url=_require("DATABASE_URL"),
        jwt_secret=secret,
        jwt_expire_minutes=int(os.environ.get("JWT_EXPIRE_MINUTES", "30")),
        cors_origins=origins,
        app_env=os.environ.get("APP_ENV", "development"),
    )


settings = load_settings()
