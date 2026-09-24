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


def retain_static_assets(releases: Path, history: Path):
    """Keep manifest-verified public assets usable by already-open browser tabs."""
    history.mkdir(parents=True, exist_ok=True)
    history.chmod(0o755)
    seen = {}
    added = 0
    for release in sorted(releases.iterdir()):
        manifest_path = release / "manifest.json"
        if not re.fullmatch(r"[0-9]{14}-studio-v[1234567]", release.name) or not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text())
        for name, digest in manifest["sha256"].items():
            parts = Path(name).parts
            if len(parts) < 4 or parts[:2] != ("site", "studio") or parts[2] not in ("studio-assets", "studio-fonts"):
                continue
            source = release / name
            relative = Path(*parts[2:])
            target = history / relative
            if (not source.resolve().is_relative_to((release / "site/studio" / parts[2]).resolve())
                    or not target.resolve().is_relative_to((history / parts[2]).resolve())
                    or source.is_symlink() or target.is_symlink()):
                raise RuntimeError("Unsafe static asset path")
            if relative in seen:
                if seen[relative] != digest:
                    raise RuntimeError(f"Static asset name collision: {relative}")
                continue
            if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"Previous static asset changed: {relative}")
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    raise RuntimeError(f"Retained static asset changed: {relative}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".next")
                shutil.copyfile(source, temporary)
                temporary.chmod(0o644)
                temporary.replace(target)
                added += 1
            seen[relative] = digest
    return {"retained": len(seen), "added": added}


def main():
    archive, version, expected_hash = sys.argv[1:4]
    if not re.fullmatch(r"[0-9]{14}-studio-v[1234567]", version):
        raise RuntimeError("Invalid release name")
    package = Path(archive)
    if hashlib.sha256(package.read_bytes()).hexdigest() != expected_hash:
        raise RuntimeError("Archive checksum mismatch")
    release = ROOT / "releases" / version
    if release.exists():
        raise RuntimeError("Release exists; refusing overwrite")
    release.mkdir(parents=True)
    with tarfile.open(package) as tar:
        manifest=json.load(tar.extractfile('manifest.json'))
        if manifest.get('reuse'):
            base_version=manifest.get('base_version','')
            if not re.fullmatch(r'[0-9]{14}-studio-v[1234567]',base_version):raise RuntimeError('Invalid base release')
            base=ROOT/'releases'/base_version
            for name in manifest['reuse']:
                source=(base/name).resolve();target=(release/name).resolve()
                if not source.is_relative_to(base.resolve()) or not target.is_relative_to(release.resolve()):raise RuntimeError('Invalid reused path')
                if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['sha256'][name]:raise RuntimeError('Base asset changed')
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        for member in tar.getmembers():
            target = (release / member.name).resolve()
            if not target.is_relative_to(release) or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise RuntimeError("Unsafe archive entry")
        tar.extractall(release)
        for member in tar.getmembers():
            (release/member.name).chmod(0o755 if member.isdir() else 0o644)
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
    run(str(venv / "bin/python"), "-c", "import fastapi,uvicorn,curl_cffi; from zoneinfo import ZoneInfo; ZoneInfo('America/Toronto')")
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
    # Build finite public-shop previews before switching the site. Originals and
    # catalogue rows remain untouched; repeated deployments reuse shared files.
    preview_builder = release / "service/image_previews.py"
    if studio_db.exists() and preview_builder.exists():
        run("runuser", "-u", "pindou", "--", str(venv / "bin/python"), str(preview_builder),
            "--db", str(studio_db), "--media-dir", str(shared / "media"))
    # Lazy routes in an open tab still import the previous build's hashed files.
    # Seed all verified releases once, then only add new filenames on later deploys.
    retained = retain_static_assets(ROOT / "releases", ROOT / "static-history")
    print(json.dumps({"static_history": retained}), flush=True)
    snippet = '''    # PinDou Studio preview (managed by studio_deploy.py)
    # VISION3: the public studio owns the homepage; generator paths remain below.
    location = / {
        if ($host = www.pindoupuppy.com) { return 308 https://pindoupuppy.com$request_uri; }
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
    }
    # Keep existing www visit drafts and reservation cookies on their origin.
    location = /favicon.ico { return 302 /studio-brand/puppy-v6.ico; }
    # The generator is a lazy native Studio route. API and stored pattern assets
    # continue to use the existing generator service.
    location = /tools {
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
    }
    location ^~ /tools/ {
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
        add_header X-Robots-Tag "noindex, nofollow" always;
    }
    location ~ ^/(upload|loading|result|editor|works|tutorial|me)(/.*)?$ {
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
    }
    location = /index.html { return 302 /; }
    location ~ ^/(account|messages|auth/wechat)$ {
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
        add_header Referrer-Policy "no-referrer" always;
    }
    # Assertions are exchanged over loopback, never through the public proxy.
    location ^~ /api/v1/studio-session/ { return 404; }
    location = /api/v1/user/email/send-code { return 410; }
    location = /api/v1/user/email/verify { return 410; }
    location = /api/v1/user/register { return 410; }
    location = /studio-api/auth/wechat/callback {
        access_log off;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
        add_header Referrer-Policy "no-referrer" always;
    }
    location = /visit {
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
    }
    location ~ ^/(visit|details|shop|cart|journal)(/.*)?$ {
        if ($host = www.pindoupuppy.com) { return 308 https://pindoupuppy.com$request_uri; }
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
    }
    location ~ ^/(manage|reservation|order)(/.*)?$ {
        rewrite ^ /studio-api/site break;
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
        add_header X-Robots-Tag "noindex, nofollow" always;
    }
    location = /version.json {
        root /opt/pindou/studio/current/site/studio;
        try_files $uri =404;
        add_header Cache-Control "no-store" always;
    }
    location = /studio/version.json {
        root /opt/pindou/studio/current/site;
        try_files $uri =404;
        add_header Cache-Control "no-store" always;
    }
    location ~ ^/(studio-assets|studio-fonts)/ {
        root /opt/pindou/studio/current/site/studio;
        try_files $uri @studio_static_history;
        add_header Cache-Control "public, max-age=31536000, immutable";
        add_header X-Content-Type-Options nosniff;
    }
    location @studio_static_history {
        root /opt/pindou/studio/static-history;
        try_files $uri =404;
        add_header Cache-Control "public, max-age=31536000, immutable";
        add_header X-Content-Type-Options nosniff;
    }
    location ~ ^/(studio-media|studio-brand|studio-journal)/ {
        root /opt/pindou/studio/current/site/studio;
        try_files $uri =404;
        add_header Cache-Control "no-cache";
        add_header X-Content-Type-Options nosniff;
    }
    location ~ ^/studio/(studio-assets|studio-fonts)/ {
        rewrite ^/studio/(.*)$ /$1 break;
        root /opt/pindou/studio/current/site/studio;
        try_files $uri @studio_static_history;
        add_header Cache-Control "public, max-age=31536000, immutable";
        add_header X-Content-Type-Options nosniff;
    }
    location ~ ^/studio/(studio-media|studio-brand|studio-journal)/ {
        root /opt/pindou/studio/current/site;
        try_files $uri =404;
        add_header Cache-Control "no-cache";
        add_header X-Content-Type-Options nosniff;
    }
    location = /studio { return 308 /$is_args$args; }
    location ~ ^/studio/(.*)$ { return 308 /$1$is_args$args; }
    location = /robots.txt {
        root /opt/pindou/studio/current/site/studio;
        try_files $uri =404;
    }
    location = /sitemap.xml {
        root /opt/pindou/studio/current/site/studio;
        try_files $uri =404;
    }
    location /studio-api/ {
        client_max_body_size 13m;
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
