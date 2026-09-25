from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Робо&Ты API"
    environment: str = "development"
    database_url: str = "sqlite:///./robo.db"
    secret_key: str = "development-only-change-me-at-least-32-chars"
    access_token_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    demo_user_email: str = "demo@robo.local"
    demo_user_password: str = "Demo-2026!"
    demo_admin_email: str = "admin@robo.local"
    demo_admin_password: str = "Admin-2026!"
    seed_dir: Path = Path(__file__).resolve().parents[2] / "data" / "seed"

    plan_storage_dir: Path = Path(__file__).resolve().parents[2] / "storage" / "plan-assets"
    max_plan_asset_bytes: int = 16 * 1024 * 1024
    yytsi_provider_url: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment.lower() == "production":
            insecure_defaults = {
                "development-only-change-me-at-least-32-chars",
                "replace-before-production-at-least-32-characters",
            }
            if len(self.secret_key) < 32 or self.secret_key in insecure_defaults:
                raise ValueError(
                    "В production SECRET_KEY должен быть случайным и не короче 32 символов"
                )
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
