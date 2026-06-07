"""Upload API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.datastructures import UploadFile

from pindou.api.deps import CurrentUser
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.quota import require_sensitive_consent
from pindou.api.storage import save_uploaded_image

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
@router.post("/")
async def upload_image(request: Request, current_user: CurrentUser) -> dict:
    """接收单张 jpg/png/webp 图片，EXIF 自动旋正后保存到 PINDOU_UPLOAD_DIR。"""
    require_sensitive_consent(current_user)
    form = await request.form()
    upload = form.get("image") or form.get("file")
    if not isinstance(upload, UploadFile):
        raise ApiException(422, ErrorCode.INVALID_UPLOAD, "请上传一张照片。")
    result = save_uploaded_image(upload.filename or "upload.png", await upload.read(), content_type=upload.content_type)
    return {"image_id": result["image_id"], "image_url": result["image_url"]}
