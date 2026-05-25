"""Reverse proxy health monitor for ADR-007."""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.request
from collections.abc import Callable


logger = logging.getLogger(__name__)


class ReverseProxyHealthMonitor:
    """Background checker that logs an ADR-007 alert after prolonged failures."""

    def __init__(
        self,
        *,
        health_url: str,
        interval_seconds: int,
        alert_after_seconds: int,
        timeout_seconds: float = 10.0,
        probe: Callable[[str, float], bool] | None = None,
    ) -> None:
        self.health_url = health_url
        self.interval_seconds = max(1, interval_seconds)
        self.alert_after_seconds = max(0, alert_after_seconds)
        self.timeout_seconds = timeout_seconds
        self.probe = probe or self._default_probe
        self.consecutive_failures = 0
        self.first_failure_started_at: float | None = None
        self.alert_logged = False
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self.run(), name="reverse-proxy-health-monitor")

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
            await self.check_once()

    async def check_once(self) -> bool:
        try:
            ok = await asyncio.to_thread(self.probe, self.health_url, self.timeout_seconds)
        except Exception as exc:  # noqa: BLE001 - health probes should not crash the app.
            self._record_failure(str(exc))
            return False

        if ok:
            self._record_success()
            return True
        self._record_failure("probe returned unhealthy status")
        return False

    def _record_success(self) -> None:
        if self.consecutive_failures:
            logger.info("Reverse proxy health check recovered after %s failure(s).", self.consecutive_failures)
        self.consecutive_failures = 0
        self.first_failure_started_at = None
        self.alert_logged = False

    def _record_failure(self, reason: str) -> None:
        now = time.monotonic()
        self.consecutive_failures += 1
        if self.first_failure_started_at is None:
            self.first_failure_started_at = now
        failure_duration = now - self.first_failure_started_at
        logger.warning(
            "Reverse proxy health check failed (%s consecutive, %.0fs elapsed): %s",
            self.consecutive_failures,
            failure_duration,
            reason,
        )
        if self._should_alert(failure_duration):
            logger.error(
                "ADR-007 alert: reverse proxy has failed %s consecutive checks for %.0fs "
                "(threshold %ss). User must re-evaluate provider/compliance fallback.",
                self.consecutive_failures,
                failure_duration,
                self.alert_after_seconds,
            )
            self.alert_logged = True

    def _should_alert(self, failure_duration: float) -> bool:
        return (
            self.consecutive_failures >= 3
            and failure_duration >= self.alert_after_seconds
            and not self.alert_logged
        )

    @staticmethod
    def _default_probe(url: str, timeout_seconds: float) -> bool:
        request = urllib.request.Request(url, headers={"User-Agent": "PinDou/0.1"})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return 200 <= response.status < 500
