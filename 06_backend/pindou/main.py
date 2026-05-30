"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


def create_app() -> FastAPI:
    settings = get_settings()
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
    install_exception_handlers(app)
    ensure_storage_dirs()
    app.mount("/static/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    app.mount("/static/previews", StaticFiles(directory=settings.preview_dir), name="previews")
    app.mount("/static/patterns", StaticFiles(directory=settings.pattern_dir), name="patterns")
    app.mount("/static/thumbnails", StaticFiles(directory=settings.thumbnail_dir), name="thumbnails")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/console", include_in_schema=False)
    @app.get("/console/", include_in_schema=False)
    async def admin_console() -> FileResponse:
        return FileResponse(STATIC_ADMIN_DIR / "admin.html")

    app.state.reverse_proxy_health_monitor = monitor
    app.state.expired_originals_delete_scheduler = expired_originals_scheduler

    app.include_router(api_router, prefix="/api")
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
