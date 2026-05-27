from __future__ import annotations

from typing import Any

import pytest

from pindou.services.hupijiao_service import (
    HupijiaoAPIError,
    HupijiaoService,
    normalize_amount,
    sign_params,
    verify_signature,
)


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, data: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "data": data, "timeout": timeout})
        return FakeResponse(self.payload)


def signed_payload(payload: dict[str, Any], secret: str) -> dict[str, Any]:
    return {**payload, "hash": sign_params(payload, secret)}


def test_sign_params_filters_hash_and_empty_values() -> None:
    params = {"b": "2", "a": "1", "empty": "", "none": None, "hash": "bad"}

    assert sign_params(params, "secret") == "8d9f51949e440aa629fd1a035708473a"
    assert verify_signature({"b": "2", "a": "1", "hash": "8d9f51949e440aa629fd1a035708473a"}, "secret")


def test_create_order_posts_signed_form_and_returns_qr_url() -> None:
    secret = "test-secret"
    payload = signed_payload({"errcode": 0, "errmsg": "success!", "url_qrcode": "https://pay/qr.png", "url": "https://pay"}, secret)
    fake = FakeSession(payload)
    service = HupijiaoService(app_id="app-1", app_secret=secret, api_base_url="https://api.test", session=fake)

    result = service.create_order(amount="28", sku="monthly_28", callback_url="https://api/callback", order_no="PD123")

    assert result.qr_code_url == "https://pay/qr.png"
    assert fake.calls[0]["url"] == "https://api.test/payment/do.html"
    posted = fake.calls[0]["data"]
    assert posted["appid"] == "app-1"
    assert posted["trade_order_id"] == "PD123"
    assert posted["total_fee"] == "28.00"
    assert verify_signature(posted, secret)


def test_create_order_returns_placeholder_when_not_configured() -> None:
    service = HupijiaoService(app_id="", app_secret="", dev_qr_url="/static/mock.svg")

    result = service.create_order(amount="9.9", sku="single_9.9", callback_url="http://local/webhook", order_no="PDDEV")

    assert result.is_mock is True
    assert result.qr_code_url == "/static/mock.svg"
    assert result.order_no == "PDDEV"


def test_query_order_maps_hupijiao_status_to_internal_status() -> None:
    secret = "test-secret"
    payload = signed_payload({"errcode": 0, "errmsg": "success!", "data": {"status": "OD"}}, secret)
    fake = FakeSession(payload)
    service = HupijiaoService(app_id="app-1", app_secret=secret, api_base_url="https://api.test", session=fake)

    result = service.query_order("PD123")

    assert result.status == "paid"
    assert result.paid_at is not None
    assert fake.calls[0]["url"] == "https://api.test/payment/query.html"
    assert fake.calls[0]["data"]["out_trade_order"] == "PD123"


def test_webhook_signature_uses_webhook_secret() -> None:
    params = {"trade_order_id": "PD123", "status": "OD", "total_fee": "9.90"}
    signed = signed_payload(params, "webhook-secret")
    service = HupijiaoService(app_id="app-1", app_secret="app-secret", webhook_secret="webhook-secret")

    assert service.verify_webhook(signed)
    assert not service.verify_webhook({**signed, "status": "WP"})


def test_api_error_when_gateway_returns_failure() -> None:
    fake = FakeSession({"errcode": 500, "errmsg": "invalid sign!"})
    service = HupijiaoService(app_id="app-1", app_secret="secret", api_base_url="https://api.test", session=fake)

    with pytest.raises(HupijiaoAPIError):
        service.create_order(amount="9.9", sku="single_9.9", callback_url="https://api/callback", order_no="PD123")


def test_normalize_amount_rounds_to_two_decimals() -> None:
    assert normalize_amount("9.995") == "10.00"
