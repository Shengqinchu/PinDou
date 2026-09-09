"""Offline preparation for Firebase -> Descope -> email routing.

Not registered with FastAPI and not shipped in the production allowlist yet.
This ledger cannot enforce provider-wide billing limits. Before enabling it,
all Firebase sends must be covered by a provider-side block and Descope's public
SDK sending endpoints must be restricted. It never sends or validates an OTP.
"""
from __future__ import annotations

import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Conservative rolling windows until each new project's billing reset boundary
# has been verified. A reservation counts even if delivery is unknown or fails.
CAPS = {"firebase": (10, 25 * 3600), "descope": (100, 32 * 86400)}
OTP_TTL = 600
OPAQUE_KEY = re.compile(r"^[a-zA-Z0-9_-]{20,128}$")


@dataclass(frozen=True)
class DeliveryPlan:
    request_key: str
    provider: str
    dispatch: bool
    expires_at: int


class SmsLedger:
    """Atomic local send budget, with provider affinity and idempotent planning.

    Keys are server-generated opaque IDs and keyed hashes, never phone numbers.
    The caller must additionally enforce per-number/IP limits and bot checks.
    A duplicate request never grants another send, including after a crash.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS studio_sms_attempts (
                    request_key TEXT PRIMARY KEY,
                    subject_key TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    outcome TEXT NOT NULL DEFAULT 'unknown'
                );
                CREATE INDEX IF NOT EXISTS studio_sms_budget
                    ON studio_sms_attempts(provider, created_at);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def validate_keys(request_key: str, subject_key: str):
        if not OPAQUE_KEY.fullmatch(request_key) or not OPAQUE_KEY.fullmatch(subject_key):
            raise ValueError("opaque_server_keys_required")

    def reserve(self, request_key: str, subject_key: str, *,
                eligible: Iterable[str] = (), now: int | None = None) -> DeliveryPlan:
        """Default disabled. Only server-confirmed ready providers are eligible.

        The caller may send exactly once when dispatch=True. Do not retry an
        ambiguous network result or switch provider for the same request key.
        A deliberate user resend uses a new key and consumes another allowance.
        """
        self.validate_keys(request_key, subject_key)
        now = int(time.time()) if now is None else int(now)
        eligible = set(eligible)
        if eligible - CAPS.keys():
            raise ValueError("unknown_provider")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM studio_sms_attempts WHERE request_key=?", (request_key,)).fetchone()
            if existing:
                if existing["subject_key"] != subject_key:
                    raise ValueError("request_subject_mismatch")
                return DeliveryPlan(request_key, existing["provider"], False, existing["expires_at"])
            provider = "email"
            for name, (limit, window) in CAPS.items():
                if name not in eligible:
                    continue
                count = db.execute(
                    "SELECT count(*) FROM studio_sms_attempts WHERE provider=? AND created_at>=?",
                    (name, now - window),
                ).fetchone()[0]
                if count < limit:
                    provider = name
                    break
            expires = now + OTP_TTL
            db.execute("INSERT INTO studio_sms_attempts(request_key,subject_key,provider,created_at,expires_at) VALUES(?,?,?,?,?)",
                       (request_key, subject_key, provider, now, expires))
            return DeliveryPlan(request_key, provider, provider != "email", expires)

    def record_outcome(self, request_key: str, subject_key: str, outcome: str):
        """Transport observation only. No status refunds a reserved send.

        Even a known delivery failure is counted: billing is per send, not per
        successful login. Unknown responses retain the original provider.
        """
        self.validate_keys(request_key, subject_key)
        if outcome not in {"sent", "failed", "unknown"}:
            raise ValueError("invalid_transport_outcome")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("UPDATE studio_sms_attempts SET outcome=? WHERE request_key=? AND subject_key=? AND provider!='email'",
                                 (outcome, request_key, subject_key)).rowcount
            if not changed:
                raise ValueError("sms_attempt_not_found")

    def verification_provider(self, request_key: str, subject_key: str, *, now: int | None = None) -> str:
        """Resolve affinity only; the provider must still verify code/token.

        Never accept a provider name or phone claim chosen by the browser.
        Verification must eventually validate issuer, audience, expiry and a
        verified phone claim before mapping to the generator's shared identity.
        """
        self.validate_keys(request_key, subject_key)
        now = int(time.time()) if now is None else int(now)
        with self.connect() as db:
            row = db.execute("SELECT * FROM studio_sms_attempts WHERE request_key=? AND subject_key=?", (request_key, subject_key)).fetchone()
        if not row or row["provider"] == "email" or row["expires_at"] <= now or row["outcome"] == "failed":
            raise ValueError("sms_attempt_unavailable")
        return row["provider"]
