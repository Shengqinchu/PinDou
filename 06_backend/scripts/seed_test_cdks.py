"""Generate test CDKs against a deployed PinDou backend.

Usage examples:
  python scripts/seed_test_cdks.py --base-url https://<cloudrun>/api/v1 --username admin --password <password>
  python scripts/seed_test_cdks.py --base-url https://<cloudrun>/api/v1 --token <admin-jwt>

Generated CDKs are active entitlement tokens. Print them for the tester, but do
not commit them into git or paste them into public docs.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from typing import Any

import requests


DEFAULT_BASE_URL = "https://pindoupuppy.com/api/v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed PinDou test CDKs via the admin API.")
    parser.add_argument("--base-url", default=os.getenv("PINDOU_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--token", default=os.getenv("PINDOU_ADMIN_TOKEN"))
    parser.add_argument("--username", default=os.getenv("PINDOU_ADMIN_USERNAME"))
    parser.add_argument("--password", default=os.getenv("PINDOU_ADMIN_PASSWORD"))
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--cdk-type", default="monthly_card", choices=["single_use", "monthly_card", "credit_pack_5", "credit_pack_10"])
    parser.add_argument("--value", type=int, default=30)
    parser.add_argument("--sales-channel", default="wxcloud_manual_test")
    parser.add_argument("--batch-id", default="wxcloud-manual-test")
    return parser.parse_args()


def request_json(method: str, url: str, *, token: str | None = None, json: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.request(method, url, headers=headers, json=json, timeout=30)
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: HTTP {response.status_code} {payload}")
    if not isinstance(payload, dict):
        raise RuntimeError(f"{method} {url} returned non-object JSON: {payload!r}")
    return payload


def login(base_url: str, username: str | None, password: str | None) -> str:
    username = username or input("Admin username: ").strip()
    password = password or getpass.getpass("Admin password: ")
    payload = request_json("POST", f"{base_url.rstrip('/')}/admin/login", json={"username": username, "password": password})
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Admin login succeeded but no token was returned.")
    return token


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    token = args.token or login(base_url, args.username, args.password)
    payload = request_json(
        "POST",
        f"{base_url}/admin/cdk/batch_generate",
        token=token,
        json={
            "cdk_type": args.cdk_type,
            "value": args.value,
            "count": args.count,
            "sales_channel": args.sales_channel,
            "batch_id": args.batch_id,
        },
    )
    cdks = payload.get("cdks") or []
    if not isinstance(cdks, list):
        raise RuntimeError(f"Unexpected response: {payload}")
    print("Generated CDKs:")
    for item in cdks:
        if isinstance(item, dict):
            print(f"- {item.get('cdk_code')} ({item.get('cdk_type')} value={item.get('value')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
