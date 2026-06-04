"""Script and AI generation API routes."""

from __future__ import annotations

import base64
import binascii
import logging
from collections.abc import Callable
from dataclasses import replace
from threading import Thread
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.datastructures import UploadFile

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.pattern_assets import finalize_artwork_pattern_assets
from pindou.api.quota import (
    consume_ai_credit,
    consume_script_quota,
    consume_white_bg_quota,
    require_ai_credit_available,
    require_sensitive_consent,
)
from pindou.api.storage import (
    load_uploaded_image,
    normalized_upload_png_bytes,
    save_preview_png,
    save_uploaded_image,
)
from pindou.db.models import GenerationJob, User, utc_now
from pindou.pattern.builder import PatternBuilder
from pindou.providers.base import PreviewProviderError, SizePreset, StylePreset
from pindou.providers.chain import PreviewProviderChain
from pindou.providers.fallback_quantize import FallbackProvider
from pindou.providers.xiaochi_gpt import XiaochiGptProvider
from pindou.services.artwork_service import ArtworkService

router = APIRouter(prefix="/generate", tags=["generate"])
preview_router = APIRouter(prefix="/preview", tags=["generate"])
LOGGER = logging.getLogger(__name__)
SessionFactory = Callable[[], Session]


@router.post("/script")
async def generate_script(request: Request, current_user: CurrentUser, db: DbSession) -> dict:
    """脚本快速生成：原图直接量化为 PatternSheet，并保存 Artwork。"""
    require_sensitive_consent(current_user)
    payload, raw_upload = await parse_payload_or_upload(request, upload_field="raw_image")
    raw_image, original_path = await resolve_raw_image(payload, raw_upload)
    size = parse_size(payload.get("size_preset") or payload.get("size") or "26x26")
    auto_remove_white_bg = parse_bool_default_false(payload.get("auto_remove_white_bg", False))

    try:
        sheet = PatternBuilder().build(
            size=size,
            raw_image=raw_image,
            brand=str(payload.get("brand") or "MARD"),
            bead_diameter_mm=float(payload.get("bead_diameter_mm") or 5.0),
            mode="script",
            auto_remove_white_bg=auto_remove_white_bg,
        )
    except Exception as exc:  # noqa: BLE001 - API normalizes pattern failures.
        raise ApiException(500, ErrorCode.PATTERN_BUILD_FAILED, "图纸生成失败，请换一张照片再试。") from exc

    consume_script_quota(db, current_user)
    if sheet.metadata.get("white_bg_detected"):
        consume_white_bg_quota(db, current_user)

    pattern_data = sheet.to_frontend_dict()
    artwork = ArtworkService(db).save_artwork(
        user_id=current_user.user_id,
        original_path=str(original_path) if original_path else None,
        preview_path="",
        pattern_json=pattern_data,
        style_preset="cartoon_fallback",
        size_preset=size.value,
        title=payload.get("title"),
    )
    pattern_url, _labeled_url = finalize_artwork_pattern_assets(db, artwork=artwork, sheet=sheet, pattern_data=pattern_data)
    return {
        "artwork_id": artwork.artwork_id,
        "pattern_url": pattern_url,
        "pattern": pattern_data,
    }


@router.post("/ai")
async def generate_ai(request: Request, current_user: CurrentUser, db: DbSession) -> dict:
    """AI 精品生成：提交后台任务，避免 Cloudflare 524 长连接超时。"""
    require_sensitive_consent(current_user)
    require_ai_credit_available(current_user)
    payload, upload = await parse_payload_or_upload(request, upload_field="image")
    raw_image, original_path = await resolve_raw_image(payload, upload)
    size = parse_size(payload.get("size_preset") or payload.get("size") or "26x26")
    style = parse_style(payload.get("style_preset") or payload.get("style") or "q_portrait")
    seed = int(payload["seed"]) if payload.get("seed") not in (None, "") else None

    job = GenerationJob(
        user_id=current_user.user_id,
        mode="ai",
        progress=4,
        stage="queued",
        message_cn="已提交，正在排队生成。",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    session_factory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
    start_ai_generation_job(
        job_id=job.job_id,
        session_factory=session_factory,
        user_id=current_user.user_id,
        raw_image=raw_image,
        original_path=str(original_path) if original_path else None,
        payload={
            "brand": str(payload.get("brand") or "MARD"),
            "bead_diameter_mm": float(payload.get("bead_diameter_mm") or 5.0),
            "title": payload.get("title"),
            "size": size.value,
            "style": style.value,
            "seed": seed,
        },
    )

    return job.to_frontend_dict()


@router.get("/status/{job_id}")
def generation_status(job_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    job = db.get(GenerationJob, job_id)
    if job is None or job.user_id != current_user.user_id:
        raise ApiException(404, ErrorCode.IMAGE_NOT_FOUND, "生成任务不存在或已过期，请重新提交。")
    return job.to_frontend_dict()


def start_ai_generation_job(
    *,
    job_id: str,
    session_factory: sessionmaker[Session],
    user_id: str,
    raw_image: bytes,
    original_path: str | None,
    payload: dict[str, Any],
) -> None:
    worker = Thread(
        target=run_ai_generation_job,
        kwargs={
            "job_id": job_id,
            "session_factory": session_factory,
            "user_id": user_id,
            "raw_image": raw_image,
            "original_path": original_path,
            "payload": payload,
        },
        name=f"pindou-ai-generation-{job_id[:8]}",
        daemon=True,
    )
    worker.start()


def run_ai_generation_job(
    *,
    job_id: str,
    session_factory: SessionFactory,
    user_id: str,
    raw_image: bytes,
    original_path: str | None,
    payload: dict[str, Any],
) -> None:
    with session_factory() as db:
        try:
            update_generation_job(
                db,
                job_id,
                status="running",
                progress=12,
                stage="ai_style",
                message_cn="AI 风格化中，正在把照片整理成 Q 版。",
            )
            size = parse_size(payload["size"])
            style = parse_style(payload["style"])
            seed = payload.get("seed")
            preview = build_preview_chain().generate(raw_image, style, size, seed=seed)
            if preview.fallback_count > 0 or preview.provider_used == FallbackProvider.name:
                raise PreviewProviderError("AI provider unavailable; refusing script fallback for AI generation.")

            update_generation_job(
                db,
                job_id,
                progress=58,
                stage="quantize",
                message_cn="生成拼豆图纸中，正在匹配豆色和网格。",
            )
            preview_path, preview_url = save_preview_png(preview.preview_id, preview.image)
            preview = replace(preview, image_url=preview_url)
            sheet = PatternBuilder(target_colors=preview.target_color_count).build(
                size=size,
                preview=preview.image,
                mode="ai",
            )

            update_generation_job(
                db,
                job_id,
                progress=84,
                stage="export",
                message_cn="导出图纸中，正在保存预览和清单。",
            )
            user = db.scalar(select(User).where(User.openid == user_id))
            if user is None:
                raise ApiException(401, ErrorCode.AUTH_REQUIRED, "登录用户不存在，请重新登录。")
            consume_ai_credit(db, user)

            pattern_data = sheet.to_frontend_dict()
            artwork = ArtworkService(db).save_artwork(
                user_id=user_id,
                original_path=original_path,
                preview_path=preview_url,
                pattern_json=pattern_data,
                style_preset=style.value,
                size_preset=size.value,
                title=payload.get("title"),
            )
            pattern_url, _labeled_url = finalize_artwork_pattern_assets(
                db,
                artwork=artwork,
                sheet=sheet,
                pattern_data=pattern_data,
                preview_path=preview_url,
            )
            result = {
                "artwork_id": artwork.artwork_id,
                "preview_url": preview_url,
                "pattern_url": pattern_url,
                "preview": preview.to_frontend_dict(),
                "pattern": pattern_data,
                "preview_path": str(preview_path),
            }
            update_generation_job(
                db,
                job_id,
                status="succeeded",
                progress=100,
                stage="done",
                message_cn="生成完成。",
                result=result,
            )
        except ApiException as exc:
            update_generation_job(
                db,
                job_id,
                status="failed",
                stage="failed",
                message_cn=exc.message_cn,
                error_code=exc.error,
                error_message_cn=exc.message_cn,
            )
        except Exception as exc:  # noqa: BLE001 - background job must normalize provider/network failures.
            LOGGER.exception("ai_generation_job_failed", extra={"job_id": job_id})
            update_generation_job(
                db,
                job_id,
                status="failed",
                stage="failed",
                message_cn="AI 生成暂时失败，请稍后重试或切换普通模式。",
                error_code=ErrorCode.PREVIEW_FAILED,
                error_message_cn="AI 生成暂时失败，请稍后重试或切换普通模式。",
            )


def update_generation_job(
    db: Session,
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    stage: str | None = None,
    message_cn: str | None = None,
    result: dict[str, Any] | None = None,
    error_code: ErrorCode | str | None = None,
    error_message_cn: str | None = None,
) -> None:
    job = db.get(GenerationJob, job_id)
    if job is None:
        return
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = max(0, min(100, int(progress)))
    if stage is not None:
        job.stage = stage
    if message_cn is not None:
        job.message_cn = message_cn
    if result is not None:
        job.result_json = result
    if error_code is not None:
        job.error_code = str(error_code)
    if error_message_cn is not None:
        job.error_message_cn = error_message_cn
    job.updated_at = utc_now()
    if status in {"succeeded", "failed"}:
        job.completed_at = utc_now()
    db.add(job)
    db.commit()


@preview_router.post("/generate")
async def generate_preview(request: Request, current_user: CurrentUser, db: DbSession) -> dict:
    """前端 PreviewResult 兼容端点：只生成并保存 AI preview，不立即建作品。"""
    require_sensitive_consent(current_user)
    require_ai_credit_available(current_user)
    payload, upload = await parse_payload_or_upload(request, upload_field="image")
    if upload is not None:
        raw_image = normalized_upload_png_bytes(upload.filename or "upload.png", await upload.read())
    else:
        raw_image, _path = await resolve_raw_image(payload, None)
    size = parse_size(payload.get("size_preset") or payload.get("size") or "26x26")
    style = parse_style(payload.get("style_preset") or payload.get("style") or "q_portrait")
    seed = int(payload["seed"]) if payload.get("seed") not in (None, "") else None

    try:
        preview = build_preview_chain().generate(raw_image, style, size, seed=seed)
        _preview_path, preview_url = save_preview_png(preview.preview_id, preview.image)
        preview = replace(preview, image_url=preview_url)
    except Exception as exc:  # noqa: BLE001 - provider failures are normalized for the client.
        raise ApiException(500, ErrorCode.PREVIEW_FAILED, "AI 生成暂时失败，请稍后再试。") from exc

    consume_ai_credit(db, current_user)
    return preview.to_frontend_dict()


async def parse_payload_or_upload(request: Request, *, upload_field: str) -> tuple[dict[str, Any], UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        payload = {key: value for key, value in form.items() if not isinstance(value, UploadFile)}
        upload = form.get(upload_field) or form.get("image") or form.get("raw_image") or form.get("file")
        return payload, upload if isinstance(upload, UploadFile) else None
    return await request.json(), None


async def resolve_raw_image(payload: dict[str, Any], upload: UploadFile | None) -> tuple[bytes, str | None]:
    if upload is not None:
        data = await upload.read()
        saved = save_uploaded_image(upload.filename or "upload.png", data)
        return load_uploaded_image(saved["image_id"])[0], saved["path"]
    image_base64 = payload.get("image_base64") or payload.get("raw_image_base64")
    if image_base64:
        filename = str(payload.get("filename") or payload.get("image_filename") or "upload.png")
        data = decode_base64_image(str(image_base64))
        saved = save_uploaded_image(filename, data)
        return load_uploaded_image(saved["image_id"])[0], saved["path"]
    image_id = str(payload.get("image_id") or "")
    if not image_id:
        raise ApiException(422, ErrorCode.IMAGE_NOT_FOUND, "缺少图片，请先上传照片。")
    data, path = load_uploaded_image(image_id)
    return data, str(path)


def decode_base64_image(value: str) -> bytes:
    """Decode a mini-program callContainer JSON image payload."""
    encoded = value.split(",", 1)[1] if "," in value and value.lstrip().startswith("data:") else value
    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "图片数据格式不正确。") from exc


def parse_bool_default_false(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def parse_size(value: Any) -> SizePreset:
    try:
        return SizePreset(str(value))
    except ValueError as exc:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "尺寸参数不正确。") from exc


def parse_style(value: Any) -> StylePreset:
    try:
        return StylePreset(str(value))
    except ValueError as exc:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "风格参数不正确。") from exc


def build_preview_chain() -> PreviewProviderChain:
    fallback = FallbackProvider()
    try:
        primary = XiaochiGptProvider()
    except Exception:  # noqa: BLE001 - local dev/test may not have image API key.
        primary = fallback
    return PreviewProviderChain(providers=[primary], fallback_provider=fallback)
