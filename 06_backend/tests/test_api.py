from __future__ import annotations

import io
import base64
import csv
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pindou.api.deps import get_db
from pindou.config import get_settings
from pindou.api.security import create_access_token
from pindou.db.models import AdminAuditLog, Artwork, Base, CDK, EmailCode, Order, User
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
    monkeypatch.setenv("HUPIJIAO_APP_ID", "")
    monkeypatch.setenv("HUPIJIAO_APP_SECRET", "")
    monkeypatch.setenv("HUPIJIAO_WEBHOOK_SECRET", "")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "sha256:8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918")
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


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/admin/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


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

    console = client.get("/console/")
    assert console.status_code == 200
    assert "PinDou Admin Console" in console.text

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


def test_email_code_login_uses_shared_db_and_returns_email_user(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    sent_codes: list[tuple[str, str]] = []

    async def fake_send_verification_email(email: str, code: str) -> tuple[bool, str]:
        sent_codes.append((email, code))
        return True, "ok"

    monkeypatch.setattr(
        "pindou.services.email_verification.send_verification_email",
        fake_send_verification_email,
    )

    sent = client.post("/api/user/email/send-code", json={"email": "Test.User@Example.COM"})
    assert sent.status_code == 200
    assert sent.json()["success"] is True
    assert sent.json()["expires_in_seconds"] == 300
    assert sent_codes and sent_codes[0][0] == "test.user@example.com"
    code = sent_codes[0][1]
    assert code.isdigit()
    assert len(code) == 6

    rate_limited = client.post("/api/user/email/send-code", json={"email": "test.user@example.com"})
    assert rate_limited.status_code == 429
    assert rate_limited.json()["error"] == "EMAIL_CODE_RATE_LIMITED"

    wrong_code = "000000" if code != "000000" else "111111"
    wrong = client.post("/api/user/email/verify", json={"email": "test.user@example.com", "code": wrong_code})
    assert wrong.status_code == 400
    assert wrong.json()["error"] == "EMAIL_CODE_INVALID"

    verified = client.post("/api/user/email/verify", json={"email": "test.user@example.com", "code": code})
    assert verified.status_code == 200
    payload = verified.json()
    assert payload["token"]
    assert payload["user"]["email"] == "test.user@example.com"
    assert payload["user"]["user_id"].startswith("email_")
    assert payload["user"]["nickname"] == "test.user"

    profile = client.get("/api/user/profile", headers={"Authorization": f"Bearer {payload['token']}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "test.user@example.com"

    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == "test.user@example.com"))
        assert user is not None
        assert user.openid == payload["user"]["user_id"]
        record = session.scalar(select(EmailCode).where(EmailCode.email == "test.user@example.com"))
        assert record is not None
        assert record.consumed_at is not None
        assert record.code_hash != code


def test_email_code_rejects_disposable_email(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _session_factory = api_client

    async def fail_if_called(email: str, code: str) -> tuple[bool, str]:
        raise AssertionError("disposable email should be rejected before sending")

    monkeypatch.setattr("pindou.services.email_verification.send_verification_email", fail_if_called)

    response = client.post("/api/user/email/send-code", json={"email": "demo@mailinator.com"})
    assert response.status_code == 400
    assert response.json()["message_cn"] == "暂不支持一次性邮箱，请换一个常用邮箱。"


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


def test_pattern_build_accepts_base64_payload(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)
    encoded = base64.b64encode(png_bytes((230, 230, 230))).decode("ascii")

    response = client.post(
        "/api/pattern/build",
        json={
            "size": "26x26",
            "mode": "script",
            "raw_image_base64": encoded,
            "filename": "sample.png",
        },
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["bead_total"] > 0
    assert payload["metadata"]["artwork_id"]


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


def test_payment_and_admin_read_only_flow(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)
    unauthorized = client.get("/api/admin/orders")
    assert unauthorized.status_code == 401

    order = client.post("/api/payment/order/create", json={"sku_id": "single_9.9"}, headers=headers)
    assert order.status_code == 200
    order_payload = order.json()
    order_id = order_payload["order_id"]

    assert client.get(f"/api/payment/order/{order_id}", headers=headers).json() == {"status": "pending"}
    qr = client.get("/api/payment/customer-service", params={"order_id": order_id}, headers=headers)
    assert qr.status_code == 200
    assert qr.json()["order_id"] == order_id

    bad_admin = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
    assert bad_admin.status_code == 401
    headers_admin = admin_headers(client)
    listed = client.get("/api/admin/orders", headers=headers_admin)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    detail = client.get(f"/api/admin/orders/{order_payload['order_no']}", headers=headers_admin)
    assert detail.status_code == 200
    assert detail.json()["webhook"]["callback_logs"] == []
    disabled = client.post("/api/admin/payment/confirm", json={"order_id": order_id}, headers=headers_admin)
    assert disabled.status_code == 403


def test_admin_read_only_endpoints_require_role_and_redact_config(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    monkeypatch.setenv("COS_SECRET_KEY", "cos-secret-should-not-leak")
    monkeypatch.setenv("HUPIJIAO_APP_SECRET", "hupijiao-secret-should-not-leak")
    get_settings.cache_clear()

    with session_factory() as session:
        user = User(openid="admin_target", nickname="Needle", avatar="")
        session.add(user)
        session.flush()
        artwork = Artwork(
            user_id=user.openid,
            original_path="uploads/source.png",
            preview_path="/static/previews/legacy.png",
            pattern_json={"grid": [["01"]]},
            style_preset="chibi",
            size_preset="26x26",
            title="Legacy preview",
        )
        order = Order(
            user_id=user.openid,
            order_no="PDADMIN001",
            sku="single_9.9",
            amount_cny=Decimal("9.90"),
            status="pending_qr",
            payment_provider="hupijiao",
        )
        cdk = CDK(code="ADMINCDKABCDEFGHJK", type="credit_pack_5", value=5, batch_id="batch-1")
        session.add_all([artwork, order, cdk])
        session.commit()

    headers_admin = admin_headers(client)
    with session_factory() as session:
        login_audit = session.scalar(select(AdminAuditLog).where(AdminAuditLog.action == "admin.login"))
        assert login_audit is not None
        assert login_audit.actor_role == "admin"
        assert login_audit.after_json["result"] == "success"
    user_headers = auth_headers(client)
    bad_role_headers = {"Authorization": f"Bearer {create_access_token(subject='ops', role='outsider')}"}
    endpoints = [
        "/api/admin/dashboard",
        "/api/admin/orders",
        "/api/admin/orders/PDADMIN001",
        "/api/admin/cdks",
        "/api/admin/users",
        "/api/admin/users/admin_target",
        "/api/admin/artworks",
        "/api/admin/config",
        "/api/admin/audit-logs",
    ]

    for endpoint in endpoints:
        assert client.get(endpoint).status_code == 401
        assert client.get(endpoint, headers=user_headers).status_code == 403
        assert client.get(endpoint, headers=bad_role_headers).status_code == 403
        assert client.get(endpoint, headers=headers_admin).status_code == 200

    dashboard = client.get("/api/admin/dashboard", headers=headers_admin).json()
    assert dashboard["total_users"] >= 1
    assert dashboard["today_orders"] >= 0
    assert "payment_success_rate" in dashboard
    assert "recent_dangerous_actions" in dashboard
    assert dashboard["total_cdks"] >= 1
    assert dashboard["redeemed_cdks"] >= 0
    assert len(dashboard["daily_new_users"]) == 7
    assert len(dashboard["daily_orders"]) == 7
    assert set(dashboard["daily_new_users"][0]) == {"date", "count"}

    orders = client.get("/api/admin/orders", params={"search": "PDADMIN"}, headers=headers_admin).json()
    assert orders == {"items": [orders["items"][0]], "total": 1, "page": 1, "size": 50}
    assert orders["items"][0]["order_no"] == "PDADMIN001"
    assert orders["items"][0]["raw_status"] == "pending_qr"

    users = client.get("/api/admin/users", params={"search": "Needle"}, headers=headers_admin).json()
    assert users["items"][0]["user_id"] == "admin_target"
    assert users["items"][0]["artwork_count"] == 1

    user_detail = client.get("/api/admin/users/admin_target", headers=headers_admin).json()
    assert user_detail["artwork_count"] == 1
    assert user_detail["recent_orders"][0]["order_no"] == "PDADMIN001"

    artworks = client.get("/api/admin/artworks", params={"user_id": "admin_target"}, headers=headers_admin).json()
    assert artworks["items"][0]["legacy_preview"] is True

    config = client.get("/api/admin/config", headers=headers_admin).json()
    config_text = json.dumps(config, ensure_ascii=False)
    assert "cos-secret-should-not-leak" not in config_text
    assert "hupijiao-secret-should-not-leak" not in config_text
    assert config["sensitive"]["COS_SECRET_KEY"] == {"env": "COS_SECRET_KEY", "configured": True}
    assert config["sensitive"]["HUPIJIAO_APP_SECRET"] == {"env": "HUPIJIAO_APP_SECRET", "configured": True}

    audit_logs = client.get(
        "/api/admin/audit-logs",
        params={"action": "admin.login", "resource_type": "admin_session"},
        headers=headers_admin,
    ).json()
    assert audit_logs["total"] >= 1
    assert audit_logs["items"][0]["action"] == "admin.login"
    assert audit_logs["items"][0]["resource_type"] == "admin_session"


def test_admin_login_failed_attempts_do_not_lock_out(api_client, caplog: pytest.LogCaptureFixture) -> None:
    client, _session_factory = api_client
    headers = {"x-forwarded-for": "203.0.113.77"}
    caplog.set_level("WARNING", logger="pindou.api.admin")

    for _index in range(6):
        response = client.post(
            "/api/admin/login",
            json={"username": "limited-admin", "password": "wrong"},
            headers=headers,
        )
        assert response.status_code == 401
        assert response.json()["message_cn"] == "管理员账号或密码不正确。"
    assert "admin_login_failed" in caplog.text
    assert "admin_username_matches" in caplog.text
    assert "password_matches" in caplog.text
    assert "wrong" not in caplog.text


def test_admin_two_step_order_fulfillment_is_audited_and_idempotent(api_client) -> None:
    client, session_factory = api_client
    with session_factory() as session:
        user = User(openid="manual_user", nickname="Manual", avatar="")
        order = Order(
            user_id=user.openid,
            order_no="PDMANUAL001",
            sku="single_9.9",
            amount_cny=Decimal("9.90"),
            status="pending_cs_qr",
            payment_provider="customer_service",
        )
        session.add_all([user, order])
        session.commit()

    headers_admin = admin_headers(client)
    user_headers = auth_headers(client)
    assert client.post(
        "/api/admin/orders/PDMANUAL001/confirm-payment-fact",
        json={"reason": "paid via QR"},
        headers=user_headers,
    ).status_code == 403

    confirmed = client.post(
        "/api/admin/orders/PDMANUAL001/confirm-payment-fact",
        json={"reason": "paid via QR"},
        headers=headers_admin,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["changed"] is True
    assert confirmed.json()["order"]["raw_status"] == "manual_payment_confirmed"
    assert isinstance(confirmed.json()["audit_id"], int)

    repeated_confirm = client.post(
        "/api/admin/orders/PDMANUAL001/confirm-payment-fact",
        json={"reason": "operator clicked again"},
        headers=headers_admin,
    )
    assert repeated_confirm.status_code == 200
    assert repeated_confirm.json()["changed"] is False

    granted = client.post(
        "/api/admin/orders/PDMANUAL001/grant-entitlement",
        json={"reason": "release purchased credit"},
        headers=headers_admin,
    )
    assert granted.status_code == 200
    assert granted.json()["granted"] is True
    assert granted.json()["order"]["raw_status"] == "paid_confirmed"
    assert granted.json()["entitlement"]["user"]["paid_credits"] == 1

    repeated_grant = client.post(
        "/api/admin/orders/PDMANUAL001/grant-entitlement",
        json={"reason": "second click"},
        headers=headers_admin,
    )
    assert repeated_grant.status_code == 200
    assert repeated_grant.json()["granted"] is False
    with session_factory() as session:
        manual_user = session.scalar(select(User).where(User.openid == "manual_user"))
        assert manual_user is not None
        assert manual_user.paid_credits == 1
        audits = list(
            session.scalars(select(AdminAuditLog).where(AdminAuditLog.resource_id == "PDMANUAL001"))
        )
        assert [audit.action for audit in audits].count("admin.order.confirm_payment_fact") == 2
        assert [audit.action for audit in audits].count("admin.order.grant_entitlement") == 2


def test_admin_grant_requires_confirmed_or_paid_order(api_client) -> None:
    client, session_factory = api_client
    with session_factory() as session:
        user = User(openid="unconfirmed_user", nickname="Unconfirmed", avatar="")
        order = Order(
            user_id=user.openid,
            order_no="PDUNCONFIRMED",
            sku="single_9.9",
            amount_cny=Decimal("9.90"),
            status="pending_qr",
            payment_provider="hupijiao",
        )
        session.add_all([user, order])
        session.commit()

    response = client.post(
        "/api/admin/orders/PDUNCONFIRMED/grant-entitlement",
        json={"reason": "too early"},
        headers=admin_headers(client),
    )
    assert response.status_code == 409


def test_admin_adjust_credits_requires_reason_and_blocks_negative_balances(api_client) -> None:
    client, session_factory = api_client
    with session_factory() as session:
        user = User(openid="credit_user", nickname="Credit", avatar="", free_credits_remaining=1, paid_credits=1)
        session.add(user)
        session.commit()

    headers_admin = admin_headers(client)
    assert client.post(
        "/api/admin/users/credit_user/credits",
        json={"delta_paid": 1, "reason": "viewer should not write"},
        headers=auth_headers(client),
    ).status_code == 403

    negative = client.post(
        "/api/admin/users/credit_user/credits",
        json={"delta_free": -2, "reason": "invalid negative"},
        headers=headers_admin,
    )
    assert negative.status_code == 400

    adjusted = client.post(
        "/api/admin/users/credit_user/credits",
        json={"delta_free": 2, "delta_paid": -1, "set_monthly_card_days": 30, "reason": "support adjustment"},
        headers=headers_admin,
    )
    assert adjusted.status_code == 200
    payload = adjusted.json()
    assert payload["user"]["free_credits_remaining"] == 3
    assert payload["user"]["paid_credits"] == 0
    assert payload["user"]["monthly_card_expires_at"] is not None
    assert isinstance(payload["audit_id"], int)
    with session_factory() as session:
        audit = session.get(AdminAuditLog, payload["audit_id"])
        assert audit is not None
        assert audit.action == "admin.user.adjust_credits"
        assert audit.reason == "support adjustment"


def test_admin_cdk_batch_generation_and_csv_export(api_client) -> None:
    client, _session_factory = api_client
    headers_admin = admin_headers(client)
    assert client.post(
        "/api/admin/cdks/batch",
        json={"type": "credit_pack_5", "value": 5, "count": 2, "sales_channel": "xhs", "reason": "seed batch"},
        headers=auth_headers(client),
    ).status_code == 403

    created = client.post(
        "/api/admin/cdks/batch",
        json={
            "type": "credit_pack_5",
            "value": 5,
            "count": 3,
            "sales_channel": "xhs",
            "notes": "launch",
            "reason": "seed launch batch",
        },
        headers=headers_admin,
    )
    assert created.status_code == 200
    payload = created.json()
    assert len(payload["codes"]) == 3
    assert len(set(payload["codes"])) == 3
    assert payload["batch_id"]
    assert isinstance(payload["audit_id"], int)

    csv_denied = client.get("/api/admin/cdks/export.csv", headers=auth_headers(client))
    assert csv_denied.status_code == 403
    exported = client.get(
        "/api/admin/cdks/export.csv",
        params={"batch_id": payload["batch_id"], "status": "active"},
        headers=headers_admin,
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows) == 3
    assert set(rows[0]) == {
        "code",
        "type",
        "value",
        "status",
        "sales_channel",
        "batch_id",
        "redeemed_by",
        "redeemed_at",
        "created_at",
    }
    assert {row["batch_id"] for row in rows} == {payload["batch_id"]}
    assert {row["sales_channel"] for row in rows} == {"xhs"}


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
    duplicate = client.post("/api/v1/webhook/hupijiao", data=webhook_payload)
    assert duplicate.status_code == 200
    assert duplicate.text == "success"
    assert client.get(f"/api/payment/order/{payload['order_id']}", headers=headers).json() == {
        "status": "paid_confirmed"
    }
    detail = client.get(f"/api/admin/orders/{payload['order_no']}", headers=admin_headers(client))
    assert detail.status_code == 200
    webhook = detail.json()["webhook"]
    assert webhook["signature_passed"] is True
    assert webhook["amount_matched"] is True
    assert webhook["duplicate_callback"] is True
    assert len(webhook["callback_logs"]) == 2
    admin_grant = client.post(
        f"/api/admin/orders/{payload['order_no']}/grant-entitlement",
        json={"reason": "verify webhook fulfillment is idempotent"},
        headers=admin_headers(client),
    )
    assert admin_grant.status_code == 200
    assert admin_grant.json()["granted"] is False
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        assert user.monthly_card_expires_at is not None
        expires_at = user.monthly_card_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at < datetime.now(timezone.utc) + timedelta(days=31)


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

    headers_admin = admin_headers(client)
    listed = client.get("/api/admin/cdks", headers=headers_admin)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["code"] == "ABCDEFGHJKLMNPQRTU"
    batch = client.post(
        "/api/admin/cdk/batch_generate",
        json={"cdk_type": "single_use", "value": 1, "count": 2},
        headers=headers_admin,
    )
    assert batch.status_code == 403
