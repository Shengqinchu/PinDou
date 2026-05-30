"""Backend-only admin audit logging helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from pindou.db.models import AdminAuditLog
from pindou.db.session import SessionLocal


def write_audit(
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    before: Any | None,
    after: Any | None,
    reason: str,
    request_id: str | None,
    *,
    session: Session | None = None,
) -> int:
    """Persist a backend-generated audit event and return its id."""
    if session is None:
        with SessionLocal() as owned_session:
            return _write_audit_with_session(
                owned_session,
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                before=before,
                after=after,
                reason=reason,
                request_id=request_id,
            )
    return _write_audit_with_session(
        session,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=before,
        after=after,
        reason=reason,
        request_id=request_id,
    )


def _write_audit_with_session(
    session: Session,
    *,
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    before: Any | None,
    after: Any | None,
    reason: str,
    request_id: str | None,
) -> int:
    audit = AdminAuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_json=_json_safe(before),
        after_json=_json_safe(after),
        reason=reason,
        request_id=request_id,
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    return audit.id


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    return str(value)
