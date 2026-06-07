"""Small HS256 JWT helper without adding a runtime dependency."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta
from typing import Any

from pindou.config import get_settings


class TokenError(ValueError):
    pass


def create_access_token(
    *,
    subject: str,
    is_admin: bool = False,
    role: str | None = None,
    expires_delta: timedelta = timedelta(days=30),
) -> str:
    now = int(time.time())
    token_role = role or ("admin" if is_admin else "user")
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + int(expires_delta.total_seconds()),
        "admin": bool(is_admin or token_role == "admin"),
        "role": token_role,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join([_b64json(header), _b64json(payload)])
    signature = _sign(signing_input)
    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_raw, payload_raw, signature = token.split(".", 2)
    except ValueError as exc:
        raise TokenError("Malformed token.") from exc

    signing_input = f"{header_raw}.{payload_raw}"
    expected_signature = _sign(signing_input)
    if not hmac.compare_digest(signature, expected_signature):
        raise TokenError("Invalid token signature.")

    payload = _b64json_decode(payload_raw)
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("Token has expired.")
    return payload


def password_matches(password: str, configured_hash: str | None) -> bool:
    if not configured_hash:
        return False
    if configured_hash.startswith("sha256:"):
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(configured_hash.removeprefix("sha256:"), digest)
    return hmac.compare_digest(configured_hash, password)


def admin_credentials_match(username: str, password: str) -> bool:
    settings = get_settings()
    configured_hash = settings.admin_password_hash.get_secret_value() if settings.admin_password_hash else None
    if settings.admin_username and configured_hash:
        return username == settings.admin_username and password_matches(password, configured_hash)
    if settings.is_development:
        return username == "admin" and password == "admin"
    return False


def admin_credentials_diagnostics(username: str, password: str) -> dict[str, Any]:
    """Return non-secret booleans for diagnosing admin login configuration."""
    settings = get_settings()
    configured_username = settings.admin_username or ""
    configured_hash = settings.admin_password_hash.get_secret_value() if settings.admin_password_hash else ""
    trimmed_hash = configured_hash.strip()
    return {
        "app_env": settings.app_env,
        "admin_username_configured": bool(configured_username),
        "admin_password_hash_configured": bool(configured_hash),
        "admin_username_matches": bool(configured_username and username == configured_username),
        "admin_username_trim_matches": bool(configured_username and username.strip() == configured_username.strip()),
        "admin_username_has_surrounding_space": bool(configured_username and configured_username != configured_username.strip()),
        "password_hash_has_sha256_prefix": configured_hash.startswith("sha256:"),
        "password_hash_length": len(configured_hash) if configured_hash else 0,
        "password_hash_trim_changes": configured_hash != trimmed_hash,
        "password_matches": bool(configured_hash and password_matches(password, configured_hash)),
        "password_matches_trimmed_hash": bool(trimmed_hash and password_matches(password, trimmed_hash)),
    }


def _secret() -> bytes:
    settings = get_settings()
    if settings.jwt_secret:
        secret = settings.jwt_secret.get_secret_value()
    elif settings.is_development:
        secret = "pindou-dev-only-jwt-secret"
    else:
        raise RuntimeError("JWT_SECRET must be configured outside development.")
    return secret.encode("utf-8")


def _sign(signing_input: str) -> str:
    digest = hmac.new(_secret(), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return _b64(digest)


def _b64json(value: dict[str, Any]) -> str:
    return _b64(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64json_decode(value: str) -> dict[str, Any]:
    padded = value + "=" * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
