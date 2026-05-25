"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pindou import __version__
from pindou.api import api_router
from pindou.config import get_settings
from pindou.tasks.delete_expired_originals import ExpiredOriginalsDeleteScheduler
from pindou.tasks.reverse_proxy_health_check import ReverseProxyHealthMonitor


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

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.state.reverse_proxy_health_monitor = monitor
    app.state.expired_originals_delete_scheduler = expired_originals_scheduler

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
