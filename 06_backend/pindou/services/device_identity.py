"""Signed anonymous device identity helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Response

from pindou.config import get_settings, secret_value
from pindou.db.models import as_aware_utc, utc_now

DEVICE_COOKIE_NAME = "pd_device"
DEVICE_HEADER_NAME = "X-PinDou-Device"
DEVICE_TOKEN_VERSION = "pdv1"
DEVICE_TOKEN_TTL_DAYS = 180


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    token: str
    expires_at: datetime
    issued_new: bool = False


def issue_device_identity(*, now: datetime | None = None) -> DeviceIdentity:
    timestamp = as_aware_utc(now) or utc_now()
    expires_at = timestamp + timedelta(days=DEVICE_TOKEN_TTL_DAYS)
    device_id = secrets.token_urlsafe(24)
    token = _pack_token(device_id=device_id, expires_at=expires_at)
    return DeviceIdentity(device_id=device_id, token=token, expires_at=expires_at, issued_new=True)


def parse_device_identity(raw_token: str | None, *, now: datetime | None = None) -> DeviceIdentity | None:
    token = (raw_token or "").strip()
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != DEVICE_TOKEN_VERSION:
        return None
    _, encoded_device_id, expires_text, signature = parts
    try:
        expires_ts = int(expires_text)
        device_id = _b64decode(encoded_device_id).decode("utf-8")
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    if not _is_valid_device_id(device_id):
        return None
    expected = _signature(encoded_device_id, expires_text)
    if not hmac.compare_digest(signature, expected):
        return None
    timestamp = as_aware_utc(now) or utc_now()
    expires_at = datetime.fromtimestamp(expires_ts, tz=timestamp.tzinfo)
    expires_at = as_aware_utc(expires_at) or expires_at
    if expires_at <= timestamp:
        return None
    return DeviceIdentity(device_id=device_id, token=token, expires_at=expires_at, issued_new=False)


def set_device_cookie(response: Response, identity: DeviceIdentity) -> None:
    settings = get_settings()
    max_age = max(0, int((identity.expires_at - utc_now()).total_seconds()))
    response.set_cookie(
        DEVICE_COOKIE_NAME,
        identity.token,
        max_age=max_age,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _pack_token(*, device_id: str, expires_at: datetime) -> str:
    encoded_device_id = _b64encode(device_id.encode("utf-8"))
    expires_text = str(int(expires_at.timestamp()))
    signature = _signature(encoded_device_id, expires_text)
    return f"{DEVICE_TOKEN_VERSION}.{encoded_device_id}.{expires_text}.{signature}"


def _signature(encoded_device_id: str, expires_text: str) -> str:
    payload = f"{DEVICE_TOKEN_VERSION}.{encoded_device_id}.{expires_text}".encode("utf-8")
    return _b64encode(hmac.new(_secret(), payload, hashlib.sha256).digest())


def _secret() -> bytes:
    settings = get_settings()
    value = secret_value(settings.device_token_secret) or secret_value(settings.jwt_secret)
    if not value:
        value = "pindou-dev-only-device-token-secret"
    return value.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _is_valid_device_id(value: str) -> bool:
    if not 16 <= len(value) <= 64:
        return False
    return all(ch.isalnum() or ch in {"-", "_"} for ch in value)
