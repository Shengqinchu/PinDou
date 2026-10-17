"""PatternBuilder API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pindou.api.deps import CurrentActor, CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.generate import parse_bool_default_false, parse_payload_or_upload, parse_size, resolve_raw_image
from pindou.api.pattern_assets import finalize_artwork_pattern_assets
from pindou.api.quota import consume_script_quota, consume_white_bg_quota, require_sensitive_consent
from pindou.api.storage import load_preview_image, load_uploaded_image, save_pattern_png, save_uploaded_image
from pindou.pattern.builder import PatternBuilder, pattern_sheet_from_frontend_dict
from pindou.pattern.exporter import PatternExporter, partition_filename
from pindou.services.artwork_service import ArtworkService
from pindou.services.ownership import belongs_to_owner
from pindou.services.storage_util import storage_url

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
        if upload is not None or payload.get("raw_image_base64") or payload.get("image_base64"):
            if upload is not None:
                saved = save_uploaded_image(upload.filename or "upload.png", await upload.read())
                raw_image, _raw_path = load_uploaded_image(saved["image_id"])
                original_path = saved["path"]
            else:
                raw_image, original_path = await resolve_raw_image(payload, None)
            sheet = PatternBuilder().build(
                size=size,
                raw_image=raw_image,
                brand=brand,
                bead_diameter_mm=bead_diameter_mm,
                mode="script",
                auto_remove_white_bg=parse_bool_default_false(payload.get("auto_remove_white_bg", False)),
            )
            consume_script_quota(db, current_user)
            if sheet.metadata.get("white_bg_detected"):
                consume_white_bg_quota(db, current_user)
            preview_path = ""
            style_preset = "cartoon_fallback"
        else:
            preview_id = payload.get("preview_id")
            if preview_id:
                preview, preview_path_obj = load_preview_image(str(preview_id))
                sheet = PatternBuilder().build(
                    size=size,
                    preview=preview,
                    brand=brand,
                    bead_diameter_mm=bead_diameter_mm,
                    mode="ai",
                )
                original_path = None
                preview_path = storage_url(f"previews/{preview_path_obj.name}")
                style_preset = "q_portrait"
            else:
                raise ApiException(422, ErrorCode.IMAGE_NOT_FOUND, "缺少 preview_id 或 raw_image。")
    except ApiException:
        raise
    except Exception as exc:  # noqa: BLE001 - pattern builder errors become API errors.
        raise ApiException(500, ErrorCode.PATTERN_BUILD_FAILED, "图纸生成失败，请重新试一次。") from exc

    pattern_data = sheet.to_frontend_dict()
    artwork = ArtworkService(db).save_artwork(
        user_id=current_user.user_id,
        original_path=original_path,
        preview_path=preview_path,
        pattern_json=pattern_data,
        style_preset=style_preset,
        size_preset=size.value,
        title=payload.get("title"),
    )
    finalize_artwork_pattern_assets(db, artwork=artwork, sheet=sheet, pattern_data=pattern_data, preview_path=preview_path)
    return pattern_data


@router.get("/{artwork_id}/partitions")
def get_pattern_partitions(
    artwork_id: str,
    actor: CurrentActor,
    db: DbSession,
    partition_size: int | None = None,
) -> dict:
    """返回高级分区图 URL 列表；固定为 2x2 四象限。"""
    _ = partition_size
    artwork = ArtworkService(db).get_artwork(artwork_id)
    if artwork is None or not belongs_to_owner(artwork, owner_type=actor.owner_type, owner_id=actor.owner_id):
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
    sheet = pattern_sheet_from_frontend_dict(artwork.pattern_json)
    partitions = PatternExporter().export_partitions(sheet)
    items: list[dict] = []
    for partition in partitions:
        _path, url = save_pattern_png(partition_filename(artwork_id, partition.index), partition.image)
        items.append(
            {
                "index": partition.index,
                "key": partition.key,
                "label": partition.label,
                "row_start": partition.row_start,
                "row_end": partition.row_end,
                "col_start": partition.col_start,
                "col_end": partition.col_end,
                "grid_offset": {"row": partition.row_start, "col": partition.col_start},
                "rows": partition.rows,
                "cols": partition.cols,
                "url": url,
            }
        )
    max_partition_dim = max((max(partition.rows, partition.cols) for partition in partitions), default=0)
    return {
        "artwork_id": artwork_id,
        "partition_size": max_partition_dim,
        "partition_layout": "2x2",
        "rows": len(sheet.grid),
        "cols": max((len(row) for row in sheet.grid), default=0),
        "total": len(items),
        "items": items,
    }


@router.get("/{artwork_id}")
def get_pattern(artwork_id: str, actor: CurrentActor, db: DbSession) -> dict:
    """返回作品保存的 PatternSheet JSON。"""
    artwork = ArtworkService(db).get_artwork(artwork_id)
    if artwork is None or not belongs_to_owner(artwork, owner_type=actor.owner_type, owner_id=actor.owner_id):
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
    return artwork.pattern_json
