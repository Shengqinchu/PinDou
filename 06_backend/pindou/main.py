"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from pindou import __version__
from pindou.api import api_router
from pindou.api.errors import install_exception_handlers
from pindou.config import get_settings
from pindou.db.session import init_db
from pindou.services.storage_util import ensure_storage_dirs
from pindou.tasks.delete_expired_originals import ExpiredOriginalsDeleteScheduler
from pindou.tasks.reverse_proxy_health_check import ReverseProxyHealthMonitor


STATIC_ADMIN_DIR = Path(__file__).resolve().parent / "static_admin"
STATIC_H5_DIR = Path(__file__).resolve().parent / "static_h5"
ADMIN_CONSOLE_PATH = "/Ios235169"


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_production_ready()
    monitor = ReverseProxyHealthMonitor(
        health_url=settings.reverse_proxy_health_url,
        interval_seconds=settings.reverse_proxy_check_interval_seconds,
        alert_after_seconds=settings.reverse_proxy_alert_after_seconds,
    )
    expired_originals_scheduler = ExpiredOriginalsDeleteScheduler(
        interval_seconds=settings.expired_original_delete_interval_seconds,
        retention_days=settings.expired_original_retention_days,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ensure_storage_dirs()
        init_db()
        app.state.reverse_proxy_health_monitor = monitor
        app.state.expired_originals_delete_scheduler = expired_originals_scheduler
        if settings.enable_reverse_proxy_health_monitor:
            monitor.start()
        if settings.enable_expired_original_delete_task:
            expired_originals_scheduler.start()
        try:
            yield
        finally:
            await monitor.stop()
            await expired_originals_scheduler.stop()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def enforce_request_body_size(request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
            except ValueError:
                length = 0
            if length > settings.max_request_body_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "REQUEST_TOO_LARGE",
                        "message_cn": "请求内容太大了，请上传更小的图片。",
                    },
                )
        return await call_next(request)

    install_exception_handlers(app)
    ensure_storage_dirs()
    app.mount("/static/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    app.mount("/static/previews", StaticFiles(directory=settings.preview_dir), name="previews")
    app.mount("/static/patterns", StaticFiles(directory=settings.pattern_dir), name="patterns")
    app.mount("/static/thumbnails", StaticFiles(directory=settings.thumbnail_dir), name="thumbnails")
    app.mount("/h5", StaticFiles(directory=STATIC_H5_DIR, html=True), name="h5")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def h5_root() -> RedirectResponse:
        return RedirectResponse(url="/h5/", status_code=307)

    @app.get(ADMIN_CONSOLE_PATH, include_in_schema=False)
    @app.get(f"{ADMIN_CONSOLE_PATH}/", include_in_schema=False)
    async def admin_console() -> FileResponse:
        return FileResponse(STATIC_ADMIN_DIR / "admin.html")

    app.state.reverse_proxy_health_monitor = monitor
    app.state.expired_originals_delete_scheduler = expired_originals_scheduler

    app.include_router(api_router, prefix="/api")
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
