from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import Artwork, User
from pindou.services.artwork_service import ArtworkService
from pindou.services.cdk_service import CDKInvalidError, CDKRateLimitError, CDKService
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


def test_cdk_redeem_grants_credits_and_rate_limits(db_session: Session) -> None:
    user = add_user(db_session)
    service = CDKService(db_session)
    cdk = service.create_cdk(code="ABCDEFGHJKLMNPQRS", cdk_type="credit_pack_5", value=5)
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)

    redeemed = service.redeem(code=cdk.code, user_id=user.openid, ip="10.0.0.1", now=now)
    db_session.refresh(user)

    assert redeemed.status == "redeemed"
    assert user.paid_credits == 5

    CDKService._attempts = []
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


def test_cdk_ip_velocity_logs_warning(db_session: Session, caplog: pytest.LogCaptureFixture) -> None:
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

    assert "Suspicious CDK redemption velocity" in caplog.text


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
