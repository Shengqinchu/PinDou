"""Request metadata helpers shared by API routes."""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str:
    """Return the best-effort real client IP behind Cloudflare/proxies."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        for candidate in forwarded_for.split(","):
            candidate = candidate.strip()
            if candidate:
                return candidate

    return request.client.host if request.client else "unknown"

