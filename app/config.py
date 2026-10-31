from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="", case_sensitive=False, env_file=".env"
    )

    database_url: str = Field(min_length=1)
    jwt_secret: SecretStr = Field(min_length=32)
    app_base_url: str = Field(min_length=1)
    smtp_host: str = Field(min_length=1)
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = False
    smtp_sender: EmailStr
    secrets_dir: Path
    admin_email: EmailStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
