"""Delete expired original uploads according to ADR-009."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import Artwork, utc_now
from pindou.db.session import SessionLocal


logger = logging.getLogger(__name__)


def delete_expired_originals_once(
    session: Session,
    *,
    now: datetime | None = None,
    retention_days: int = 30,
) -> int:
    timestamp = now or utc_now()
    cutoff = timestamp - timedelta(days=retention_days)
    artworks = list(
        session.scalars(
            select(Artwork).where(
                Artwork.original_deleted_at.is_(None),
                Artwork.original_path.is_not(None),
                Artwork.created_at < cutoff,
            )
        )
    )

    deleted_count = 0
    for artwork in artworks:
        path = Path(artwork.original_path) if artwork.original_path else None
        if path and path.exists() and path.is_file():
            path.unlink()
        artwork.original_deleted_at = timestamp
        deleted_count += 1

    if deleted_count:
        session.commit()
        logger.info("Deleted %s expired original upload(s).", deleted_count)
    return deleted_count


class ExpiredOriginalsDeleteScheduler:
    """Daily background task for the ADR-009 original upload retention rule."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] = SessionLocal,
        interval_seconds: int = 86400,
        retention_days: int = 30,
    ) -> None:
        self.session_factory = session_factory
        self.interval_seconds = max(1, interval_seconds)
        self.retention_days = retention_days
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self.run(), name="expired-originals-delete-scheduler")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            await asyncio.to_thread(self._run_once)

    def _run_once(self) -> int:
        with self.session_factory() as session:
            return delete_expired_originals_once(session, retention_days=self.retention_days)
