"""Hupijiao (Xunhupay) payment API client."""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

import requests


PAYMENT_PATH = "/payment/do.html"
QUERY_PATH = "/payment/query.html"
HUPIJIAO_SUCCESS = {0, "0"}
HUPIJIAO_PAID_STATUS = "OD"
HUPIJIAO_PENDING_STATUS = "WP"
HUPIJIAO_CANCELLED_STATUS = "CD"


class HupijiaoError(RuntimeError):
    """Base exception for Hupijiao integration errors."""


class HupijiaoAPIError(HupijiaoError):
    """Raised when Hupijiao returns an API-level error."""


class HupijiaoSignatureError(HupijiaoError):
    """Raised when a Hupijiao response or webhook fails signature verification."""


@dataclass(frozen=True)
class HupijiaoOrderResult:
    order_no: str
    qr_code_url: str
    payment_url: str
    expires_at: datetime
    raw: dict[str, Any]
    is_mock: bool = False


@dataclass(frozen=True)
class HupijiaoQueryResult:
    order_no: str
    status: str
    paid_at: datetime | None
    raw: dict[str, Any]


def sign_params(params: Mapping[str, Any], app_secret: str) -> str:
    """Return Hupijiao MD5 hash for non-empty params sorted by ASCII key."""
    filtered: dict[str, str] = {}
    for key, value in params.items():
        if key == "hash" or value is None or value == "":
            continue
        filtered[str(key)] = str(value)
    signing_text = "&".join(f"{key}={filtered[key]}" for key in sorted(filtered)) + app_secret
    return hashlib.md5(signing_text.encode("utf-8")).hexdigest().lower()


def verify_signature(params: Mapping[str, Any], app_secret: str) -> bool:
    received = str(params.get("hash") or "").lower()
    if not received:
        return False
    return secrets.compare_digest(received, sign_params(params, app_secret))


def normalize_amount(amount: Decimal | float | str) -> str:
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(value, "f")


def generate_nonce() -> str:
    return secrets.token_hex(16)


class HupijiaoService:
    def __init__(
        self,
        *,
        app_id: str | None,
        app_secret: str | None,
        api_base_url: str = "https://api.xunhupay.com",
        webhook_secret: str | None = None,
        timeout_seconds: float = 30.0,
        session: Any | None = None,
        dev_qr_url: str = "/static/assets/qr-placeholder.svg",
    ) -> None:
        self.app_id = (app_id or "").strip()
        self.app_secret = (app_secret or "").strip()
        self.webhook_secret = (webhook_secret or "").strip() or self.app_secret
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests
        self.dev_qr_url = dev_qr_url

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def create_order(
        self,
        *,
        amount: Decimal | float | str,
        sku: str,
        callback_url: str,
        order_no: str,
        title: str | None = None,
        return_url: str | None = None,
    ) -> HupijiaoOrderResult:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        if not self.is_configured:
            return HupijiaoOrderResult(
                order_no=order_no,
                qr_code_url=self.dev_qr_url,
                payment_url=self.dev_qr_url,
                expires_at=expires_at,
                raw={"mock": True, "reason": "hupijiao credentials not configured"},
                is_mock=True,
            )

        params: dict[str, Any] = {
            "version": "1.1",
            "appid": self.app_id,
            "trade_order_id": order_no,
            "total_fee": normalize_amount(amount),
            "title": title or f"PinDou {sku}",
            "time": str(int(time.time())),
            "notify_url": callback_url,
            "nonce_str": generate_nonce(),
            "plugins": "pindou-miniapp",
            "attach": sku,
        }
        if return_url:
            params["return_url"] = return_url
        params["hash"] = sign_params(params, self.app_secret)

        payload = self._post(PAYMENT_PATH, params)
        self._assert_success_payload(payload)
        if payload.get("hash") and not verify_signature(payload, self.app_secret):
            raise HupijiaoSignatureError("Hupijiao create_order response signature mismatch.")

        payment_url = str(payload.get("url") or "")
        qr_code_url = str(payload.get("url_qrcode") or payment_url or self.dev_qr_url)
        return HupijiaoOrderResult(
            order_no=order_no,
            qr_code_url=qr_code_url,
            payment_url=payment_url or qr_code_url,
            expires_at=expires_at,
            raw=payload,
        )

    def query_order(self, order_no: str) -> HupijiaoQueryResult:
        if not self.is_configured:
            return HupijiaoQueryResult(order_no=order_no, status="pending", paid_at=None, raw={"mock": True})

        params: dict[str, Any] = {
            "appid": self.app_id,
            "out_trade_order": order_no,
            "time": str(int(time.time())),
            "nonce_str": generate_nonce(),
        }
        params["hash"] = sign_params(params, self.app_secret)

        payload = self._post(QUERY_PATH, params)
        self._assert_success_payload(payload)
        if payload.get("hash") and not verify_signature(payload, self.app_secret):
            raise HupijiaoSignatureError("Hupijiao query_order response signature mismatch.")

        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        raw_status = str(data.get("status") or "")
        status = {
            HUPIJIAO_PAID_STATUS: "paid",
            HUPIJIAO_PENDING_STATUS: "pending",
            HUPIJIAO_CANCELLED_STATUS: "cancelled",
            "RD": "refunding",
            "UD": "refund_failed",
        }.get(raw_status, "unknown")
        paid_at = datetime.now(timezone.utc) if status == "paid" else None
        return HupijiaoQueryResult(order_no=order_no, status=status, paid_at=paid_at, raw=payload)

    def verify_webhook(self, params: Mapping[str, Any]) -> bool:
        return bool(self.webhook_secret and verify_signature(params, self.webhook_secret))

    def _post(self, path: str, params: Mapping[str, Any]) -> dict[str, Any]:
        try:
            response = self.session.post(
                f"{self.api_base_url}{path}",
                data=dict(params),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.Timeout as exc:
            raise HupijiaoAPIError("虎皮椒请求超时。") from exc
        except requests.RequestException as exc:
            raise HupijiaoAPIError("虎皮椒网络请求失败。") from exc
        except ValueError as exc:
            raise HupijiaoAPIError("虎皮椒响应不是合法 JSON。") from exc

        if not isinstance(payload, dict):
            raise HupijiaoAPIError("虎皮椒响应格式异常。")
        return payload

    @staticmethod
    def _assert_success_payload(payload: Mapping[str, Any]) -> None:
        if payload.get("errcode") not in HUPIJIAO_SUCCESS:
            message = str(payload.get("errmsg") or "虎皮椒返回失败。")
            raise HupijiaoAPIError(message)
