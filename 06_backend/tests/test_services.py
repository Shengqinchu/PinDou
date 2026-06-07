from __future__ import annotations

import logging
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import pytest
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from pindou.api.errors import ApiException
from pindou.api.quota import consume_ai_credit, consume_script_quota
from pindou.db.models import AdminAuditLog, Artwork, Base, User
from pindou.services.admin_audit_service import write_audit
from pindou.services.artwork_service import ArtworkService
from pindou.services.cdk_service import CDKInvalidError, CDKRateLimitError, CDKService
from pindou.services.credit_service import (
    AI_GENERATION_POINT_COST,
    get_credit_balance,
    grant_points,
    reserve_points,
)
from pindou.services.payment_service import (
    InvalidOrderTransitionError,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_PAID,
    PaymentService,
)
from pindou.services.user_service import UserService
from pindou.tasks.delete_expired_originals import delete_expired_originals_once


def add_user(db_session: Session, openid: str = "openid_user") -> User:
    user = User(openid=openid, nickname="Tester")
    db_session.add(user)
    db_session.commit()
    return user


class FakeStorageBackend:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.uploads: list[tuple[str, str | None]] = []

    def upload(self, path: str, content: bytes, *, content_type: str | None = None) -> str:
        self.files[path] = content
        self.uploads.append((path, content_type))
        return path

    def download(self, path: str) -> bytes:
        return self.files[path]

    def delete(self, path: str) -> bool:
        return self.files.pop(path, None) is not None

    def exists(self, path: str) -> bool:
        return path in self.files

    def get_url(self, path: str) -> str:
        return f"https://cos.example.test/{path}"


def png_bytes(color: tuple[int, int, int] = (255, 128, 64)) -> bytes:
    output = BytesIO()
    Image.new("RGB", (64, 48), color).save(output, format="PNG")
    return output.getvalue()


def test_user_service_register_consent_and_quota(db_session: Session) -> None:
    service = UserService(db_session)

    user = service.register_or_login(openid="openid_login", nickname="Pin", avatar="/avatar.png")
    same_user = service.register_or_login(openid="openid_login", nickname="Dou")
    consent = service.record_consent(user_id=user.openid, consent_type="privacy", ip="127.0.0.1")
    quota = service.get_or_create_daily_quota(user_id=user.openid, quota_date=date(2026, 5, 25))
    same_quota = service.get_or_create_daily_quota(user_id=user.openid, quota_date=date(2026, 5, 25))

    assert same_user.id == user.id
    assert same_user.nickname == "Dou"
    assert consent.consent_type == "privacy"
    assert same_user.privacy_consent_at is not None
    assert quota.id == same_quota.id
    assert service.credit_summary(user.openid)["free_credits_remaining"] == 3
    assert service.credit_summary(user.openid)["paid_credits"] == 1
    assert service.credit_summary(user.openid)["ai_points_balance"] == 188


def test_normal_and_ai_credit_buckets_are_separate(db_session: Session) -> None:
    user = add_user(db_session, openid="quota_bucket_user")
    grant_points(
        db_session,
        owner_id=user.user_id,
        amount=AI_GENERATION_POINT_COST,
        kind="paid",
        source_type="test",
        source_id="quota_bucket_user",
    )

    consume_script_quota(db_session, user)
    db_session.refresh(user)
    assert user.free_credits_remaining == 2
    assert user.paid_credits == 1

    consume_ai_credit(db_session, user, reservation_key="test:quota_bucket_user:ai:1")
    db_session.refresh(user)
    assert user.free_credits_remaining == 2
    assert user.paid_credits == 0
    assert get_credit_balance(db_session, owner_id=user.user_id).available == 0

    with pytest.raises(ApiException):
        consume_ai_credit(db_session, user, reservation_key="test:quota_bucket_user:ai:2")
    db_session.refresh(user)
    assert user.free_credits_remaining == 2
    assert user.paid_credits == 0


def test_membership_unlocks_script_but_never_ai_points(db_session: Session) -> None:
    user = add_user(db_session, openid="membership_not_ai_user")
    user.free_credits_remaining = 0
    user.membership_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    user.monthly_card_expires_at = user.membership_expires_at
    db_session.add(user)
    db_session.commit()

    assert consume_script_quota(db_session, user) is False
    with pytest.raises(ApiException):
        consume_ai_credit(db_session, user, reservation_key="test:membership_not_ai_user:ai")
    assert get_credit_balance(db_session, owner_id=user.user_id).available == 0


def test_ai_point_reservation_is_atomic_under_concurrency(tmp_path) -> None:
    db_path = tmp_path / "credits.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with SessionTesting() as session:
        user = User(openid="concurrent_ai_user", nickname="Concurrent")
        session.add(user)
        session.flush()
        grant_points(
            session,
            owner_id=user.user_id,
            amount=AI_GENERATION_POINT_COST,
            kind="paid",
            source_type="test",
            source_id="concurrent_ai_user",
        )
        session.commit()

    def reserve_once(index: int) -> str:
        with SessionTesting() as session:
            try:
                reserve_points(
                    session,
                    owner_id="concurrent_ai_user",
                    amount=AI_GENERATION_POINT_COST,
                    reservation_key=f"test:concurrent_ai_user:{index}",
                )
                session.commit()
                return "reserved"
            except ApiException:
                return "quota_exceeded"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve_once, range(2)))

    assert results.count("reserved") == 1
    assert results.count("quota_exceeded") == 1
    with SessionTesting() as session:
        balance = get_credit_balance(session, owner_id="concurrent_ai_user")
        assert balance.available == 0
        assert balance.reserved == AI_GENERATION_POINT_COST


def test_artwork_service_save_list_delete_removes_original_file(db_session: Session, tmp_path) -> None:
    user = add_user(db_session)
    original = tmp_path / "original.png"
    original.write_bytes(b"fake image bytes")
    service = ArtworkService(db_session)

    artwork = service.save_artwork(
        user_id=user.openid,
        original_path=str(original),
        preview_path="/preview.png",
        pattern_json={"grid": [["01"]]},
        style_preset="chibi",
        size_preset="26x26",
        title="Kept pattern",
    )

    assert service.list_artworks(user_id=user.openid)[0].artwork_id == artwork.artwork_id
    assert service.delete_artwork(artwork_id=artwork.artwork_id, user_id=user.openid) is True
    assert not original.exists()
    assert service.get_artwork(artwork.artwork_id) is None


def test_artwork_thumbnail_uses_storage_backend_url(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    backend = FakeStorageBackend()
    monkeypatch.setattr("pindou.services.artwork_service.get_storage_backend", lambda: backend)

    source_key = "patterns/pattern_artwork_with_grid.png"
    backend.upload(source_key, png_bytes(), content_type="image/png")

    user = add_user(db_session)
    service = ArtworkService(db_session)
    artwork = service.save_artwork(
        user_id=user.openid,
        original_path="uploads/source.png",
        preview_path="",
        pattern_json={"metadata": {"labeled_image_url": backend.get_url(source_key)}},
        style_preset="script",
        size_preset="26x26",
        title="Storage thumbnail",
    )

    frontend_artwork = service.to_frontend_dict(artwork)
    expected_key = f"thumbnails/thumb_{artwork.artwork_id}.png"
    expected_url = backend.get_url(expected_key)

    assert frontend_artwork["thumbnail_url"] == expected_url
    assert not frontend_artwork["thumbnail_url"].startswith("/static/")
    assert (expected_key, "image/png") in backend.uploads
    assert backend.files[expected_key].startswith(b"\x89PNG")


def test_cdk_redeem_grants_credits_and_rate_limits(db_session: Session) -> None:
    user = add_user(db_session)
    service = CDKService(db_session)
    cdk = service.create_cdk(code="ABCDEFGHJKLMNPQRS", cdk_type="credit_pack_5", value=5)
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)

    redeemed = service.redeem(code=cdk.code, user_id=user.openid, ip="10.0.0.1", now=now)
    db_session.refresh(user)

    assert redeemed.status == "redeemed"
    assert user.paid_credits == 5
    assert get_credit_balance(db_session, owner_id=user.user_id).available == 5 * AI_GENERATION_POINT_COST

    for index in range(3):
        with pytest.raises(CDKInvalidError):
            service.redeem(
                code=f"MISSING{index}",
                user_id=user.openid,
                ip="10.0.0.1",
                now=now + timedelta(seconds=index),
            )
    with pytest.raises(CDKRateLimitError):
        service.redeem(code="MISSING4", user_id=user.openid, ip="10.0.0.1", now=now + timedelta(seconds=4))


def test_cdk_redeem_points_and_membership_types(db_session: Session) -> None:
    user = add_user(db_session, openid="new_cdk_user")
    service = CDKService(db_session)
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    points_cdk = service.create_cdk(code="POINTSABCDEFGHJKLM", cdk_type="points", value=200)
    membership_cdk = service.create_cdk(code="MEMBERABCDEFGHJKLM", cdk_type="membership", value=7)

    service.redeem(code=points_cdk.code, user_id=user.openid, ip="10.0.0.3", now=now)
    service.redeem(code=membership_cdk.code, user_id=user.openid, ip="10.0.0.3", now=now + timedelta(seconds=1))
    db_session.refresh(user)

    assert get_credit_balance(db_session, owner_id=user.user_id).available == 200
    assert user.membership_expires_at is not None
    assert user.membership_expires_at.date() == date(2026, 6, 1)


def test_cdk_redeem_monthly_card_extends_existing_expiry(db_session: Session) -> None:
    user = add_user(db_session, openid="monthly_cdk_user")
    user.monthly_card_expires_at = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
    db_session.add(user)
    db_session.commit()

    service = CDKService(db_session)
    cdk = service.create_cdk(code="MONTHLYABCDEFGHJK", cdk_type="monthly_card", value=15)
    redeemed = service.redeem(
        code=cdk.code,
        user_id=user.openid,
        ip="10.0.0.2",
        now=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc),
    )
    db_session.refresh(user)

    assert redeemed.status == "redeemed"
    assert user.monthly_card_expires_at is not None
    assert user.membership_expires_at is not None
    assert user.monthly_card_expires_at.date() == date(2026, 6, 14)


def test_cdk_ip_velocity_is_rate_limited(db_session: Session, caplog: pytest.LogCaptureFixture) -> None:
    service = CDKService(db_session)
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    caplog.set_level(logging.WARNING)

    for index in range(5):
        user = add_user(db_session, openid=f"ip_user_{index}")
        with pytest.raises(CDKInvalidError):
            service.redeem(
                code=f"MISSING{index}",
                user_id=user.openid,
                ip="203.0.113.8",
                now=now + timedelta(seconds=index),
            )

    user = add_user(db_session, openid="ip_user_limited")
    with pytest.raises(CDKRateLimitError):
        service.redeem(
            code="MISSING_LIMITED",
            user_id=user.openid,
            ip="203.0.113.8",
            now=now + timedelta(seconds=6),
        )
    assert "CDK redemption rate limited" in caplog.text


def test_payment_service_customer_service_qr_state_machine(db_session: Session) -> None:
    user = add_user(db_session)
    service = PaymentService(db_session)

    order = service.create_order(user_id=user.openid, sku="single_export", amount_cny="9.90")
    paid = service.transition_order(order_no=order.order_no, status=ORDER_STATUS_PAID, handler="cs-1")

    assert paid.status == ORDER_STATUS_PAID
    assert paid.paid_at is not None
    assert paid.customer_service_handler == "cs-1"
    with pytest.raises(InvalidOrderTransitionError):
        service.transition_order(order_no=order.order_no, status=ORDER_STATUS_CANCELLED)


def test_payment_service_normalizes_blank_optional_order_refs(db_session: Session) -> None:
    user = add_user(db_session)
    service = PaymentService(db_session)

    order = service.create_order(
        user_id=user.openid,
        sku="single_export",
        amount_cny="9.90",
        artwork_id=" ",
        qr_code_path="",
        cdk_code="\t",
    )

    assert order.artwork_id is None
    assert order.qr_code_path is None
    assert order.cdk_code is None


def test_write_audit_persists_backend_event(db_session: Session) -> None:
    audit_id = write_audit(
        actor_id="admin",
        actor_role="admin",
        action="admin.login",
        resource_type="admin_session",
        resource_id="admin",
        before=None,
        after={"result": "success"},
        reason="unit test",
        request_id="req-1",
        session=db_session,
    )

    audit = db_session.get(AdminAuditLog, audit_id)
    assert audit is not None
    assert audit.actor_id == "admin"
    assert audit.actor_role == "admin"
    assert audit.after_json == {"result": "success"}
    assert audit.request_id == "req-1"


def test_delete_expired_originals_once_marks_only_old_uploads(db_session: Session, tmp_path) -> None:
    user = add_user(db_session)
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    old_file = tmp_path / "old-original.png"
    fresh_file = tmp_path / "fresh-original.png"
    old_file.write_bytes(b"old")
    fresh_file.write_bytes(b"fresh")

    old_artwork = Artwork(
        user_id=user.openid,
        original_path=str(old_file),
        preview_path="/preview-old.png",
        pattern_json={"grid": [["01"]]},
        style_preset="chibi",
        size_preset="26x26",
        created_at=now - timedelta(days=31),
    )
    fresh_artwork = Artwork(
        user_id=user.openid,
        original_path=str(fresh_file),
        preview_path="/preview-fresh.png",
        pattern_json={"grid": [["02"]]},
        style_preset="chibi",
        size_preset="26x26",
        created_at=now - timedelta(days=2),
    )
    db_session.add_all([old_artwork, fresh_artwork])
    db_session.commit()

    deleted_count = delete_expired_originals_once(db_session, now=now, retention_days=30)
    refreshed_old = db_session.scalar(select(Artwork).where(Artwork.artwork_id == old_artwork.artwork_id))

    assert deleted_count == 1
    assert not old_file.exists()
    assert fresh_file.exists()
    assert refreshed_old is not None
    assert refreshed_old.original_deleted_at == now
