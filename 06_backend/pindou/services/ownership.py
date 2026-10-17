"""Owner helpers for user/device owned rows."""

from __future__ import annotations

from typing import Any


def owner_values(row: Any) -> tuple[str, str]:
    """Return canonical owner values with legacy user_id fallback."""
    owner_type = str(getattr(row, "owner_type", "") or "")
    owner_id = str(getattr(row, "owner_id", "") or "")
    user_id = getattr(row, "user_id", None)
    if owner_type and owner_id:
        return owner_type, owner_id
    if user_id:
        return "user", str(user_id)
    return owner_type, owner_id


def belongs_to_owner(row: Any, *, owner_type: str, owner_id: str) -> bool:
    row_owner_type, row_owner_id = owner_values(row)
    return row_owner_type == owner_type and row_owner_id == owner_id
