from __future__ import annotations

import io
import base64
import csv
import json
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pindou.api.deps import get_db
from pindou.api.generate import refund_reserved_ai_credit
from pindou.config import get_settings
from pindou.api.security import create_access_token
from pindou.db.models import (
    AdminAuditLog,
    Artwork,
    Base,
    CDK,
    CreditGrant,
    DailyQuota,
    DeviceClaim,
    EmailCode,
    GenerationJob,
    MembershipGrant,
    Order,
    User,
)
from pindou.main import create_app
from pindou.providers.base import PreviewResult
from pindou.services.hupijiao_service import sign_params
from pindou.services.cdk_service import CDKService
from pindou.services.credit_service import AI_GENERATION_POINT_COST, get_credit_balance, grant_points
from pindou.services.storage_util import get_storage_backend
from pindou.api import payment as payment_api


@pytest.fixture()
def api_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv("PINDOU_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("PINDOU_PREVIEW_DIR", str(tmp_path / "previews"))
    monkeypatch.setenv("PINDOU_PATTERN_DIR", str(tmp_path / "patterns"))
    monkeypatch.setenv("PINDOU_THUMBNAIL_DIR", str(tmp_path / "thumbnails"))
    monkeypatch.setenv("ENABLE_REVERSE_PROXY_HEALTH_MONITOR", "false")
    monkeypatch.setenv("ENABLE_EXPIRED_ORIGINAL_DELETE_TASK", "false")
    monkeypatch.setenv("HUPIJIAO_APP_ID", "")
    monkeypatch.setenv("HUPIJIAO_APP_SECRET", "")
    monkeypatch.setenv("HUPIJIAO_WEBHOOK_SECRET", "")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "sha256:8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918")
    get_settings.cache_clear()
    get_storage_backend.cache_clear()

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
    get_storage_backend.cache_clear()


def png_bytes(color: tuple[int, int, int] = (250, 250, 250)) -> bytes:
    image = Image.new("RGB", (32, 32), color)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def image_bytes(*, image_format: str = "PNG", size: tuple[int, int] = (320, 180)) -> bytes:
    image = Image.new("RGB", size, (255, 200, 160))
    output = io.BytesIO()
    image.save(output, format=image_format)
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


def wait_generation_job(
    client: TestClient,
    headers: dict[str, str],
    job_id: str,
    *,
    timeout_seconds: float = 10.0,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    latest: dict | None = None
    time.sleep(0.1)
    while time.monotonic() < deadline:
        response = client.get(f"/api/generate/status/{job_id}", headers=headers)
        assert response.status_code == 200
        latest = response.json()
        if latest["status"] in {"succeeded", "failed"}:
            return latest
        time.sleep(0.15)
    raise AssertionError(f"generation job did not finish: {latest}")


def capture_email_codes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    sent_codes: list[tuple[str, str]] = []

    async def fake_send_verification_email(email: str, code: str) -> tuple[bool, str]:
        sent_codes.append((email, code))
        return True, "ok"

    monkeypatch.setattr(
        "pindou.services.email_verification.send_verification_email",
        fake_send_verification_email,
    )
    return sent_codes


def test_user_login_profile_consent_and_auth_error(api_client) -> None:
    client, _session_factory = api_client

    console = client.get("/Ios235169/")
    assert console.status_code == 200
    assert "PinDou Admin Console" in console.text
    assert client.get("/console/").status_code == 404

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


def test_update_profile_validates_nickname_and_preset_avatar(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client, consent=False)

    updated = client.patch(
        "/api/user/profile",
        json={"nickname": "  小拼 豆  ", "avatar_url": "/brand/logo.png"},
        headers=headers,
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["nickname"] == "小拼 豆"
    assert payload["avatar"] == "/brand/logo.png"
    assert "free_credits_remaining" in payload
    assert "paid_credits" in payload

    empty = client.patch("/api/user/profile", json={"nickname": "   "}, headers=headers)
    assert empty.status_code == 422
    assert empty.json()["message_cn"] == "昵称不能为空。"

    too_long = client.patch("/api/user/profile", json={"nickname": "豆" * 21}, headers=headers)
    assert too_long.status_code == 422
    assert too_long.json()["message_cn"] == "昵称最多 20 个字符。"

    sensitive = client.patch("/api/user/profile", json={"nickname": "官方客服"}, headers=headers)
    assert sensitive.status_code == 422
    assert "昵称" in sensitive.json()["message_cn"]

    bad_avatar = client.patch("/api/user/profile", json={"avatar_url": "https://example.com/avatar.png"}, headers=headers)
    assert bad_avatar.status_code == 422
    assert bad_avatar.json()["message_cn"] == "请选择 PinDou 提供的预设头像。"


def test_upload_avatar_validates_type_size_and_stores_square_png(api_client, tmp_path) -> None:
    client, session_factory = api_client
    headers = auth_headers(client, consent=False)

    uploaded = client.post(
        "/api/user/avatar",
        files={"image": ("avatar.png", image_bytes(image_format="PNG", size=(320, 180)), "image/png")},
        headers=headers,
    )
    assert uploaded.status_code == 200
    payload = uploaded.json()
    assert payload["avatar_url"].startswith("/static/thumbnails/avatar_")
    assert payload["user"]["avatar"] == payload["avatar_url"]

    avatar_path = tmp_path / "thumbnails" / payload["avatar_url"].rsplit("/", 1)[-1]
    assert avatar_path.exists()
    with Image.open(avatar_path) as avatar:
        assert avatar.size == (256, 256)
        assert avatar.format == "PNG"

    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid == payload["user"]["user_id"]))
        assert user is not None
        assert user.avatar == payload["avatar_url"]

    too_large = client.post(
        "/api/user/avatar",
        files={"image": ("huge.png", b"x" * (2 * 1024 * 1024 + 1), "image/png")},
        headers=headers,
    )
    assert too_large.status_code == 413
    assert too_large.json()["message_cn"] == "头像图片不能超过 2MB。"

    wrong_type = client.post(
        "/api/user/avatar",
        files={"image": ("avatar.gif", b"GIF89a", "image/gif")},
        headers=headers,
    )
    assert wrong_type.status_code == 415
    assert wrong_type.json()["message_cn"] == "头像仅支持 JPG、PNG 或 WEBP 图片。"

    wrong_content = client.post(
        "/api/user/avatar",
        files={"image": ("avatar.png", image_bytes(image_format="JPEG"), "image/png")},
        headers=headers,
    )
    assert wrong_content.status_code == 415
    assert wrong_content.json()["message_cn"] == "头像图片格式不正确，请换一张 JPG、PNG 或 WEBP。"


def test_artwork_gallery_paginates_current_user(api_client) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)
    profile = client.get("/api/user/profile", headers=headers).json()
    user_id = profile["user_id"]

    pattern_one = {
        "color_counts": {"H7": 12, "G11": 4},
        "bead_total": 16,
        "palette_used": [{"code": "H7"}, {"code": "G11"}],
        "metadata": {"thumbnail_url": "/static/thumbnails/a.png"},
    }
    pattern_two = {
        "color_counts": {"F23": 7},
        "bead_total": 7,
        "palette_used": [{"code": "F23"}],
        "metadata": {"thumbnail_url": "/static/thumbnails/b.png"},
    }
    pattern_three = {
        "color_counts": {"A1": 2, "B2": 1, "C3": 1},
        "bead_total": 4,
        "palette_used": [{"code": "A1"}, {"code": "B2"}, {"code": "C3"}],
        "metadata": {"thumbnail_url": "/static/thumbnails/c.png"},
    }

    with session_factory() as session:
        session.add_all(
            [
                Artwork(
                    artwork_id="older",
                    user_id=user_id,
                    preview_path="/static/previews/older.png",
                    pattern_json=pattern_one,
                    style_preset="q_portrait",
                    size_preset="52x52",
                    title="旧作品",
                    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                ),
                Artwork(
                    artwork_id="middle",
                    user_id=user_id,
                    preview_path="/static/previews/middle.png",
                    pattern_json=pattern_two,
                    style_preset="q_pet",
                    size_preset="26x26",
                    title=None,
                    created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                ),
                Artwork(
                    artwork_id="newest",
                    user_id=user_id,
                    preview_path="/static/previews/newest.png",
                    pattern_json=pattern_three,
                    style_preset="cartoon_fallback",
                    size_preset="78x78",
                    title="新作品",
                    created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
                ),
                User(openid="other-user", nickname="Other"),
                Artwork(
                    artwork_id="other-artwork",
                    user_id="other-user",
                    preview_path="/static/previews/other.png",
                    pattern_json=pattern_one,
                    style_preset="q_pet",
                    size_preset="104x104",
                    title="别人的作品",
                    created_at=datetime(2026, 1, 4, tzinfo=timezone.utc),
                ),
            ]
        )
        session.commit()

    anonymous_page = client.get("/api/artwork/gallery")
    assert anonymous_page.status_code == 200
    assert anonymous_page.json()["total"] == 0
    assert anonymous_page.json()["items"] == []

    default_page = client.get("/api/artwork/gallery", headers=headers)
    assert default_page.status_code == 200
    assert default_page.json()["size"] == 12

    mobile_page = client.get("/api/artwork/gallery?page=1&size=4", headers=headers)
    assert mobile_page.status_code == 200
    assert mobile_page.json()["size"] == 4

    tablet_page = client.get("/api/artwork/gallery?page=1&size=6", headers=headers)
    assert tablet_page.status_code == 200
    assert tablet_page.json()["size"] == 6

    page_one = client.get("/api/artwork/gallery?page=1&size=2", headers=headers)
    assert page_one.status_code == 200
    payload = page_one.json()
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["size"] == 2
    assert payload["has_more"] is True
    assert [item["artwork_id"] for item in payload["items"]] == ["newest", "middle"]
    assert payload["items"][0]["bead_count"] == 4
    assert payload["items"][0]["color_count"] == 3
    assert "pattern_data" not in payload["items"][0]

    page_two = client.get("/api/artwork/gallery?page=2&size=2", headers=headers)
    assert page_two.status_code == 200
    payload = page_two.json()
    assert payload["has_more"] is False
    assert [item["artwork_id"] for item in payload["items"]] == ["older"]

    too_large = client.get("/api/artwork/gallery?page=1&size=21", headers=headers)
    assert too_large.status_code == 422


def test_email_code_login_uses_shared_db_and_returns_email_user(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    sent_codes = capture_email_codes(monkeypatch)

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


def test_web_password_register_login_and_duplicate_register(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    sent_codes = capture_email_codes(monkeypatch)

    sent = client.post("/api/user/email/send-code", json={"email": "Password.User@Example.COM"})
    assert sent.status_code == 200
    code = sent_codes[-1][1]

    registered = client.post(
        "/api/user/register",
        json={"email": "password.user@example.com", "code": code, "password": "secret123"},
    )
    assert registered.status_code == 200
    payload = registered.json()
    assert payload["token"]
    assert payload["user"]["email"] == "password.user@example.com"
    assert payload["cdk"]["success"] is False

    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == "password.user@example.com"))
        assert user is not None
        assert user.password_hash
        assert "secret123" not in user.password_hash
        assert user.password_hash.startswith("pbkdf2_sha256$")

    duplicate = client.post(
        "/api/user/register",
        json={"email": "password.user@example.com", "code": code, "password": "another123"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["message_cn"] == "该邮箱已注册，请登录。"

    logged_in = client.post(
        "/api/user/email-login",
        json={"email": "Password.User@Example.COM", "password": "secret123"},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["user_id"] == payload["user"]["user_id"]


def test_web_password_register_rejects_wrong_code_and_wrong_password(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _session_factory = api_client
    sent_codes = capture_email_codes(monkeypatch)

    sent = client.post("/api/user/email/send-code", json={"email": "wrong.code@example.com"})
    assert sent.status_code == 200
    code = sent_codes[-1][1]
    wrong_code = "000000" if code != "000000" else "111111"

    bad_register = client.post(
        "/api/user/register",
        json={"email": "wrong.code@example.com", "code": wrong_code, "password": "secret123"},
    )
    assert bad_register.status_code == 400
    assert bad_register.json()["error"] == "EMAIL_CODE_INVALID"

    assert client.post("/api/user/email/send-code", json={"email": "login.fail@example.com"}).status_code == 200
    valid_code = sent_codes[-1][1]
    assert client.post(
        "/api/user/register",
        json={"email": "login.fail@example.com", "code": valid_code, "password": "secret123"},
    ).status_code == 200

    wrong_password = client.post(
        "/api/user/email-login",
        json={"email": "login.fail@example.com", "password": "wrong-password"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["message_cn"] == "密码不正确，请重新输入。"

    missing_user = client.post(
        "/api/user/email-login",
        json={"email": "not.registered@example.com", "password": "secret123"},
    )
    assert missing_user.status_code == 404
    assert missing_user.json()["message_cn"] == "邮箱未注册，请先注册。"


def test_web_password_register_with_cdk_grants_credits(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    sent_codes = capture_email_codes(monkeypatch)
    code_value = "REGCDKABCDEFGHJKL"

    with session_factory() as session:
        CDKService(session).create_cdk(code=code_value, cdk_type="credit_pack_5", value=5)

    assert client.post("/api/user/email/send-code", json={"email": "cdk.register@example.com"}).status_code == 200
    email_code = sent_codes[-1][1]
    registered = client.post(
        "/api/user/register",
        json={
            "email": "cdk.register@example.com",
            "code": email_code,
            "password": "secret123",
            "cdk": code_value.lower(),
        },
    )
    assert registered.status_code == 200
    payload = registered.json()
    assert payload["cdk"]["success"] is True
    assert payload["cdk"]["value"] == 5
    assert payload["user"]["paid_credits"] == 6

    with session_factory() as session:
        cdk = session.get(CDK, code_value)
        assert cdk is not None
        assert cdk.status == "redeemed"
        assert cdk.redeemed_by == payload["user"]["user_id"]


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


def test_upload_rejects_disguised_or_oversized_pixel_images(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)

    disguised_svg = client.post(
        "/api/upload",
        files={"image": ("sample.png", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/png")},
        headers=headers,
    )
    assert disguised_svg.status_code == 415

    mismatched = client.post(
        "/api/upload",
        files={"image": ("sample.png", image_bytes(image_format="JPEG"), "image/png")},
        headers=headers,
    )
    assert mismatched.status_code == 415

    monkeypatch.setattr("pindou.api.storage.MAX_IMAGE_PIXELS", 100)
    too_many_pixels = client.post(
        "/api/upload",
        files={"image": ("sample.png", png_bytes(), "image/png")},
        headers=headers,
    )
    assert too_many_pixels.status_code == 413


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
    client, session_factory = api_client
    headers = auth_headers(client)
    image_id = upload_image(client, headers)

    missing = client.post("/api/generate/script", json={"image_id": "missing", "size": "26x26"}, headers=headers)
    assert missing.status_code == 404

    generated = client.post("/api/generate/script", json={"image_id": image_id, "size": "26x26"}, headers=headers)
    assert generated.status_code == 200
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        # Standard generation is free; allowances are left untouched.
        assert user.free_credits_remaining == 3
        assert user.paid_credits == 1
    artwork_id = generated.json()["artwork_id"]
    assert generated.json()["pattern"]["metadata"]["artwork_id"] == artwork_id
    assert generated.json()["pattern"]["metadata"]["labeled_image_url"].endswith("_with_grid.png")

    assert client.get("/api/artwork/list", headers=headers).json()[0]["artwork_id"] == artwork_id
    assert client.get(f"/api/artwork/{artwork_id}", headers=headers).status_code == 200
    assert client.get(f"/api/pattern/{artwork_id}", headers=headers).status_code == 200
    assert client.delete(f"/api/artwork/{artwork_id}", headers=headers).json() == {"success": True}
    assert client.get(f"/api/artwork/{artwork_id}", headers=headers).status_code == 404


def test_standard_generation_is_free_without_any_allowance(api_client) -> None:
    client, session_factory = api_client
    user_id = "wx_no_allowance"
    with session_factory() as session:
        session.add(User(openid=user_id, nickname="Zero", avatar="", free_credits_remaining=0, paid_credits=0,
                         sensitive_consent_at=datetime.now(timezone.utc)))
        session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(subject=user_id)}"}
    for _ in range(4):
        response = client.post(
            "/api/v1/generate/script",
            data={"size": "26x26", "mode": "script"},
            files={"raw_image": ("sample.png", png_bytes((40, 120, 200)), "image/png")},
            headers=headers,
        )
        assert response.status_code == 200
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid == user_id))
        assert user is not None and user.free_credits_remaining == 0 and user.paid_credits == 0


def test_save_artwork_pattern_rebuilds_counts_and_exports_png(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)
    image_id = upload_image(client, headers)

    generated = client.post("/api/generate/script", json={"image_id": image_id, "size": "26x26"}, headers=headers)
    assert generated.status_code == 200
    artwork_id = generated.json()["artwork_id"]
    pattern = generated.json()["pattern"]
    replacement_color = {
        "brand": "MARD",
        "code": "H7",
        "name_cn": "H7",
        "name_en": "H7",
        "hex": "#F05050",
        "rgb": [240, 80, 80],
        "bead_diameter_mm": 5.0,
    }

    pattern["grid"][0][0] = replacement_color
    pattern["palette_used"].append(replacement_color)
    pattern["color_counts"] = {}
    pattern["bead_total"] = 0
    pattern["metadata"]["thumbnail_url"] = "/static/patterns/stale_thumb.png"

    saved = client.put(f"/api/artwork/{artwork_id}/pattern", json={"pattern_json": pattern}, headers=headers)
    assert saved.status_code == 200
    payload = saved.json()
    saved_pattern = payload["pattern"]
    assert payload["success"] is True
    assert payload["pattern_url"].endswith(f"pattern_{artwork_id}.json")
    assert saved_pattern["grid"][0][0]["code"] == "H7"
    assert saved_pattern["color_counts"]["H7"] >= 1
    assert saved_pattern["bead_total"] > 0
    assert saved_pattern["metadata"]["labeled_image_url"].endswith("_with_grid.png")
    assert saved_pattern["metadata"].get("thumbnail_url") != "/static/patterns/stale_thumb.png"
    assert payload["artwork"]["preview_url"] == saved_pattern["metadata"]["labeled_image_url"]

    detail = client.get(f"/api/artwork/{artwork_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["pattern_data"]["grid"][0][0]["code"] == "H7"

    fast_pattern = json.loads(json.dumps(saved_pattern))
    fast_color = {
        "brand": "MARD",
        "code": "G11",
        "name_cn": "G11",
        "name_en": "G11",
        "hex": "#5050F0",
        "rgb": [80, 80, 240],
        "bead_diameter_mm": 5.0,
    }
    original_labeled_url = saved_pattern["metadata"]["labeled_image_url"]
    fast_pattern["grid"][0][1] = fast_color
    fast_pattern["palette_used"].append(fast_color)

    fast_saved = client.put(
        f"/api/artwork/{artwork_id}/pattern",
        json={"pattern_json": fast_pattern, "render_preview": False},
        headers=headers,
    )
    assert fast_saved.status_code == 200
    fast_payload = fast_saved.json()
    assert fast_payload["pattern"]["grid"][0][1]["code"] == "G11"
    assert fast_payload["pattern"]["metadata"]["labeled_image_url"] == original_labeled_url
    assert fast_payload["artwork"]["preview_url"] == original_labeled_url


def test_unlimited_credit_email_skips_normal_credit_consumption(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    monkeypatch.setenv("UNLIMITED_CREDIT_EMAILS", " StayWithCSQ@Outlook.com ")
    get_settings.cache_clear()
    user_id = "email_unlimited_script"

    with session_factory() as session:
        user = User(
            openid=user_id,
            email="staywithcsq@outlook.com",
            nickname="Stay",
            avatar="",
            free_credits_remaining=0,
            paid_credits=0,
            sensitive_consent_at=datetime.now(timezone.utc),
        )
        quota = DailyQuota(
            user_id=user_id,
            date=date.today(),
            script_used=3,
            white_bg_used=1,
        )
        session.add_all([user, quota])
        session.commit()

    response = client.post(
        "/api/v1/generate/script",
        data={"size": "26x26", "mode": "script"},
        files={"raw_image": ("sample.png", png_bytes((240, 240, 240)), "image/png")},
        headers={"Authorization": f"Bearer {create_access_token(subject=user_id)}"},
    )
    assert response.status_code == 200
    assert response.json()["artwork_id"]

    with session_factory() as session:
        quota = session.scalar(select(DailyQuota).where(DailyQuota.user_id == user_id))
        assert quota is not None
        assert quota.script_used == 3
        assert quota.white_bg_used == 1
        user = session.scalar(select(User).where(User.openid == user_id))
        assert user is not None
        assert user.free_credits_remaining == 0
        assert user.paid_credits == 0


def test_generate_ai_endpoint_with_mocked_provider(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        grant_points(
            session,
            owner_id=user.user_id,
            amount=2 * AI_GENERATION_POINT_COST,
            kind="paid",
            source_type="test",
            source_id="generate_ai_two_runs",
        )
        session.commit()
    calls = []

    class FakeChain:
        def generate(self, image: bytes, style_preset, size_preset, seed=None) -> PreviewResult:
            calls.append({"style": style_preset.value, "size": size_preset.value, "seed": seed, "bytes": len(image)})
            return PreviewResult.from_image_bytes(
                png_bytes((255, 255, 255)),
                target_color_count=8,
                provider_used="fake",
                cost_estimate=0.0,
                latency_ms=10,
            )

    monkeypatch.setattr("pindou.api.generate.build_preview_chain", lambda: FakeChain())
    web_form = client.post(
        "/api/v1/generate/ai",
        data={"style_preset": "q_pet", "size_preset": "52x52"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers=headers,
    )
    assert web_form.status_code == 200
    form_job = wait_generation_job(client, headers, web_form.json()["job_id"])
    assert form_job["status"] == "succeeded"
    assert form_job["progress"] == 100
    assert form_job["result"]["preview"]["provider_used"] == "fake"
    assert form_job["result"]["pattern"]["metadata"]["size_preset"] == "52x52"
    assert form_job["result"]["pattern"]["metadata"]["target_colors"] == 8
    assert calls[-1]["style"] == "q_pet"
    assert calls[-1]["size"] == "52x52"
    assert calls[-1]["bytes"] > 0

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
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        assert user.free_credits_remaining == 3
        assert get_credit_balance(session, owner_id=user.user_id).available == 188


def test_generate_ai_refuses_script_fallback(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)

    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        before_free_credits = user.free_credits_remaining
        before_ai_credits = user.paid_credits
        before_artworks = len(session.scalars(select(Artwork)).all())

    class FakeFallbackChain:
        def generate(self, image: bytes, style_preset, size_preset, seed=None) -> PreviewResult:
            return PreviewResult.from_image_bytes(
                png_bytes((255, 255, 255)),
                target_color_count=8,
                provider_used="fallback_quantize",
                fallback_count=1,
                cost_estimate=0.0,
                latency_ms=10,
            )

    monkeypatch.setattr("pindou.api.generate.build_preview_chain", lambda: FakeFallbackChain())
    response = client.post(
        "/api/v1/generate/ai",
        data={"style_preset": "q_portrait", "size_preset": "52x52"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers=headers,
    )
    assert response.status_code == 200
    finished = wait_generation_job(client, headers, response.json()["job_id"])
    assert finished["status"] == "failed"
    assert finished["error"]["code"] == "PREVIEW_FAILED"
    assert finished["error"]["message_cn"] == "AI 生成暂时失败，请稍后重试或切换普通模式。"

    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        assert user.free_credits_remaining == before_free_credits
        assert user.paid_credits == before_ai_credits
        assert len(session.scalars(select(Artwork)).all()) == before_artworks


def test_reserved_ai_credit_refund_is_idempotent(api_client) -> None:
    _client, session_factory = api_client
    with session_factory() as session:
        user = User(openid="refund_user", nickname="Refund", paid_credits=0)
        job = GenerationJob(user_id=user.openid, mode="ai", ai_credit_reserved=True, ai_credit_refunded=False)
        session.add_all([user, job])
        session.commit()
        job_id = job.job_id

        refund_reserved_ai_credit(session, job_id=job_id, user_id=user.openid)
        refund_reserved_ai_credit(session, job_id=job_id, user_id=user.openid)

        session.refresh(user)
        refunded = session.get(GenerationJob, job_id)
        assert user.paid_credits == 1
        assert refunded is not None
        assert refunded.ai_credit_refunded is True


def test_preview_generate_refuses_fallback_and_refunds_ai_credit(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        before_ai_credits = user.paid_credits

    class FakeFallbackChain:
        def generate(self, image: bytes, style_preset, size_preset, seed=None) -> PreviewResult:
            return PreviewResult.from_image_bytes(
                png_bytes((255, 255, 255)),
                target_color_count=8,
                provider_used="fallback_quantize",
                fallback_count=1,
                cost_estimate=0.0,
                latency_ms=10,
            )

    monkeypatch.setattr("pindou.api.generate.build_preview_chain", lambda: FakeFallbackChain())
    response = client.post(
        "/api/v1/preview/generate",
        data={"style_preset": "q_portrait", "size_preset": "26x26"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers=headers,
    )
    assert response.status_code == 500
    assert response.json()["message_cn"] == "AI 生成暂时失败，请稍后再试。"
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        assert user.paid_credits == before_ai_credits


def test_unlimited_credit_email_skips_ai_credit_requirement(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    monkeypatch.setenv("UNLIMITED_CREDIT_EMAILS", "staywithcsq@outlook.com")
    get_settings.cache_clear()
    user_id = "email_unlimited_ai"

    with session_factory() as session:
        user = User(
            openid=user_id,
            email="staywithcsq@outlook.com",
            nickname="Stay",
            avatar="",
            free_credits_remaining=0,
            paid_credits=0,
            sensitive_consent_at=datetime.now(timezone.utc),
        )
        session.add(user)
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
        headers={"Authorization": f"Bearer {create_access_token(subject=user_id)}"},
    )
    assert response.status_code == 200
    assert response.json()["provider_used"] == "fake"

    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid == user_id))
        assert user is not None
        assert user.free_credits_remaining == 0
        assert user.paid_credits == 0


def test_preview_generate_rejects_monthly_card_without_ai_points(api_client) -> None:
    client, session_factory = api_client
    user_id = "monthly_no_ai_points"

    with session_factory() as session:
        user = User(
            openid=user_id,
            nickname="Monthly",
            avatar="",
            free_credits_remaining=0,
            paid_credits=0,
            monthly_card_expires_at=datetime(2099, 1, 1, 0, 0, 0),
            sensitive_consent_at=datetime.now(timezone.utc),
        )
        user.membership_expires_at = user.monthly_card_expires_at
        session.add(user)
        session.commit()
    response = client.post(
        "/api/v1/preview/generate",
        data={"style_preset": "q_portrait", "size_preset": "26x26"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers={"Authorization": f"Bearer {create_access_token(subject=user_id)}"},
    )
    assert response.status_code == 429
    assert "AI 积分不足" in response.json()["message_cn"]


def test_payment_and_admin_read_only_flow(api_client) -> None:
    client, _session_factory = api_client
    headers = auth_headers(client)
    unauthorized = client.get("/api/admin/orders")
    assert unauthorized.status_code == 401

    skus = client.get("/api/payment/skus")
    assert skus.status_code == 200
    sku_payload = skus.json()
    assert sku_payload["ai_generation_cost_points"] == AI_GENERATION_POINT_COST
    assert [item["sku"] for item in sku_payload["items"] if item["category"] == "points"] == [
        "points_trial_099",
        "points_standard_990",
        "points_value_2990",
    ]
    # Time cards are off sale; they must not be listed.
    assert [item["sku"] for item in sku_payload["items"] if item["category"] == "membership"] == []
    assert all(item["sku"] not in {"single_9.9", "monthly_28", "custom_99"} for item in sku_payload["items"])

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


def test_admin_login_failed_attempts_are_rate_limited(api_client, caplog: pytest.LogCaptureFixture) -> None:
    client, _session_factory = api_client
    headers = {"x-forwarded-for": "203.0.113.77"}
    caplog.set_level("WARNING", logger="pindou.api.admin")

    for _index in range(5):
        response = client.post(
            "/api/admin/login",
            json={"username": "limited-admin", "password": "wrong"},
            headers=headers,
        )
        assert response.status_code == 401
        assert response.json()["message_cn"] == "管理员账号或密码不正确。"
    locked = client.post(
        "/api/admin/login",
        json={"username": "limited-admin", "password": "wrong"},
        headers=headers,
    )
    assert locked.status_code == 429
    assert locked.json()["message_cn"] == "管理员登录尝试太频繁，请稍后再试。"
    assert "admin_login_failed" in caplog.text
    assert "admin_username_matches" in caplog.text
    assert "password_matches" in caplog.text
    assert "wrong" not in caplog.text


def test_production_config_requires_real_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("APP_CORS_ALLOW_ORIGINS", "*")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="Production configuration is not safe to start"):
        create_app()
    get_settings.cache_clear()


def test_admin_two_step_order_fulfillment_is_audited_and_idempotent(api_client) -> None:
    client, session_factory = api_client
    with session_factory() as session:
        user = User(openid="manual_user", nickname="Manual", avatar="", paid_credits=0)
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


def test_hupijiao_webhook_marks_order_paid_and_grants_monthly_card(api_client, monkeypatch) -> None:
    # Orders placed before the time-card sale ended must still be fulfilled.
    monkeypatch.setitem(payment_api.SKU_CATALOG["membership_month_1990"], "active", True)
    client, session_factory = api_client
    headers = auth_headers(client)
    order = client.post("/api/payment/order/create", json={"sku_id": "monthly_28"}, headers=headers)
    assert order.status_code == 200
    payload = order.json()
    assert payload["payment_provider"] == "hupijiao"
    assert payload["qr_code_url"]

    webhook_payload = {
        "trade_order_id": payload["order_no"],
        "total_fee": "19.90",
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
        assert user.membership_expires_at is not None
        assert get_credit_balance(session, owner_id=user.user_id).gift >= 1888
        expires_at = user.monthly_card_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at < datetime.now(timezone.utc) + timedelta(days=31)


def test_hupijiao_webhook_grants_points_pack_idempotently(api_client) -> None:
    client, session_factory = api_client
    headers = auth_headers(client)
    order = client.post("/api/payment/order/create", json={"sku_id": "points_trial_099"}, headers=headers)
    assert order.status_code == 200
    payload = order.json()
    webhook_payload = {
        "trade_order_id": payload["order_no"],
        "total_fee": "0.99",
        "transaction_id": "MOCKTXN_POINTS",
        "open_order_id": "OPEN_POINTS",
        "order_title": "PinDou 体验积分包",
        "status": "OD",
        "appid": "mock",
        "time": "1760000000",
        "nonce_str": "mocknonce-points",
    }
    webhook_payload["hash"] = sign_params(webhook_payload, "pindou-dev-hupijiao-mock-secret")

    assert client.post("/api/v1/webhook/hupijiao", data=webhook_payload).status_code == 200
    assert client.post("/api/v1/webhook/hupijiao", data=webhook_payload).status_code == 200
    with session_factory() as session:
        user = session.scalar(select(User).where(User.openid.like("wx_%")))
        assert user is not None
        balance = get_credit_balance(session, owner_id=user.user_id)
        assert balance.available == 188 + 200
        assert balance.paid == 200


def test_time_card_orders_are_off_sale(api_client) -> None:
    client, _ = api_client
    headers = auth_headers(client)
    for sku in ("membership_week_990", "membership_month_1990", "membership_season_4990", "monthly_card"):
        order = client.post("/api/payment/order/create", json={"sku_id": sku}, headers=headers)
        assert order.status_code == 422
    assert client.post("/api/payment/order/create", json={"sku_id": "points_standard_990"}, headers=headers).status_code == 200


def test_hupijiao_webhook_rejects_missing_amount(api_client, monkeypatch) -> None:
    # Orders placed before the time-card sale ended must still be fulfilled.
    monkeypatch.setitem(payment_api.SKU_CATALOG["membership_month_1990"], "active", True)
    client, session_factory = api_client
    headers = auth_headers(client)
    order = client.post("/api/payment/order/create", json={"sku_id": "monthly_28"}, headers=headers)
    assert order.status_code == 200
    payload = order.json()

    webhook_payload = {
        "trade_order_id": payload["order_no"],
        "transaction_id": "MOCKTXN_NO_AMOUNT",
        "status": "OD",
        "appid": "mock",
        "time": "1760000000",
        "nonce_str": "mocknonce-no-amount",
    }
    webhook_payload["hash"] = sign_params(webhook_payload, "pindou-dev-hupijiao-mock-secret")
    callback = client.post("/api/v1/webhook/hupijiao", data=webhook_payload)
    assert callback.status_code == 400

    with session_factory() as session:
        stored = session.scalar(select(Order).where(Order.order_no == payload["order_no"]))
        assert stored is not None
        assert stored.status == "pending_qr"


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


def test_wallet_profile_issues_signed_device_and_rejects_tampered_token(api_client) -> None:
    client, _ = api_client
    first = client.get("/api/wallet/profile")
    assert first.status_code == 200
    payload = first.json()
    assert payload["owner_type"] == "device"
    assert payload["is_anonymous"] is True
    assert payload["normal_trial_remaining"] == 0
    assert payload["device_token"]
    assert "pd_device=" in first.headers.get("set-cookie", "")

    token = payload["device_token"]
    repeated = client.get("/api/wallet/profile", headers={"X-PinDou-Device": token})
    assert repeated.status_code == 200
    assert repeated.json()["owner_id"] == payload["owner_id"]

    client.cookies.clear()
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    forged = client.get("/api/wallet/profile", headers={"X-PinDou-Device": tampered})
    assert forged.status_code == 200
    assert forged.json()["owner_type"] == "device"
    assert forged.json()["owner_id"] != payload["owner_id"]
    assert forged.json()["ai_points_balance"] == 0


def test_anonymous_cdk_redeem_grants_device_wallet(api_client) -> None:
    client, session_factory = api_client
    wallet = client.get("/api/wallet/profile")
    assert wallet.status_code == 200
    token = wallet.json()["device_token"]
    device_id = wallet.json()["device_id"]

    with session_factory() as session:
        service = CDKService(session)
        service.create_cdk(code="DEVICEPOINTSABCDEFG", cdk_type="points", value=200)
        service.create_cdk(code="DEVICEMEMBERABCDEFG", cdk_type="membership", value=7)

    headers = {"X-PinDou-Device": token}
    points = client.post("/api/cdk/redeem", json={"cdk_code": "DEVICEPOINTSABCDEFG"}, headers=headers)
    assert points.status_code == 200
    assert points.json()["owner_type"] == "device"
    assert points.json()["is_anonymous"] is True
    assert points.json()["device_token"] == token

    membership = client.post("/api/cdk/redeem", json={"cdk_code": "DEVICEMEMBERABCDEFG"}, headers=headers)
    assert membership.status_code == 200

    refreshed = client.get("/api/wallet/profile", headers=headers).json()
    assert refreshed["owner_id"] == device_id
    assert refreshed["ai_points_balance"] == 200
    assert refreshed["membership_expires_at"] is not None

    with session_factory() as session:
        balance = get_credit_balance(session, owner_type="device", owner_id=device_id)
        assert balance.available == 200
        assert session.get(CDK, "DEVICEPOINTSABCDEFG").redeemed_owner_type == "device"
        assert session.get(CDK, "DEVICEPOINTSABCDEFG").redeemed_owner_id == device_id
        assert session.get(CDK, "DEVICEPOINTSABCDEFG").redeemed_by is None
        assert (
            session.query(MembershipGrant)
            .filter(MembershipGrant.owner_type == "device", MembershipGrant.owner_id == device_id)
            .count()
            == 1
        )


def test_anonymous_device_with_membership_can_generate_and_owns_artwork(api_client) -> None:
    client, session_factory = api_client
    wallet = client.get("/api/wallet/profile")
    assert wallet.status_code == 200
    token = wallet.json()["device_token"]
    device_id = wallet.json()["device_id"]
    headers = {"X-PinDou-Device": token}

    # Standard generation is free since 2026-10-17, so a device without any allowance can generate.
    free = client.post(
        "/api/generate/script",
        data={"size": "26x26", "auto_remove_white_bg": "true"},
        files={"raw_image": ("sample.png", png_bytes(), "image/png")},
        headers=headers,
    )
    assert free.status_code == 200

    with session_factory() as session:
        CDKService(session).create_cdk(code="DEVICEGENMEMBERABC", cdk_type="membership", value=7)

    redeemed = client.post("/api/cdk/redeem", json={"cdk_code": "DEVICEGENMEMBERABC"}, headers=headers)
    assert redeemed.status_code == 200
    assert redeemed.json()["owner_type"] == "device"

    generated = client.post(
        "/api/generate/script",
        data={"size": "26x26", "auto_remove_white_bg": "true"},
        files={"raw_image": ("sample.png", png_bytes(), "image/png")},
        headers=headers,
    )
    assert generated.status_code == 200
    artwork_id = generated.json()["artwork_id"]

    with session_factory() as session:
        artwork = session.get(Artwork, artwork_id)
        assert artwork is not None
        assert artwork.user_id is None
        assert artwork.owner_type == "device"
        assert artwork.owner_id == device_id

    detail = client.get(f"/api/artwork/{artwork_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["owner_type"] == "device"
    assert client.get(f"/api/pattern/{artwork_id}", headers=headers).status_code == 200
    gallery = client.get("/api/artwork/gallery", headers=headers)
    assert gallery.status_code == 200
    assert gallery.json()["total"] == 2
    assert artwork_id in {item["artwork_id"] for item in gallery.json()["items"]}

    client.cookies.clear()
    stranger_wallet = client.get("/api/wallet/profile")
    stranger_token = stranger_wallet.json()["device_token"]
    stranger_headers = {"X-PinDou-Device": stranger_token}
    assert stranger_wallet.json()["device_id"] != device_id
    assert client.get(f"/api/artwork/{artwork_id}", headers=stranger_headers).status_code == 404
    assert client.get(f"/api/pattern/{artwork_id}", headers=stranger_headers).status_code == 404
    stranger_gallery = client.get("/api/artwork/gallery", headers=stranger_headers)
    assert stranger_gallery.status_code == 200
    assert stranger_gallery.json()["total"] == 0


def test_anonymous_device_with_points_can_generate_ai_and_poll_result(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = api_client
    wallet = client.get("/api/wallet/profile")
    assert wallet.status_code == 200
    token = wallet.json()["device_token"]
    device_id = wallet.json()["device_id"]
    headers = {"X-PinDou-Device": token}

    no_points = client.post(
        "/api/generate/ai",
        data={"style_preset": "q_pet", "size_preset": "52x52"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers=headers,
    )
    assert no_points.status_code == 402
    assert no_points.json()["details"]["kind"] == "ai"
    assert no_points.json()["details"]["missing"] == "points"

    with session_factory() as session:
        grant_points(
            session,
            owner_type="device",
            owner_id=device_id,
            amount=AI_GENERATION_POINT_COST,
            kind="paid",
            source_type="test",
            source_id="anonymous_ai",
        )
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
    submitted = client.post(
        "/api/generate/ai",
        data={"style_preset": "q_pet", "size_preset": "52x52"},
        files={"image": ("sample.png", png_bytes((255, 255, 255)), "image/png")},
        headers=headers,
    )
    assert submitted.status_code == 200
    job_id = submitted.json()["job_id"]
    finished = wait_generation_job(client, headers, job_id)
    assert finished["status"] == "succeeded"
    artwork_id = finished["result"]["artwork_id"]

    with session_factory() as session:
        assert get_credit_balance(session, owner_type="device", owner_id=device_id).available == 0
        job = session.get(GenerationJob, job_id)
        assert job is not None
        assert job.user_id is None
        assert job.owner_type == "device"
        assert job.owner_id == device_id
        artwork = session.get(Artwork, artwork_id)
        assert artwork is not None
        assert artwork.user_id is None
        assert artwork.owner_type == "device"
        assert artwork.owner_id == device_id

    assert client.get(f"/api/artwork/{artwork_id}", headers=headers).status_code == 200
    client.cookies.clear()
    stranger = client.get("/api/wallet/profile").json()
    stranger_headers = {"X-PinDou-Device": stranger["device_token"]}
    assert stranger["device_id"] != device_id
    assert client.get(f"/api/generate/status/{job_id}", headers=stranger_headers).status_code == 404
    assert client.get(f"/api/artwork/{artwork_id}", headers=stranger_headers).status_code == 404


def test_register_migrates_anonymous_device_wallet_artwork_and_jobs_and_retires_device(
    api_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    sent_codes = capture_email_codes(monkeypatch)
    wallet = client.get("/api/wallet/profile")
    assert wallet.status_code == 200
    old_token = wallet.json()["device_token"]
    old_device_id = wallet.json()["device_id"]
    old_headers = {"X-PinDou-Device": old_token}

    with session_factory() as session:
        service = CDKService(session)
        service.create_cdk(code="MIGRATEPOINTSABC", cdk_type="points", value=200)
        service.create_cdk(code="MIGRATEMEMBERABC", cdk_type="membership", value=7)

    assert client.post("/api/cdk/redeem", json={"cdk_code": "MIGRATEPOINTSABC"}, headers=old_headers).status_code == 200
    assert client.post("/api/cdk/redeem", json={"cdk_code": "MIGRATEMEMBERABC"}, headers=old_headers).status_code == 200

    generated = client.post(
        "/api/generate/script",
        data={"size": "26x26", "auto_remove_white_bg": "true"},
        files={"raw_image": ("sample.png", png_bytes(), "image/png")},
        headers=old_headers,
    )
    assert generated.status_code == 200
    artwork_id = generated.json()["artwork_id"]

    with session_factory() as session:
        pending_job = GenerationJob(
            job_id="pending-device-migration-job",
            user_id=None,
            owner_type="device",
            owner_id=old_device_id,
            status="queued",
            mode="ai",
            progress=5,
            stage="queued",
            message_cn="等待中",
        )
        session.add(pending_job)
        session.commit()

    assert client.post("/api/user/email/send-code", json={"email": "device.move@example.com"}).status_code == 200
    email_code = sent_codes[-1][1]
    registered = client.post(
        "/api/user/register",
        json={"email": "device.move@example.com", "code": email_code, "password": "secret123"},
        headers=old_headers,
    )
    assert registered.status_code == 200
    payload = registered.json()
    user_id = payload["user"]["user_id"]
    assert payload["device_token"] and payload["device_token"] != old_token
    assert payload["device_id"] != old_device_id
    assert payload["device_migration"]["status"] == "migrated"
    assert payload["device_migration"]["moved_artworks"] == 1
    assert payload["device_migration"]["moved_jobs"] == 1
    assert payload["device_migration"]["moved_cdks"] == 2
    assert payload["user"]["ai_points_balance"] == 200 + 188
    assert payload["user"]["membership_expires_at"] is not None

    auth = {"Authorization": f"Bearer {payload['token']}"}
    detail = client.get(f"/api/artwork/{artwork_id}", headers=auth)
    assert detail.status_code == 200
    assert detail.json()["owner_type"] == "user"
    assert detail.json()["user_id"] == user_id
    pending = client.get("/api/generate/status/pending-device-migration-job", headers=auth)
    assert pending.status_code == 200
    gallery = client.get("/api/artwork/gallery", headers=auth)
    assert gallery.status_code == 200
    assert gallery.json()["total"] == 1

    with session_factory() as session:
        claim = session.get(DeviceClaim, old_device_id)
        assert claim is not None
        assert claim.claimed_by_user_id == user_id
        assert session.query(CreditGrant).filter(CreditGrant.owner_type == "device", CreditGrant.owner_id == old_device_id).count() == 0
        assert session.query(MembershipGrant).filter(MembershipGrant.owner_type == "device", MembershipGrant.owner_id == old_device_id).count() == 0
        migrated_artwork = session.get(Artwork, artwork_id)
        assert migrated_artwork is not None
        assert migrated_artwork.owner_type == "user"
        assert migrated_artwork.owner_id == user_id
        migrated_job = session.get(GenerationJob, "pending-device-migration-job")
        assert migrated_job is not None
        assert migrated_job.owner_type == "user"
        assert migrated_job.owner_id == user_id
        assert session.get(CDK, "MIGRATEPOINTSABC").redeemed_owner_type == "user"
        assert session.get(CDK, "MIGRATEPOINTSABC").redeemed_by == user_id

    retired = client.get("/api/wallet/profile", headers=old_headers)
    assert retired.status_code == 200
    assert retired.json()["owner_type"] == "device"
    assert retired.json()["device_id"] != old_device_id
    assert retired.json()["ai_points_balance"] == 0
    assert client.get(f"/api/artwork/{artwork_id}", headers=old_headers).status_code == 404


def test_device_migration_is_idempotent_and_blocks_second_account(api_client) -> None:
    client, session_factory = api_client
    wallet = client.get("/api/wallet/profile")
    old_token = wallet.json()["device_token"]
    old_device_id = wallet.json()["device_id"]
    old_headers = {"X-PinDou-Device": old_token}

    with session_factory() as session:
        grant_points(
            session,
            owner_type="device",
            owner_id=old_device_id,
            amount=300,
            kind="paid",
            source_type="test",
            source_id="first_claim",
        )
        session.commit()

    first = client.post("/api/user/login", json={"code": "claim-owner", "nickname": "Owner"}, headers=old_headers)
    assert first.status_code == 200
    first_payload = first.json()
    first_user_id = first_payload["user"]["user_id"]
    assert first_payload["device_migration"]["status"] == "migrated"
    assert first_payload["user"]["ai_points_balance"] == 300 + 188

    repeated = client.post("/api/user/login", json={"code": "claim-owner", "nickname": "Owner"}, headers=old_headers)
    assert repeated.status_code == 200
    assert repeated.json()["device_migration"]["status"] == "already_claimed_by_user"
    assert repeated.json()["user"]["ai_points_balance"] == 300 + 188

    with session_factory() as session:
        grant_points(
            session,
            owner_type="device",
            owner_id=old_device_id,
            amount=1000,
            kind="paid",
            source_type="test",
            source_id="stale_claimed_device",
        )
        session.commit()

    second = client.post("/api/user/login", json={"code": "second-owner", "nickname": "Second"}, headers=old_headers)
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["user"]["user_id"] != first_user_id
    assert second_payload["device_migration"]["status"] == "claimed_by_other"
    assert second_payload["device_migration"]["claimed_by_user_id"] == first_user_id
    assert second_payload["user"]["ai_points_balance"] == 188

    with session_factory() as session:
        stale_balance = get_credit_balance(session, owner_type="device", owner_id=old_device_id)
        assert stale_balance.available == 1000
        claim = session.get(DeviceClaim, old_device_id)
        assert claim is not None
        assert claim.claimed_by_user_id == first_user_id
