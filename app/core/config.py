from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_EXPIRE_MIN: int = 15
    REFRESH_EXPIRE_DAYS: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"

    PENDING_REG_TTL_SEC: int = 60 * 10
    REG_RESEND_COOLDOWN_SEC: int = 60
    VERIFY_MAX_ATTEMPTS: int = 5
    CODE_PEPPER: str = Field(..., min_length=16)

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@outfit.local"
    SMTP_TLS: bool = False

    MAIL_STREAM: str = "mail:outbox"
    MAIL_GROUP: str = "mail-workers"
    MAIL_CONSUMER: str = "worker-1"

    DEBUG: bool = False
    SERVICE_NAME: str = "auth-service"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
