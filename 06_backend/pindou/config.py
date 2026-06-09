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
    max_request_body_bytes: int = Field(default=12 * 1024 * 1024, validation_alias="MAX_REQUEST_BODY_BYTES")
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
    thumbnail_dir: Path = Field(default=Path("./var/data/thumbnails"), validation_alias="PINDOU_THUMBNAIL_DIR")
    storage_backend: str = Field(default="local", validation_alias="STORAGE_BACKEND")
    cos_secret_id: SecretStr | None = Field(default=None, validation_alias="COS_SECRET_ID")
    cos_secret_key: SecretStr | None = Field(default=None, validation_alias="COS_SECRET_KEY")
    cos_bucket: str | None = Field(default=None, validation_alias="COS_BUCKET")
    cos_region: str | None = Field(default=None, validation_alias="COS_REGION")
    cos_public_base_url: str | None = Field(default=None, validation_alias="COS_PUBLIC_BASE_URL")

    xiaochi_gpt_base_url: str = Field(
        default="https://gpt.xiaochisaascn.org/v1",
        validation_alias="XIAOCHI_GPT_BASE_URL",
    )
    xiaochi_gpt_api_key: SecretStr | None = Field(default=None, validation_alias="XIAOCHI_GPT_API_KEY")
    xiaochi_gpt_image_cost_cny: float = Field(default=0.0, validation_alias="XIAOCHI_GPT_IMAGE_COST_CNY")
    xiaochi_gpt_prompt_variant: str = Field(default="prompt_a_current", validation_alias="XIAOCHI_GPT_PROMPT_VARIANT")
    enable_ai_preview_white_bg_auto_nobead: bool = Field(
        default=True,
        validation_alias="ENABLE_AI_PREVIEW_WHITE_BG_AUTO_NOBEED",
    )
    xiaochi_text_base_url: str = Field(
        default="https://api2.xiaochisaas.com",
        validation_alias="XIAOCHI_TEXT_BASE_URL",
    )
    xiaochi_text_api_key: SecretStr | None = Field(default=None, validation_alias="XIAOCHI_TEXT_API_KEY")

    wechat_mp_appid: str | None = Field(default=None, validation_alias="WECHAT_MP_APPID")
    wechat_mp_appsecret: SecretStr | None = Field(default=None, validation_alias="WECHAT_MP_APPSECRET")
    resend_api_key: SecretStr | None = Field(default=None, validation_alias="RESEND_API_KEY")
    sender_email: str = Field(default="noreply@pindoupuppy.com", validation_alias="SENDER_EMAIL")
    sender_name: str = Field(default="PinDou 拼豆", validation_alias="SENDER_NAME")
    unlimited_credit_emails: str = Field(default="", validation_alias="UNLIMITED_CREDIT_EMAILS")

    jwt_secret: SecretStr | None = Field(default=None, validation_alias="JWT_SECRET")
    device_token_secret: SecretStr | None = Field(default=None, validation_alias="DEVICE_TOKEN_SECRET")
    admin_username: str | None = Field(default=None, validation_alias="ADMIN_USERNAME")
    admin_password_hash: SecretStr | None = Field(default=None, validation_alias="ADMIN_PASSWORD_HASH")
    customer_service_qr_url: str = Field(
        default="/static/assets/qr-placeholder.svg",
        validation_alias="CUSTOMER_SERVICE_QR_URL",
    )
    customer_service_wx_id: str = Field(default="pindou_cs_01", validation_alias="CUSTOMER_SERVICE_WX_ID")
    hupijiao_app_id: str | None = Field(default=None, validation_alias="HUPIJIAO_APP_ID")
    hupijiao_app_secret: SecretStr | None = Field(default=None, validation_alias="HUPIJIAO_APP_SECRET")
    hupijiao_webhook_secret: SecretStr | None = Field(default=None, validation_alias="HUPIJIAO_WEBHOOK_SECRET")
    hupijiao_callback_url: str = Field(
        default="http://192.168.2.40:8000/api/v1/webhook/hupijiao",
        validation_alias="HUPIJIAO_CALLBACK_URL",
    )
    hupijiao_api_base_url: str = Field(
        default="https://api.xunhupay.com",
        validation_alias="HUPIJIAO_API_BASE_URL",
    )

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
    expired_original_retention_days: int = Field(
        default=30,
        validation_alias="EXPIRED_ORIGINAL_RETENTION_DAYS",
    )
    expired_original_delete_interval_seconds: int = Field(
        default=86400,
        validation_alias="EXPIRED_ORIGINAL_DELETE_INTERVAL_SECONDS",
    )
    enable_expired_original_delete_task: bool = Field(
        default=True,
        validation_alias="ENABLE_EXPIRED_ORIGINAL_DELETE_TASK",
    )

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"dev", "development", "local", "test"}

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_allow_origins.split(",") if origin.strip()]

    @property
    def unlimited_credit_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.unlimited_credit_emails.split(",")
            if email.strip()
        }

    def validate_production_ready(self) -> None:
        if not self.is_production:
            return

        errors: list[str] = []
        jwt_secret = secret_value(self.jwt_secret)
        if not jwt_secret or jwt_secret in {"pindou-dev-only-jwt-secret", "pindou-dev-email-code-secret"}:
            errors.append("JWT_SECRET must be configured to a strong production value.")
        elif len(jwt_secret) < 32:
            errors.append("JWT_SECRET must be at least 32 characters.")
        device_secret = secret_value(self.device_token_secret)
        if device_secret is not None and len(device_secret) < 32:
            errors.append("DEVICE_TOKEN_SECRET must be at least 32 characters when configured.")

        origins = self.cors_allow_origins
        if not origins:
            errors.append("APP_CORS_ALLOW_ORIGINS must include the production web origin.")
        for origin in origins:
            lowered = origin.lower()
            if lowered == "*" or "localhost" in lowered or "127.0.0.1" in lowered:
                errors.append("APP_CORS_ALLOW_ORIGINS must not include wildcard or local origins in production.")
            if not lowered.startswith("https://"):
                errors.append("APP_CORS_ALLOW_ORIGINS must use HTTPS origins in production.")

        if self.storage_backend.lower() == "cos":
            if not (self.cos_secret_id and self.cos_secret_key and self.cos_bucket and self.cos_region):
                errors.append("COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, and COS_REGION are required for COS storage.")

        if not secret_value(self.xiaochi_gpt_api_key):
            errors.append("XIAOCHI_GPT_API_KEY must be configured for production AI mode.")
        if not secret_value(self.resend_api_key):
            errors.append("RESEND_API_KEY must be configured for production email login.")
        if not self.admin_username or not secret_value(self.admin_password_hash):
            errors.append("ADMIN_USERNAME and ADMIN_PASSWORD_HASH must be configured in production.")

        if not self.hupijiao_app_id or not secret_value(self.hupijiao_app_secret) or not secret_value(
            self.hupijiao_webhook_secret
        ):
            errors.append("HUPIJIAO_APP_ID, HUPIJIAO_APP_SECRET, and HUPIJIAO_WEBHOOK_SECRET are required.")
        callback_url = self.hupijiao_callback_url.strip().lower()
        if not callback_url.startswith("https://"):
            errors.append("HUPIJIAO_CALLBACK_URL must be an HTTPS public URL in production.")
        if "192.168." in callback_url or "localhost" in callback_url or "127.0.0.1" in callback_url:
            errors.append("HUPIJIAO_CALLBACK_URL must not point to a local or private address in production.")

        if errors:
            joined = "; ".join(dict.fromkeys(errors))
            raise RuntimeError(f"Production configuration is not safe to start: {joined}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def secret_value(secret: SecretStr | None) -> str | None:
    return secret.get_secret_value() if secret else None
