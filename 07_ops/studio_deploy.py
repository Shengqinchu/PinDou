"""Additive studio deployment. Run on the PinDou origin as root with a reviewed archive."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path("/opt/pindou/studio")
NGINX = Path("/etc/nginx/sites-available/pindou-staging")
UNIT = Path("/etc/systemd/system/pindou-studio.service")
MARKER = "    # PinDou Studio preview (managed by studio_deploy.py)"


def run(*args):
    subprocess.run(args, check=True)


def switch_link(link, target):
    temporary = link.with_name(link.name + ".next")
    if temporary.is_symlink():
        temporary.unlink()
    elif temporary.exists():
        raise RuntimeError(f"Unexpected non-symlink at {temporary}")
    temporary.symlink_to(target)
    temporary.replace(link)


def main():
    archive, version, expected_hash = sys.argv[1:4]
    if not re.fullmatch(r"[0-9]{14}-studio-v[12]", version):
        raise RuntimeError("Invalid release name")
    package = Path(archive)
    if hashlib.sha256(package.read_bytes()).hexdigest() != expected_hash:
        raise RuntimeError("Archive checksum mismatch")
    release = ROOT / "releases" / version
    if release.exists():
        raise RuntimeError("Release exists; refusing overwrite")
    release.mkdir(parents=True)
    with tarfile.open(package) as tar:
        for member in tar.getmembers():
            target = (release / member.name).resolve()
            if not target.is_relative_to(release) or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise RuntimeError("Unsafe archive entry")
        tar.extractall(release)
    manifest = json.loads((release / "manifest.json").read_text())
    for name, expected in manifest["sha256"].items():
        if hashlib.sha256((release / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"File checksum mismatch: {name}")
    shared = ROOT / "shared"
    shared.mkdir(exist_ok=True)
    shutil.chown(shared, user="pindou", group="pindou")
    shared.chmod(0o700)
    venv = ROOT / "venv"
    if not venv.exists():
        run("python3", "-m", "venv", str(venv))
    dependencies = release / "service/requirements.lock.txt"
    if not dependencies.exists():
        dependencies = release / "service/requirements.txt"
    run(str(venv / "bin/pip"), "install", "--disable-pip-version-check", "-r", str(dependencies))
    run(str(venv / "bin/python"), "-c", "import fastapi,uvicorn; from zoneinfo import ZoneInfo; ZoneInfo('America/Toronto')")
    old_nginx = NGINX.read_text()
    old_unit = UNIT.read_text() if UNIT.exists() else None
    current = ROOT / "current"
    if current.exists() and not current.is_symlink():
        raise RuntimeError("Studio current must be a symlink")
    old_current = os.readlink(current) if current.is_symlink() else None
    backup = ROOT / "backups" / version
    backup.mkdir(parents=True)
    backup.chmod(0o700)
    (backup / "nginx.conf").write_text(old_nginx)
    (backup / "state.json").write_text(json.dumps({"previous_current": old_current, "previous_unit": old_unit is not None}, indent=2))
    if old_unit is not None:
        (backup / "pindou-studio.service").write_text(old_unit)
    studio_db = shared / "studio.sqlite3"
    if studio_db.exists():
        with sqlite3.connect(f"file:{studio_db}?mode=ro", uri=True) as source_db:
            with sqlite3.connect(backup / "studio.sqlite3") as target_db:
                source_db.backup(target_db)
        (backup / "studio.sqlite3").chmod(0o600)
    snippet = '''    # PinDou Studio preview (managed by studio_deploy.py)
    location = /studio { return 302 /studio/; }
    location = /studio/version.json {
        root /opt/pindou/studio/current/site;
        try_files $uri =404;
        add_header Cache-Control "no-store" always;
        add_header X-Content-Type-Options nosniff;
    }
    location ^~ /studio/studio-assets/ {
        root /opt/pindou/studio/current/site;
        try_files $uri =404;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
    }
    location ^~ /studio/studio-media/ {
        root /opt/pindou/studio/current/site;
        try_files $uri =404;
        add_header Cache-Control "no-cache";
        add_header X-Content-Type-Options nosniff;
    }
    location /studio/ {
        root /opt/pindou/studio/current/site;
        try_files $uri $uri/ /studio/index.html;
        add_header Cache-Control "no-store";
        add_header X-Robots-Tag "noindex, nofollow" always;
    }
    location /studio-api/ {
        client_max_body_size 16k;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    # End PinDou Studio preview

'''
    if MARKER not in old_nginx:
        if old_nginx.count("    location /api/ {") != 1:
            raise RuntimeError("Expected Nginx insertion point not found exactly once")
        new_nginx = old_nginx.replace("    location /api/ {", snippet + "    location /api/ {", 1)
    else:
        new_nginx = re.sub(r"    # PinDou Studio preview \(managed by studio_deploy.py\).*?    # End PinDou Studio preview\n\n", lambda _: snippet, old_nginx, count=1, flags=re.S)
    unit = '''[Unit]
Description=PinDou Puppy Studio inquiries
After=network-online.target pindou.service
Wants=network-online.target

[Service]
User=pindou
Group=pindou
WorkingDirectory=/opt/pindou/studio/current/service
Environment=STUDIO_DB_PATH=/opt/pindou/studio/shared/studio.sqlite3
Environment=STUDIO_ADMIN_ORIGIN=http://127.0.0.1:8000
EnvironmentFile=-/opt/pindou/studio/shared/.env
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/pindou/studio/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8011 --proxy-headers --forwarded-allow-ips=127.0.0.1 --no-access-log
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/pindou/studio/shared

[Install]
WantedBy=multi-user.target
'''
    try:
        switch_link(current, release)
        UNIT.write_text(unit)
        run("systemctl", "daemon-reload")
        run("systemctl", "enable", "--now", "pindou-studio")
        if old_unit is not None:
            run("systemctl", "restart", "pindou-studio")
        healthy = False
        for _ in range(15):
            try:
                with urlopen("http://127.0.0.1:8011/studio-api/health", timeout=2) as response:
                    healthy = json.load(response)["status"] == "ok"
                if healthy: break
            except Exception:
                time.sleep(1)
        if not healthy:
            raise RuntimeError("Studio health check failed")
        NGINX.write_text(new_nginx)
        run("nginx", "-t")
        run("systemctl", "reload", "nginx")
        print(json.dumps({"deployed": version, "release": str(release), "rollback": str(backup), "files_verified": len(manifest["sha256"])}, indent=2))
    except Exception:
        NGINX.write_text(old_nginx)
        run("nginx", "-t")
        run("systemctl", "reload", "nginx")
        if old_current:
            switch_link(current, old_current)
        if old_unit:
            UNIT.write_text(old_unit)
            run("systemctl", "daemon-reload")
            run("systemctl", "restart", "pindou-studio")
        else:
            run("systemctl", "disable", "--now", "pindou-studio")
        raise


if __name__ == "__main__":
    main()
