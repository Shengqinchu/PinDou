#!/usr/bin/env python3
"""Tell the owner through Server酱 that the nightly backup failed.

Installed as /usr/local/sbin/pindou-backup-alert and started by pindou-backup.service
(OnFailure=). It reuses the Studio owner-alert key and sends no backup content.
"""
import json
import re
import socket
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SECRET = "/opt/pindou/studio/shared/serverchan-secret.json"


def main() -> int:
    try:
        with open(SECRET, encoding="utf-8") as handle:
            sendkey = str(json.load(handle).get("sendkey", ""))
    except (OSError, ValueError) as exc:
        print(f"no Server酱 key: {type(exc).__name__}", file=sys.stderr)
        return 1
    if not re.fullmatch(r"SCT[A-Za-z0-9]{12,196}", sendkey):  # same rule as 06_studio/owner_notifications.py
        print("Server酱 key has an unexpected format", file=sys.stderr)
        return 1
    title = "PinDou 服务器备份失败"
    body = (
        f"{time.strftime('%Y-%m-%d %H:%M %Z')} {socket.gethostname()} 的每日备份没有完成。\n\n"
        "网站和预约不受影响。请让 Claude 查看：journalctl -u pindou-backup"
    )
    request = Request(
        f"https://sctapi.ftqq.com/{sendkey}.send",
        data=urlencode({"title": title, "desp": body}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "PinDouBackup/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read(65536))
    except (OSError, ValueError) as exc:
        print(f"Server酱 unreachable: {type(exc).__name__}", file=sys.stderr)
        return 1
    ok = isinstance(result, dict) and result.get("code") == 0
    print("alert accepted" if ok else f"alert rejected, code {result.get('code') if isinstance(result, dict) else '?'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
