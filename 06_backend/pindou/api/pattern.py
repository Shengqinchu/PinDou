"""PatternBuilder API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.generate import parse_payload_or_upload, parse_size
from pindou.api.quota import consume_script_quota, consume_white_bg_quota, require_sensitive_consent
from pindou.api.storage import load_preview_image
from pindou.pattern.builder import PatternBuilder
from pindou.services.artwork_service import ArtworkService

router = APIRouter(prefix="/pattern", tags=["pattern"])


@router.post("/build")
async def build_pattern(request: Request, current_user: CurrentUser, db: DbSession) -> dict:
    """独立调用 PatternBuilder；前端“再生成一次”和脚本上传路径复用。"""
    require_sensitive_consent(current_user)
    payload, upload = await parse_payload_or_upload(request, upload_field="raw_image")
    size = parse_size(payload.get("size") or payload.get("size_preset") or "26x26")
    brand = str(payload.get("brand") or "MARD")
    bead_diameter_mm = float(payload.get("bead_diameter_mm") or 5.0)
    mode = str(payload.get("mode") or "auto")

    try:
        if upload is not None:
            raw_image = await upload.read()
            sheet = PatternBuilder().build(
                size=size,
                raw_image=raw_image,
                brand=brand,
                bead_diameter_mm=bead_diameter_mm,
                mode="script",
                auto_remove_white_bg=bool(payload.get("auto_remove_white_bg", False)),
            )
            consume_script_quota(db, current_user)
            if sheet.metadata.get("white_bg_detected"):
                consume_white_bg_quota(db, current_user)
        else:
            preview_id = payload.get("preview_id")
            if preview_id:
                preview, _path = load_preview_image(str(preview_id))
                sheet = PatternBuilder().build(
                    size=size,
                    preview=preview,
                    brand=brand,
                    bead_diameter_mm=bead_diameter_mm,
                    mode="ai",
                )
            else:
                raise ApiException(422, ErrorCode.IMAGE_NOT_FOUND, "缺少 preview_id 或 raw_image。")
    except ApiException:
        raise
    except Exception as exc:  # noqa: BLE001 - pattern builder errors become API errors.
        raise ApiException(500, ErrorCode.PATTERN_BUILD_FAILED, "图纸生成失败，请重新试一次。") from exc

    return sheet.to_frontend_dict()


@router.get("/{artwork_id}")
def get_pattern(artwork_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """返回作品保存的 PatternSheet JSON。"""
    artwork = ArtworkService(db).get_artwork(artwork_id)
    if artwork is None or artwork.user_id != current_user.user_id:
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
    return artwork.pattern_json
