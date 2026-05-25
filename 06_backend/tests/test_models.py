from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import Artwork, CDK, ConsentLog, DailyQuota, Order, User


def test_phase2_models_crud_and_frontend_mapping(db_session: Session) -> None:
    user = User(openid="wechat_openid_1", nickname="Pin", avatar="https://example.test/avatar.png")
    db_session.add(user)
    db_session.flush()

    artwork = Artwork(
        user_id=user.openid,
        original_path="/tmp/original.png",
        preview_path="/tmp/preview.png",
        pattern_json={"grid": [["01"]], "counts": {"01": 1}},
        style_preset="chibi",
        size_preset="small_60x80",
        title="test pattern",
    )
    order = Order(
        user_id=user.openid,
        order_no="PDTEST0001",
        sku="single_export",
        amount_cny=Decimal("9.90"),
    )
    cdk = CDK(code="ABCDEFGHJKLMNPQRS", type="credit_pack_5", value=5, sales_channel="xhs")
    consent = ConsentLog(user_id=user.openid, consent_type="privacy")
    quota = DailyQuota(user_id=user.openid, date=date(2026, 5, 25))
    db_session.add_all([artwork, order, cdk, consent, quota])
    db_session.commit()

    assert db_session.scalar(select(User).where(User.openid == "wechat_openid_1")) is not None
    assert user.to_frontend_dict()["user_id"] == "wechat_openid_1"
    assert artwork.to_frontend_dict()["preview_url"] == "/tmp/preview.png"
    assert artwork.to_frontend_dict()["pattern_data"]["counts"]["01"] == 1
    assert order.to_frontend_dict()["amount_cny"] == 9.9
    assert cdk.cdk_code == "ABCDEFGHJKLMNPQRS"
    assert quota.script_used == 0
