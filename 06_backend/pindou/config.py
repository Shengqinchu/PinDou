"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", validation_alias="APP_HOST")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")
    app_log_level: str = Field(default="info", validation_alias="APP_LOG_LEVEL")
    app_name: str = "PinDou API"
    app_cors_allow_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8000",
        validation_alias="APP_CORS_ALLOW_ORIGINS",
    )

    database_url: str = Field(default="sqlite:///./var/pindou.db", validation_alias="DATABASE_URL")
    data_dir: Path = Field(default=Path("./var/data"), validation_alias="PINDOU_DATA_DIR")
    upload_dir: Path = Field(default=Path("./var/data/uploads"), validation_alias="PINDOU_UPLOAD_DIR")
    preview_dir: Path = Field(default=Path("./var/data/previews"), validation_alias="PINDOU_PREVIEW_DIR")
    pattern_dir: Path = Field(default=Path("./var/data/patterns"), validation_alias="PINDOU_PATTERN_DIR")

    xiaochi_gpt_base_url: str = Field(
        default="https://gpt.xiaochisaascn.org/v1",
        validation_alias="XIAOCHI_GPT_BASE_URL",
    )
    xiaochi_gpt_api_key: SecretStr | None = Field(default=None, validation_alias="XIAOCHI_GPT_API_KEY")
    xiaochi_gpt_image_cost_cny: float = Field(default=0.0, validation_alias="XIAOCHI_GPT_IMAGE_COST_CNY")
    xiaochi_text_base_url: str = Field(
        default="https://api2.xiaochisaas.com",
        validation_alias="XIAOCHI_TEXT_BASE_URL",
    )
    xiaochi_text_api_key: SecretStr | None = Field(default=None, validation_alias="XIAOCHI_TEXT_API_KEY")

    wechat_mp_appid: str | None = Field(default=None, validation_alias="WECHAT_MP_APPID")
    wechat_mp_appsecret: SecretStr | None = Field(default=None, validation_alias="WECHAT_MP_APPSECRET")

    jwt_secret: SecretStr | None = Field(default=None, validation_alias="JWT_SECRET")
    admin_username: str | None = Field(default=None, validation_alias="ADMIN_USERNAME")
    admin_password_hash: SecretStr | None = Field(default=None, validation_alias="ADMIN_PASSWORD_HASH")

    reverse_proxy_health_url: str = Field(
        default="https://gpt.xiaochisaascn.org/v1/models",
        validation_alias="REVERSE_PROXY_HEALTH_URL",
    )
    reverse_proxy_check_interval_seconds: int = Field(
        default=300,
        validation_alias="REVERSE_PROXY_CHECK_INTERVAL_SECONDS",
    )
    reverse_proxy_alert_after_seconds: int = Field(
        default=21600,
        validation_alias="REVERSE_PROXY_ALERT_AFTER_SECONDS",
    )
    enable_reverse_proxy_health_monitor: bool = Field(
        default=True,
        validation_alias="ENABLE_REVERSE_PROXY_HEALTH_MONITOR",
    )

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"dev", "development", "local", "test"}

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
