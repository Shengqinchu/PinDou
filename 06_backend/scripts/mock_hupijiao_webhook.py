"""Trigger a local Hupijiao paid webhook for development testing.

Usage:
    python scripts/mock_hupijiao_webhook.py <order_no> --amount 28.00
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from pindou.services.hupijiao_service import sign_params  # noqa: E402


DEV_MOCK_WEBHOOK_SECRET = "pindou-dev-hupijiao-mock-secret"
DEFAULT_CALLBACK_URL = "http://127.0.0.1:8000/api/v1/webhook/hupijiao"


def main() -> int:
    parser = argparse.ArgumentParser(description="Mock a paid Hupijiao webhook against local PinDou API.")
    parser.add_argument("order_no", help="PinDou order_no, for example PD20260526123456ABCD1234")
    parser.add_argument("--amount", default="28.00", help="Order amount in CNY. Must match the DB order amount.")
    parser.add_argument("--url", default=None, help="Webhook URL. Defaults to local API.")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(BACKEND_ROOT / ".env")

    secret = (
        os.getenv("HUPIJIAO_WEBHOOK_SECRET")
        or os.getenv("HUPIJIAO_APP_SECRET")
        or DEV_MOCK_WEBHOOK_SECRET
    )
    url = args.url or DEFAULT_CALLBACK_URL
    now = str(int(time.time()))
    payload = {
        "trade_order_id": args.order_no,
        "total_fee": f"{float(args.amount):.2f}",
        "transaction_id": f"MOCK{secrets.token_hex(8).upper()}",
        "open_order_id": f"OPEN{secrets.token_hex(6).upper()}",
        "order_title": "PinDou mock paid order",
        "status": "OD",
        "appid": os.getenv("HUPIJIAO_APP_ID") or "mock_app",
        "time": now,
        "nonce_str": secrets.token_hex(8),
    }
    payload["hash"] = sign_params(payload, secret)

    response = requests.post(url, data=payload, timeout=15)
    print(f"POST {url}")
    print(f"status={response.status_code} body={response.text}")
    return 0 if response.status_code == 200 and response.text.strip() == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
