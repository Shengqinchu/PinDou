"""Shared database-backed fixed-window rate limits."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pindou.db.models import RateLimitBucket, utc_now


class RateLimitExceeded(ValueError):
    def __init__(self, *, retry_after_seconds: int, scope: str) -> None:
        self.retry_after_seconds = max(1, retry_after_seconds)
        self.scope = scope
        super().__init__(f"Rate limit exceeded for {scope}; retry after {self.retry_after_seconds}s.")


@dataclass(frozen=True)
class RateLimitRule:
    scope: str
    identity: str | None
    limit: int
    window_seconds: int


def consume_rate_limits(session: Session, rules: list[RateLimitRule], *, now: datetime | None = None) -> None:
    timestamp = as_utc(now)
    for rule in rules:
        consume_rate_limit(
            session,
            scope=rule.scope,
            identity=rule.identity,
            limit=rule.limit,
            window_seconds=rule.window_seconds,
            now=timestamp,
        )


def consume_rate_limit(
    session: Session,
    *,
    scope: str,
    identity: str | None,
    limit: int,
    window_seconds: int,
    now: datetime | None = None,
) -> None:
    if limit <= 0 or window_seconds <= 0:
        raise ValueError("Rate limit and window must be positive.")

    timestamp = as_utc(now)
    identity_key = normalize_identity(identity)
    window_start = fixed_window_start(timestamp, window_seconds)
    retry_after = retry_after_seconds(timestamp, window_start, window_seconds)

    for attempt in range(2):
        try:
            updated = session.execute(
                update(RateLimitBucket)
                .where(
                    RateLimitBucket.scope == scope,
                    RateLimitBucket.identity == identity_key,
                    RateLimitBucket.window_start == window_start,
                    RateLimitBucket.window_seconds == window_seconds,
                    RateLimitBucket.count < limit,
                )
                .values(count=RateLimitBucket.count + 1, updated_at=timestamp)
            )
            if updated.rowcount == 1:
                session.commit()
                return

            bucket = session.scalar(
                select(RateLimitBucket).where(
                    RateLimitBucket.scope == scope,
                    RateLimitBucket.identity == identity_key,
                    RateLimitBucket.window_start == window_start,
                    RateLimitBucket.window_seconds == window_seconds,
                )
            )
            if bucket is not None:
                session.rollback()
                raise RateLimitExceeded(retry_after_seconds=retry_after, scope=scope)

            bucket = RateLimitBucket(
                scope=scope,
                identity=identity_key,
                window_start=window_start,
                window_seconds=window_seconds,
                count=1,
                created_at=timestamp,
                updated_at=timestamp,
            )
            session.add(bucket)
            session.commit()
            return
        except IntegrityError:
            session.rollback()
            if attempt == 1:
                raise


def normalize_identity(identity: str | None) -> str:
    normalized = (identity or "unknown").strip().lower()
    return normalized or "unknown"


def fixed_window_start(now: datetime, window_seconds: int) -> datetime:
    timestamp = int(now.timestamp())
    bucket_start = timestamp - (timestamp % window_seconds)
    return datetime.fromtimestamp(bucket_start, tz=timezone.utc)


def retry_after_seconds(now: datetime, window_start: datetime, window_seconds: int) -> int:
    window_end = window_start + timedelta(seconds=window_seconds)
    return max(1, int((window_end - now).total_seconds()))


def as_utc(value: datetime | None = None) -> datetime:
    timestamp = value or utc_now()
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)
