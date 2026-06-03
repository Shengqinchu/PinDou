"""Password hashing helpers for web email accounts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os


ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 210_000
SALT_BYTES = 16
HASH_BYTES = 32


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    digest = _derive(password=password, salt=salt, iterations=ITERATIONS)
    return "$".join(
        (
            ALGORITHM,
            str(ITERATIONS),
            _b64encode(salt),
            _b64encode(digest),
        )
    )


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = stored_hash.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        iterations = int(iterations_raw)
        salt = _b64decode(salt_raw)
        expected = _b64decode(digest_raw)
    except (ValueError, TypeError):
        return False
    actual = _derive(password=password, salt=salt, iterations=iterations)
    return hmac.compare_digest(actual, expected)


def _derive(*, password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=HASH_BYTES,
    )


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
