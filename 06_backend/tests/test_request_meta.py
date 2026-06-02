from __future__ import annotations

from starlette.requests import Request

from pindou.api.request_meta import client_ip


def make_request(headers: dict[str, str] | None = None, client_host: str = "10.0.0.8") -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw_headers,
            "client": (client_host, 443),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def test_client_ip_prefers_cloudflare_connecting_ip() -> None:
    request = make_request(
        {
            "CF-Connecting-IP": "203.0.113.24",
            "X-Forwarded-For": "198.51.100.1, 198.51.100.2",
        }
    )

    assert client_ip(request) == "203.0.113.24"


def test_client_ip_uses_first_forwarded_for_when_cloudflare_header_missing() -> None:
    request = make_request({"X-Forwarded-For": "198.51.100.1, 198.51.100.2"})

    assert client_ip(request) == "198.51.100.1"


def test_client_ip_falls_back_to_socket_client() -> None:
    request = make_request(client_host="192.0.2.9")

    assert client_ip(request) == "192.0.2.9"

