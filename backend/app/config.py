"""Application configuration.

Settings are loaded from environment variables (optionally via a local `.env`
file).  This keeps secrets out of source control while still allowing a
zero-config local development experience via sensible defaults.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Inventory & Order Management System."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    app_name: str = "Inventory & Order Management System"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # --- Database ----------------------------------------------------------
    # Defaults to a local SQLite file so tests and quick starts need no server.
    # In production/docker-compose this is overridden with a PostgreSQL URL,
    # e.g. postgresql+psycopg://user:pass@db:5432/inventory
    database_url: str = Field(default="sqlite:///./inventory.db")

    # --- Security ----------------------------------------------------------
    secret_key: str = Field(default="change-me-in-production")
    access_token_expire_minutes: int = Field(default=60 * 12)
    algorithm: str = Field(default="HS256")

    # --- CORS --------------------------------------------------------------
    # Comma-separated list of allowed origins.
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://localhost:8080"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated origins into a clean list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- Business rules ----------------------------------------------------
    low_stock_threshold_default: int = Field(default=10)
    currency: str = Field(default="INR")
    tax_rate: float = Field(default=0.0)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()


settings = get_settings()
