from __future__ import annotations

import io
from datetime import datetime
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pindou.api.deps import get_db
from pindou.config import get_settings
from pindou.db.models import Base, User
from pindou.main import create_app
from pindou.providers.base import PreviewResult
from pindou.services.hupijiao_service import sign_params
from pindou.services.cdk_service import CDKService


@pytest.fixture()
def api_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv("PINDOU_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("PINDOU_PREVIEW_DIR", str(tmp_path / "previews"))
    monkeypatch.setenv("PINDOU_PATTERN_DIR", str(tmp_path / "patterns"))
    monkeypatch.setenv("ENABLE_REVERSE_PROXY_HEALTH_MONITOR", "false")
    monkeypatch.setenv("ENABLE_EXPIRED_ORIGINAL_DELETE_TASK", "false")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    app = create_app()

    def override_db() -> Iterator[Session]:
        with SessionTesting() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, SessionTesting
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def png_bytes(color: tuple[int, int, int] = (250, 250, 250)) -> bytes:
    image = Image.new("RGB", (32, 32), color)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def auth_headers(client: TestClient, *, consent: bool = True) -> dict[str, str]:
    response = client.post("/api/user/login", json={"code": "test-code", "nickname": "Tester"})
    assert response.status_code == 200
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    if consent:
        assert client.post("/api/user/consent", json={"type": "sensitive"}, headers=headers).status_code == 200
    return headers


def upload_image(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/upload",
        files={"image": ("sample.png", png_bytes(), "image/png")},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["image_id"]


def test_user_login_profile_consent_and_auth_error(api_client) -> None:
    client, _session_factory = api_client

    assert client.get("/api/user/me").status_code == 401
    response = client.post("/api/user/login", json={"code": "abc", "nickname": "Pin"})
    assert response.status_code == 200
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.get("/api/user/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["nickname"] == "Pin"

    consent = client.post("/api/user/consent", json={"type": "privacy"}, headers=headers)
    assert consent.status_code == 200
    assert consent.json()["success"] is True


def test_upload_happy_path_and_consent_error(api_client) -> None:
    client, _session_factory = api_client
    headers_without_consent = auth_headers(client, consent=False)

    denied = client.post(
        "/api/upload",
        files={"image": ("sample.png", png_bytes(), "image/png")},
        headers=headers_without_consent,
    )
    assert denied.status_code == 403
    assert denied.json()["error"] == "CONSENT_REQUIRED"

    assert client.post("/api/user/consent", json={"type": "sensitive"}, headers=headers_without_consent).status_code == 200
    uploaded = client.post(
        "/api/upload",
        files={"image": ("sample.png", png_bytes(), "image/png")},
        headers=headers_without_consent,
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["image_id"]


def test_pattern_build_happy_path_and_error(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)

    bad = client.post("/api/pattern/build", json={"size": "10x10"}, headers=headers)
    assert bad.status_code == 422

    response = client.post(
        "/api/pattern/build",
        data={"size": "26x26", "mode": "script"},
        files={"raw_image": ("sample.png", png_bytes((240, 240, 240)), "image/png")},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["bead_total"] > 0
    assert payload["metadata"]["artwork_id"]
    assert payload["metadata"]["labeled_image_url"].endswith("_with_grid.png")

    partitions = client.get(f"/api/pattern/{payload['metadata']['artwork_id']}/partitions", headers=headers)
    assert partitions.status_code == 200
    partition_payload = partitions.json()
    assert partition_payload["total"] == 4
    assert partition_payload["partition_layout"] == "2x2"
    assert partition_payload["items"][0]["label"] == "左上区"
    assert partition_payload["items"][0]["grid_offset"] == {"row": 0, "col": 0}
    assert partition_payload["items"][0]["url"].endswith("_partition_01.png")


def test_generate_script_artwork_pattern_and_delete_flow(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)
    image_id = upload_image(client, headers)

    missing = client.post("/api/generate/script", json={"image_id": "missing", "size": "26x26"}, headers=headers)
    assert missing.status_code == 404

    generated = client.post("/api/generate/script", json={"image_id": image_id, "size": "26x26"}, headers=headers)
    assert generated.status_code == 200
    artwork_id = generated.json()["artwork_id"]
    assert generated.json()["pattern"]["metadata"]["artwork_id"] == artwork_id
    assert generated.json()["pattern"]["metadata"]["labeled_image_url"].endswith("_with_grid.png")

    assert client.get("/api/artwork/list", headers=headers).json()[0]["artwork_id"] == artwork_id
    assert client.get(f"/api/artwork/{artwork_id}", headers=headers).status_code == 200
    assert client.get(f"/api/pattern/{artwork_id}", headers=headers).status_code == 200
    assert client.delete(f"/api/artwork/{artwork_id}", headers=headers).json() == {"success": True}
    assert client.get(f"/api/artwork/{artwork_id}", headers=headers).status_code == 404


def test_generate_ai_endpoint_with_mocked_provider(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)
    image_id = upload_image(client, headers)

    class FakeChain:
        def generate(self, image: bytes, style_preset, size_preset, seed=None) -> PreviewResult:
            return PreviewResult.from_image_bytes(
                png_bytes((255, 255, 255)),
                target_color_count=8,
                provider_used="fake",
                cost_estimate=0.0,
                latency_ms=10,
            )

    monkeypatch.setattr("pindou.api.generate.build_preview_chain", lambda: FakeChain())
    response = client.post(
        "/api/generate/ai",
        json={"image_id": image_id, "style_preset": "q_portrait", "size_preset": "26x26"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["preview"]["provider_used"] == "fake"

    preview_only = client.post(
        "/api/v1/preview/generate",
        data={"style_preset": "q_portrait", "size_preset": "26x26"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers=headers,
    )
    assert preview_only.status_code == 200
    assert preview_only.json()["provider_used"] == "fake"
    assert "preview_id" in preview_only.json()
    assert "pattern" not in preview_only.json()


def test_preview_generate_accepts_sqlite_naive_monthly_card(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)

    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        user.free_credits_remaining = 0
        user.paid_credits = 0
        user.monthly_card_expires_at = datetime(2099, 1, 1, 0, 0, 0)
        session.commit()

    class FakeChain:
        def generate(self, image: bytes, style_preset, size_preset, seed=None) -> PreviewResult:
            return PreviewResult.from_image_bytes(
                png_bytes((255, 255, 255)),
                target_color_count=8,
                provider_used="fake",
                cost_estimate=0.0,
                latency_ms=10,
            )

    monkeypatch.setattr("pindou.api.generate.build_preview_chain", lambda: FakeChain())
    response = client.post(
        "/api/v1/preview/generate",
        data={"style_preset": "q_portrait", "size_preset": "26x26"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["provider_used"] == "fake"


def test_payment_and_admin_confirm_flow(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)
    unauthorized = client.get("/api/admin/orders")
    assert unauthorized.status_code == 401

    order = client.post("/api/payment/order/create", json={"sku_id": "single_9.9"}, headers=headers)
    assert order.status_code == 200
    order_id = order.json()["order_id"]

    assert client.get(f"/api/payment/order/{order_id}", headers=headers).json() == {"status": "pending"}
    qr = client.get("/api/payment/customer-service", params={"order_id": order_id}, headers=headers)
    assert qr.status_code == 200
    assert qr.json()["order_id"] == order_id

    bad_admin = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
    assert bad_admin.status_code == 401
    admin_token = client.post("/api/admin/login", json={"username": "admin", "password": "admin"}).json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    confirmed = client.post("/api/admin/payment/confirm", json={"order_id": order_id}, headers=admin_headers)
    assert confirmed.status_code == 200
    assert client.get(f"/api/payment/order/{order_id}", headers=headers).json() == {"status": "paid_confirmed"}
    assert client.get("/api/admin/orders", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/users", headers=admin_headers).status_code == 200


def test_hupijiao_webhook_marks_order_paid_and_grants_monthly_card(api_client) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)
    order = client.post("/api/payment/order/create", json={"sku_id": "monthly_28"}, headers=headers)
    assert order.status_code == 200
    payload = order.json()
    assert payload["payment_provider"] == "hupijiao"
    assert payload["qr_code_url"]

    webhook_payload = {
        "trade_order_id": payload["order_no"],
        "total_fee": "28.00",
        "transaction_id": "MOCKTXN001",
        "open_order_id": "OPEN001",
        "order_title": "PinDou 月卡",
        "status": "OD",
        "appid": "mock",
        "time": "1760000000",
        "nonce_str": "mocknonce",
    }
    webhook_payload["hash"] = sign_params(webhook_payload, "pindou-dev-hupijiao-mock-secret")
    callback = client.post("/api/v1/webhook/hupijiao", data=webhook_payload)
    assert callback.status_code == 200
    assert callback.text == "success"
    assert client.get(f"/api/payment/order/{payload['order_id']}", headers=headers).json() == {
        "status": "paid_confirmed"
    }
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        assert user.monthly_card_expires_at is not None


def test_cdk_redeem_and_admin_batch_generate(api_client) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)
    with session_factory() as session:
        CDKService(session).create_cdk(code="ABCDEFGHJKLMNPQRTU", cdk_type="credit_pack_5", value=5)

    invalid = client.post("/api/cdk/redeem", json={"cdk_code": "missing"}, headers=headers)
    assert invalid.status_code == 404

    redeemed = client.post("/api/cdk/redeem", json={"cdk_code": "ABCDEFGHJKLMNPQRTU"}, headers=headers)
    assert redeemed.status_code == 200
    assert redeemed.json()["cdk_type"] == "credit_pack_5"

    admin_token = client.post("/api/admin/login", json={"username": "admin", "password": "admin"}).json()["token"]
    batch = client.post(
        "/api/admin/cdk/batch_generate",
        json={"cdk_type": "single_use", "value": 1, "count": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert batch.status_code == 200
    assert len(batch.json()["cdks"]) == 2
