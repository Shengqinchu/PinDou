"""Email verification-code login backed by the shared application database."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import random
import re
from datetime import timedelta
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.api.errors import ApiException, ErrorCode
from pindou.config import get_settings
from pindou.db.models import EmailCode, as_aware_utc, utc_now
from pindou.services.rate_limit_service import RateLimitExceeded, RateLimitRule, consume_rate_limits


CODE_LENGTH = 6
CODE_EXPIRE_MINUTES = 5
CODE_RESEND_COOLDOWN_SECONDS = 60
MAX_VERIFY_ATTEMPTS = 5

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)

DISPOSABLE_EMAIL_DOMAINS = {
    "10mail.org",
    "10minmail.com",
    "10minutemail.com",
    "10minutemail.net",
    "dispostable.com",
    "emailfake.com",
    "emailondeck.com",
    "fakeinbox.com",
    "fakemailgenerator.com",
    "getnada.com",
    "grr.la",
    "guerrillamail.biz",
    "guerrillamail.com",
    "guerrillamail.info",
    "guerrillamail.net",
    "guerrillamail.org",
    "maildrop.cc",
    "mailinator.com",
    "mailinator.net",
    "mailinator.org",
    "mailnesia.com",
    "mailsac.com",
    "mohmal.com",
    "mohmal.im",
    "nada.email",
    "sharklasers.com",
    "temp.email",
    "temp-mail.org",
    "temp-mail.ru",
    "tempail.com",
    "tempmail.com",
    "tempmail.net",
    "tempmail.org",
    "throwaway.email",
    "throwawaymail.com",
    "trash-mail.com",
    "trashmail.com",
    "trashmail.net",
    "yopmail.com",
    "yopmail.fr",
    "yopmail.net",
}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email_or_raise(email: str) -> str:
    normalized = normalize_email(email)
    if not EMAIL_RE.fullmatch(normalized):
        raise ApiException(400, ErrorCode.VALIDATION_ERROR, "邮箱格式不正确，请检查后再试。")
    if is_disposable_email(normalized):
        raise ApiException(400, ErrorCode.VALIDATION_ERROR, "暂不支持一次性邮箱，请换一个常用邮箱。")
    return normalized


def is_disposable_email(email: str) -> bool:
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].lower().strip(".")
    try:
        from disposable_email_domains import blocklist  # type: ignore

        if domain in blocklist:
            return True
    except Exception:
        pass
    return domain in DISPOSABLE_EMAIL_DOMAINS or any(domain.endswith(f".{blocked}") for blocked in DISPOSABLE_EMAIL_DOMAINS)


def generate_verification_code() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(CODE_LENGTH))


class EmailVerificationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    async def send_code(self, *, email: str, request_ip: str | None = None) -> dict[str, Any]:
        normalized = validate_email_or_raise(email)
        now = utc_now()
        try:
            consume_rate_limits(
                self.session,
                [
                    RateLimitRule("email_send:ip:minute", request_ip, limit=5, window_seconds=60),
                    RateLimitRule("email_send:ip:day", request_ip, limit=30, window_seconds=24 * 60 * 60),
                    RateLimitRule("email_send:global:hour", "all", limit=300, window_seconds=60 * 60),
                ],
                now=now,
            )
        except RateLimitExceeded as exc:
            raise ApiException(
                429,
                "EMAIL_CODE_RATE_LIMITED",
                "验证码发送太频繁，请稍后再试。",
                {"retry_after_seconds": exc.retry_after_seconds},
            ) from exc
        existing = self.session.scalar(select(EmailCode).where(EmailCode.email == normalized))
        if existing is not None:
            sent_at = as_aware_utc(existing.sent_at)
            if sent_at and (now - sent_at).total_seconds() < CODE_RESEND_COOLDOWN_SECONDS:
                remaining = CODE_RESEND_COOLDOWN_SECONDS - int((now - sent_at).total_seconds())
                raise ApiException(
                    429,
                    "EMAIL_CODE_RATE_LIMITED",
                    f"验证码发送太频繁，请 {remaining} 秒后再试。",
                    {"retry_after_seconds": remaining},
                )

        code = generate_verification_code()
        expires_at = now + timedelta(minutes=CODE_EXPIRE_MINUTES)
        if existing is None:
            existing = EmailCode(email=normalized, code_hash=_hash_code(normalized, code), expires_at=expires_at)
            self.session.add(existing)
        else:
            existing.code_hash = _hash_code(normalized, code)
            existing.expires_at = expires_at
        existing.sent_at = now
        existing.attempts = 0
        existing.consumed_at = None
        existing.request_ip = request_ip
        self.session.commit()

        success, message = await send_verification_email(normalized, code)
        if not success:
            self.session.delete(existing)
            self.session.commit()
            raise ApiException(503, "EMAIL_SEND_FAILED", message or "验证码邮件发送失败，请稍后再试。")

        return {
            "success": True,
            "message": "验证码已发送到您的邮箱。",
            "cooldown_seconds": CODE_RESEND_COOLDOWN_SECONDS,
            "expires_in_seconds": CODE_EXPIRE_MINUTES * 60,
        }

    def verify_code(self, *, email: str, code: str) -> str:
        normalized = validate_email_or_raise(email)
        cleaned_code = code.strip()
        if not re.fullmatch(r"\d{6}", cleaned_code):
            raise ApiException(400, ErrorCode.VALIDATION_ERROR, "验证码应为 6 位数字。")

        record = self.session.scalar(select(EmailCode).where(EmailCode.email == normalized))
        now = utc_now()
        if record is None or record.consumed_at is not None:
            raise ApiException(400, "EMAIL_CODE_INVALID", "验证码不存在或已失效，请重新获取。")
        if as_aware_utc(record.expires_at) <= now:
            self.session.delete(record)
            self.session.commit()
            raise ApiException(400, "EMAIL_CODE_EXPIRED", "验证码已过期，请重新获取。")
        if record.attempts >= MAX_VERIFY_ATTEMPTS:
            self.session.delete(record)
            self.session.commit()
            raise ApiException(429, "EMAIL_CODE_ATTEMPTS_EXCEEDED", "验证码错误次数过多，请重新获取。")
        if not hmac.compare_digest(record.code_hash, _hash_code(normalized, cleaned_code)):
            record.attempts += 1
            self.session.commit()
            raise ApiException(400, "EMAIL_CODE_INVALID", "验证码不正确，请检查后再试。")

        record.consumed_at = now
        self.session.commit()
        return normalized


async def send_verification_email(email: str, code: str) -> tuple[bool, str]:
    return await asyncio.to_thread(_send_verification_email_sync, email, code)


def _send_verification_email_sync(email: str, code: str) -> tuple[bool, str]:
    settings = get_settings()
    api_key = settings.resend_api_key.get_secret_value() if settings.resend_api_key else ""
    if not api_key:
        return False, "邮件服务未配置，请稍后再试。"

    sender = f"{settings.sender_name} <{settings.sender_email}>"
    payload = {
        "from": sender,
        "to": [email],
        "subject": "PinDou 登录验证码",
        "html": _email_html(code),
        "text": f"您的 PinDou 登录验证码是 {code}，5 分钟内有效。如非本人操作，请忽略本邮件。",
    }
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        return False, "邮件服务暂时连接失败，请稍后再试。"

    if 200 <= response.status_code < 300:
        return True, "ok"
    return False, "验证码邮件发送失败，请稍后再试。"


def _hash_code(email: str, code: str) -> str:
    settings = get_settings()
    if settings.jwt_secret:
        secret = settings.jwt_secret.get_secret_value()
    elif settings.is_development:
        secret = "pindou-dev-email-code-secret"
    else:
        raise RuntimeError("JWT_SECRET must be configured outside development.")
    message = f"{email}:{code}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _email_html(code: str) -> str:
    return f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:0 auto;padding:28px;color:#1a1a1a;">
      <h2 style="margin:0 0 12px;">PinDou 登录验证码</h2>
      <p style="margin:0 0 18px;color:#555;">请输入下面的 6 位验证码完成登录或注册：</p>
      <div style="font-size:34px;font-weight:800;letter-spacing:8px;background:#fff1e8;border-radius:16px;padding:18px 22px;text-align:center;color:#ff6b5a;">
        {code}
      </div>
      <p style="margin:18px 0 0;color:#777;font-size:13px;">验证码 5 分钟内有效。如非本人操作，请忽略本邮件。</p>
    </div>
    """
