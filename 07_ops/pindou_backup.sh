#!/bin/bash
# PinDou daily server backup. Installed as /usr/local/sbin/pindou-backup and run by
# pindou-backup.timer (03:30 Toronto). See 07_ops/SERVER_HARDENING_BACKUP_20261107.md.
#
# Each run writes /var/backups/pindou/daily/<stamp>/ with:
#   db/       online SQLite copies (backup API) of studio.sqlite3 and pindou.db, integrity-checked
#   files/    both shared directories (minus the live databases) plus service configuration;
#             unchanged files are hardlinks to the previous snapshot, so a day costs only its changes
#   manifest.json
# Keeps 14 daily snapshots and the first snapshot of each month for 6 months.
set -euo pipefail
umask 077

ROOT=/var/backups/pindou
DAILY=$ROOT/daily
MONTHLY=$ROOT/monthly
KEEP_DAILY=14
KEEP_MONTHLY=6
STAMP=$(date +%Y%m%d-%H%M%S)
DEST=$DAILY/$STAMP
PARTIAL=$DEST.partial
WORK=$(mktemp -d /var/tmp/pindou-backup.XXXXXX)
trap 'rm -rf "$WORK" "$PARTIAL"' EXIT

install -d -m 700 -o root -g root "$ROOT" "$DAILY" "$MONTHLY"
find "$DAILY" -mindepth 1 -maxdepth 1 -name '*.partial' -exec rm -rf {} +
PREV=$(find "$DAILY" -mindepth 1 -maxdepth 1 -type d -name '2*' | sort | tail -n 1)

# 1. Online database copies, taken as the service user so SQLite never leaves
#    root-owned -wal/-shm files next to the live databases.
chown pindou:pindou "$WORK"
runuser -u pindou -- python3 - "$WORK" <<'PY'
import json
import os
import sqlite3
import sys

work = sys.argv[1]
sources = {
    "studio.sqlite3": "/opt/pindou/studio/shared/studio.sqlite3",
    "pindou.db": "/opt/pindou/shared/var/pindou.db",
}
report = {}
for name, source_path in sources.items():
    target = os.path.join(work, name)
    source = sqlite3.connect(source_path, timeout=60)
    copy = sqlite3.connect(target)
    source.backup(copy)
    copy.close()
    source.close()
    check = sqlite3.connect(target)
    result = check.execute("PRAGMA integrity_check").fetchone()[0]
    tables = check.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    check.close()
    if result != "ok":
        sys.exit(f"{name}: integrity_check returned {result!r}")
    report[name] = {"integrity": result, "tables": tables, "bytes": os.path.getsize(target)}
with open(os.path.join(work, "sqlite.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=1)
PY

# 2. Files and configuration. Missing optional paths are skipped, not fatal.
SOURCES=()
for path in \
  /opt/pindou/studio/shared /opt/pindou/shared \
  /etc/cloudflared /etc/nginx /etc/ssh/sshd_config /etc/ssh/sshd_config.d \
  /etc/fail2ban/jail.d /etc/fail2ban/fail2ban.d /etc/apt/apt.conf.d/20auto-upgrades \
  /etc/systemd/system/pindou.service /etc/systemd/system/pindou-studio.service \
  /etc/systemd/system/pindou-backup.service /etc/systemd/system/pindou-backup.timer \
  /etc/systemd/system/pindou-backup-alert.service \
  /etc/systemd/system/cloudflared.service /etc/systemd/system/cloudflared.service.d \
  /etc/systemd/system/cnproxy-guard.service /usr/local/sbin \
  /var/lib/cnproxy/.ssh /root/.ssh/authorized_keys /home/pindou/.ssh/authorized_keys \
  /var/spool/cron/crontabs; do
  [ -e "$path" ] && SOURCES+=("$path")
done
LINK_DEST=()
[ -n "$PREV" ] && [ -d "$PREV/files" ] && LINK_DEST=(--link-dest="$PREV/files")
mkdir -p "$PARTIAL/files" "$PARTIAL/db"
rsync -aR --numeric-ids "${LINK_DEST[@]}" \
  --exclude='/opt/pindou/studio/shared/studio.sqlite3*' \
  --exclude='/opt/pindou/shared/var/pindou.db*' \
  "${SOURCES[@]}" "$PARTIAL/files/"

# 3. Databases, manifest, then publish the snapshot in one rename.
mv "$WORK/studio.sqlite3" "$WORK/pindou.db" "$PARTIAL/db/"
python3 - "$PARTIAL" "$WORK/sqlite.json" <<'PY'
import hashlib
import json
import os
import socket
import sys
import time

dest, report_path = sys.argv[1], sys.argv[2]
with open(report_path, encoding="utf-8") as handle:
    databases = json.load(handle)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


for name, entry in databases.items():
    entry["sha256"] = sha256(os.path.join(dest, "db", name))
file_count = sum(len(names) for _, _, names in os.walk(os.path.join(dest, "files")))
manifest = {
    "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "host": socket.gethostname(),
    "studio_release": os.path.realpath("/opt/pindou/studio/current"),
    "generator_release": os.path.realpath("/opt/pindou/current"),
    "databases": databases,
    "file_count": file_count,
}
with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as handle:
    json.dump(manifest, handle, indent=1)
PY
mv "$PARTIAL" "$DEST"
ln -sfn "$DEST" "$ROOT/latest"

# 4. Monthly copy (hardlinks, nearly free) and retention.
MONTH=$(date +%Y-%m)
[ -d "$MONTHLY/$MONTH" ] || cp -al "$DEST" "$MONTHLY/$MONTH"
find "$DAILY" -mindepth 1 -maxdepth 1 -type d -name '2*' | sort | head -n -"$KEEP_DAILY" | xargs -r rm -rf
find "$MONTHLY" -mindepth 1 -maxdepth 1 -type d | sort | head -n -"$KEEP_MONTHLY" | xargs -r rm -rf

echo "backup $STAMP ok: $(du -sh "$DEST" | cut -f1) snapshot, $(du -sh "$ROOT" | cut -f1) total kept"
