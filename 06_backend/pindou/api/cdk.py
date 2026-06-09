"""CDK redemption API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from pindou.api.deps import CurrentActor, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.request_meta import client_ip
from pindou.services.cdk_service import CDKAlreadyRedeemedError, CDKInvalidError, CDKRateLimitError, CDKService

router = APIRouter(prefix="/cdk", tags=["cdk"])


class RedeemCDKRequest(BaseModel):
    cdk_code: str = Field(min_length=1)


@router.post("/redeem")
def redeem_cdk(payload: RedeemCDKRequest, request: Request, actor: CurrentActor, db: DbSession) -> dict:
    """兑换 CDK；登录用户归账号，游客归签名 device 钱包。"""
    service = CDKService(db)
    try:
        cdk = service.redeem(
            code=payload.cdk_code,
            owner_type=actor.owner_type,
            owner_id=actor.owner_id,
            user_id=actor.user.user_id if actor.user else None,
            ip=client_ip(request),
        )
    except CDKRateLimitError as exc:
        raise ApiException(429, ErrorCode.CDK_RATE_LIMITED, "您操作太快了，稍后再试。") from exc
    except CDKAlreadyRedeemedError as exc:
        raise ApiException(409, ErrorCode.CDK_REDEEMED, "该兑换码已经被兑换过了。") from exc
    except CDKInvalidError as exc:
        raise ApiException(404, ErrorCode.INVALID_CDK, "兑换码不正确，请检查输入是否正确。") from exc
    return {
        "success": True,
        "cdk_type": cdk.type,
        "value": cdk.value,
        "expires_at": cdk.expires_at.isoformat() if cdk.expires_at else None,
        "owner_type": actor.owner_type,
        "owner_id": actor.owner_id,
        "is_anonymous": actor.is_anonymous,
        "device_token": actor.device.token if actor.device else None,
    }
