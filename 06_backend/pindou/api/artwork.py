"""Artwork API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm.attributes import flag_modified

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.pattern_assets import attach_labeled_pattern_image
from pindou.api.storage import save_pattern_json
from pindou.colormap.loader import estimate_cost_cny
from pindou.pattern.builder import ColorRef, NoBead, PatternSheet, color_ref_from_frontend_dict
from pindou.services.artwork_service import ArtworkService

router = APIRouter(prefix="/artwork", tags=["artwork"])


class SavePatternRequest(BaseModel):
    pattern_json: dict[str, Any] = Field(min_length=1)


@router.get("/list")
def list_artworks(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """分页返回当前用户作品列表。"""
    return ArtworkService(db).list_frontend_artworks(user_id=current_user.user_id, limit=limit, offset=offset)


@router.get("/gallery")
def list_artwork_gallery(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=50),
) -> dict:
    """返回当前用户作品集轻量摘要，供 Web /works 分页使用。"""
    offset = (page - 1) * size
    service = ArtworkService(db)
    total = service.count_artworks(user_id=current_user.user_id)
    items = service.list_gallery_artworks(user_id=current_user.user_id, limit=size, offset=offset)
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "has_more": offset + len(items) < total,
    }


@router.get("/{artwork_id}")
def get_artwork(artwork_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """返回单个作品详情。"""
    artwork = ArtworkService(db).get_artwork(artwork_id)
    if artwork is None or artwork.user_id != current_user.user_id:
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
    return ArtworkService(db).to_frontend_dict(artwork)


@router.put("/{artwork_id}/pattern")
def save_artwork_pattern(
    artwork_id: str,
    payload: SavePatternRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """保存编辑后的图纸 JSON，并重新导出带网格色号的 PNG。"""
    service = ArtworkService(db)
    artwork = service.get_artwork(artwork_id)
    if artwork is None or artwork.user_id != current_user.user_id:
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")

    try:
        pattern_data = normalize_pattern_json(payload.pattern_json, artwork_id=artwork.artwork_id)
        sheet = pattern_sheet_from_normalized_data(pattern_data)
        labeled_url = attach_labeled_pattern_image(pattern_data, sheet, artwork.artwork_id)
        _pattern_path, pattern_url = save_pattern_json(f"pattern_{artwork.artwork_id}", pattern_data)
    except ApiException:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize arbitrary client JSON into API errors.
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "图纸数据格式不正确，保存失败。") from exc

    artwork.pattern_json = pattern_data
    artwork.preview_path = labeled_url
    flag_modified(artwork, "pattern_json")
    db.add(artwork)
    db.commit()
    db.refresh(artwork)

    frontend_artwork = service.to_frontend_dict(artwork)
    return {
        "success": True,
        "pattern_url": pattern_url,
        "pattern": frontend_artwork["pattern_data"],
        "artwork": frontend_artwork,
    }


@router.delete("/{artwork_id}")
def delete_artwork(artwork_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """删除作品并同步删除磁盘上的原图文件。"""
    deleted = ArtworkService(db).delete_artwork(artwork_id=artwork_id, user_id=current_user.user_id)
    if not deleted:
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
    return {"success": True}


def normalize_pattern_json(pattern_data: dict[str, Any], *, artwork_id: str) -> dict[str, Any]:
    """Use grid cells as source of truth and rebuild derived counts/coords."""
    grid_raw = pattern_data.get("grid")
    if not isinstance(grid_raw, list) or not grid_raw:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "图纸缺少可保存的网格数据。")

    row_lengths = [len(row) for row in grid_raw if isinstance(row, list)]
    if len(row_lengths) != len(grid_raw) or not row_lengths or min(row_lengths) == 0:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "图纸网格行列格式不正确。")
    if len(set(row_lengths)) != 1:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "图纸网格必须是规整矩形。")
    if len(grid_raw) > 104 or row_lengths[0] > 104:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "图纸尺寸超过当前支持的拼豆板规格。")

    palette_by_code = color_refs_by_code(pattern_data.get("palette_used", []))
    grid: list[list[dict[str, Any] | None]] = []
    color_counts: dict[str, int] = {}
    coords: list[list[int | str]] = []
    no_bead_mask: list[list[bool]] = []
    first_seen_order: list[str] = []

    for row_index, row in enumerate(grid_raw):
        grid_row: list[dict[str, Any] | None] = []
        mask_row: list[bool] = []
        for col_index, cell in enumerate(row):
            if cell is None:
                grid_row.append(None)
                mask_row.append(True)
                continue
            if not isinstance(cell, dict):
                raise ApiException(422, ErrorCode.VALIDATION_ERROR, "图纸格子颜色格式不正确。")
            color = color_ref_from_frontend_dict(cell)
            if color.code not in palette_by_code:
                palette_by_code[color.code] = color
            if color.code not in color_counts:
                first_seen_order.append(color.code)
            color_counts[color.code] = color_counts.get(color.code, 0) + 1
            coords.append([row_index, col_index, color.code])
            grid_row.append(color.to_frontend_dict())
            mask_row.append(False)
        grid.append(grid_row)
        no_bead_mask.append(mask_row)

    palette_used = [
        palette_by_code[code].to_frontend_dict()
        for code in palette_order(pattern_data.get("palette_used", []), first_seen_order)
        if color_counts.get(code, 0) > 0
    ]
    brand = str(pattern_data.get("brand") or "MARD").upper()
    bead_diameter_mm = float(pattern_data.get("bead_diameter_mm") or 5.0)
    metadata = dict(pattern_data.get("metadata", {}))
    metadata.pop("thumbnail_url", None)
    metadata["artwork_id"] = artwork_id
    metadata["edited_at"] = datetime.now(timezone.utc).isoformat()

    try:
        estimated_cost_cny = estimate_cost_cny(color_counts, brand=brand, bead_diameter_mm=bead_diameter_mm)
    except Exception:
        estimated_cost_cny = float(pattern_data.get("estimated_cost_cny") or 0)

    return {
        **pattern_data,
        "grid": grid,
        "color_counts": color_counts,
        "bead_total": sum(color_counts.values()),
        "coords": coords,
        "no_bead_mask": no_bead_mask,
        "palette_used": palette_used,
        "estimated_cost_cny": estimated_cost_cny,
        "suggested_buffer_pct": int(pattern_data.get("suggested_buffer_pct", 10)),
        "brand": brand,
        "bead_diameter_mm": bead_diameter_mm,
        "metadata": metadata,
    }


def color_refs_by_code(items: Any) -> dict[str, ColorRef]:
    colors: dict[str, ColorRef] = {}
    if not isinstance(items, list):
        return colors
    for item in items:
        if isinstance(item, dict):
            color = color_ref_from_frontend_dict(item)
            colors.setdefault(color.code, color)
    return colors


def palette_order(palette_items: Any, first_seen_order: list[str]) -> list[str]:
    ordered_codes: list[str] = []
    if isinstance(palette_items, list):
        for item in palette_items:
            if isinstance(item, dict):
                code = str(item.get("code") or "")
                if code and code not in ordered_codes:
                    ordered_codes.append(code)
    for code in first_seen_order:
        if code not in ordered_codes:
            ordered_codes.append(code)
    return ordered_codes


def pattern_sheet_from_normalized_data(pattern_data: dict[str, Any]) -> PatternSheet:
    grid: list[list[ColorRef | NoBead]] = []
    for row in pattern_data["grid"]:
        grid.append([
            NoBead() if cell is None else color_ref_from_frontend_dict(cell)
            for cell in row
        ])
    return PatternSheet(
        grid=grid,
        color_counts={str(key): int(value) for key, value in pattern_data["color_counts"].items()},
        bead_total=int(pattern_data["bead_total"]),
        coords=[tuple(coord) for coord in pattern_data["coords"]],
        no_bead_mask=pattern_data["no_bead_mask"],
        palette_used=[color_ref_from_frontend_dict(color) for color in pattern_data["palette_used"]],
        estimated_cost_cny=float(pattern_data.get("estimated_cost_cny", 0)),
        suggested_buffer_pct=int(pattern_data.get("suggested_buffer_pct", 10)),
        brand=str(pattern_data.get("brand", "MARD")),
        bead_diameter_mm=float(pattern_data.get("bead_diameter_mm", 5.0)),
        metadata=dict(pattern_data.get("metadata", {})),
    )
