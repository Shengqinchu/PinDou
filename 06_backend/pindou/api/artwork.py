"""Artwork API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.db.models import Artwork
from pindou.services.artwork_service import ArtworkService

router = APIRouter(prefix="/artwork", tags=["artwork"])


@router.get("/list")
def list_artworks(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """分页返回当前用户作品列表。"""
    rows = list(
        db.scalars(
            select(Artwork)
            .where(Artwork.user_id == current_user.user_id)
            .order_by(Artwork.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return [row.to_frontend_dict() for row in rows]


@router.get("/{artwork_id}")
def get_artwork(artwork_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """返回单个作品详情。"""
    artwork = ArtworkService(db).get_artwork(artwork_id)
    if artwork is None or artwork.user_id != current_user.user_id:
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
    return artwork.to_frontend_dict()


@router.delete("/{artwork_id}")
def delete_artwork(artwork_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """删除作品并同步删除磁盘上的原图文件。"""
    deleted = ArtworkService(db).delete_artwork(artwork_id=artwork_id, user_id=current_user.user_id)
    if not deleted:
        raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
    return {"success": True}
