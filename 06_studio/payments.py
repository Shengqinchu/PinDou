"""Xunhupay adapter. Amounts are CNY fen; there is no production mock mode.

Contract: https://www.xunhupay.com/doc/api/pay.html and /search.html.
The gateway's QR image is already encoded and valid for five minutes.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class PaymentUnavailable(RuntimeError):
    pass


class PaymentRejected(PaymentUnavailable):
    pass


def sign(params: dict, secret: str) -> str:
    values = [(k, str(v)) for k, v in sorted(params.items()) if k != "hash" and v is not None and v != ""]
    return hashlib.md5(("&".join(f"{k}={v}" for k, v in values) + secret).encode()).hexdigest()


def verify(params: dict, secret: str) -> bool:
    received = str(params.get("hash", "")).lower()
    return bool(secret and len(received) == 32 and hmac.compare_digest(sign(params, secret), received))


def https_url(value: str) -> str:
    parsed = urlparse(str(value))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise PaymentUnavailable("Invalid payment URL")
    return str(value)


class Gateway:
    def __init__(self):
        self.app_id = os.getenv("HUPIJIAO_APP_ID", "").strip()
        self.secret = os.getenv("HUPIJIAO_APP_SECRET", "").strip()
        self.base = os.getenv("HUPIJIAO_API_BASE_URL", "https://api.xunhupay.com").rstrip("/")
        self.origin = os.getenv("STUDIO_PUBLIC_ORIGIN", "https://pindoupuppy.com").rstrip("/")

    @property
    def configured(self):
        return bool(self.app_id and self.secret and self.base.startswith("https://"))

    def request(self, path: str, values: dict) -> dict:
        if not self.configured:
            raise PaymentUnavailable("Payment account is not configured")
        params = {"appid": self.app_id, "time": str(int(time.time())), "nonce_str": secrets.token_hex(16), **values}
        params["hash"] = sign(params, self.secret)
        req = Request(https_url(self.base + path), data=urlencode(params).encode(), headers={
            "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "PinDou-Studio/2.0",
        })
        try:
            with urlopen(req, timeout=15) as response:
                payload = json.loads(response.read(32000))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            # A timeout can still have created an order. Callers keep its reservation.
            raise PaymentUnavailable("Payment gateway temporarily unavailable") from exc
        if not isinstance(payload, dict):
            raise PaymentUnavailable("Invalid gateway response")
        if payload.get("errcode") not in (0, "0"):
            raise PaymentRejected("Payment gateway declined the request")
        # Flat create responses are signed. Query returns nested data; the legacy PHP
        # contract does not define a portable nested hash. Queries are authenticated
        # outbound HTTPS to the fixed merchant gateway, with order/amount binding below.
        if "data" not in payload and not verify(payload, self.secret):
            raise PaymentUnavailable("Invalid gateway response signature")
        return payload

    def create(self, order_id: str, cny_fen: int) -> dict:
        result = self.request("/payment/do.html", {
            "version": "1.1", "trade_order_id": order_id,
            "total_fee": f"{cny_fen // 100}.{cny_fen % 100:02d}",
            "title": "Pindou Puppy Studio", "plugins": "pindou-studio",
            "notify_url": self.origin + "/studio-api/payments/hupijiao/notify",
            "return_url": self.origin + "/studio/order/" + order_id,
        })
        data = result.get("data") if isinstance(result.get("data"), dict) else result
        url = https_url(data["url"]) if data.get("url") else ""
        qr = https_url(data["url_qrcode"]) if data.get("url_qrcode") else ""
        if not (url or qr):
            raise PaymentUnavailable("Gateway did not return a cashier")
        # `openid` in legacy create responses is an undocumented historic order ID;
        # do not confuse it with the documented query `open_order_id` identity.
        return {"payment_url": url, "qr_url": qr, "provider_id": str(data.get("open_order_id") or "")}

    def query(self, order_id: str) -> dict:
        result = self.request("/payment/query.html", {"out_trade_order": order_id})
        data = result.get("data")
        if not isinstance(data, dict):
            raise PaymentUnavailable("Invalid query response")
        return data

    def verify_callback(self, params):
        return self.configured and params.get("appid") == self.app_id and verify(params, self.secret)


gateway = Gateway()
