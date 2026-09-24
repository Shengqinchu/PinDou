"""Package a reviewed Studio frontend build on top of the verified live release.

All service files and previous hashed assets are reused byte-for-byte from the
base manifest. This avoids shipping unrelated local backend changes.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if not re.fullmatch(r"\d{14}-studio-v7", base.get("version", "")):
    raise SystemExit("Expected a verified v7 production manifest")
base_hashes = base.get("sha256", {})
if not base_hashes or not any(name.startswith("service/") for name in base_hashes):
    raise SystemExit("Base manifest does not contain the Studio service")

dist = root / "05_studio/dist"
if not (dist / "index.html").is_file() or not (dist / "version.json").is_file():
    raise SystemExit("Build the Studio frontend first")
site = {}
for path in dist.rglob("*"):
    if path.is_symlink():
        raise SystemExit(f"Symlink in frontend build: {path}")
    if path.is_file():
        site["site/studio/" + path.relative_to(dist).as_posix()] = path
if len(site) < 100:
    raise SystemExit("Frontend build looks incomplete")

hashes = dict(base_hashes)
hashes.update({name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in site.items()})
changed = {name: path for name, path in site.items() if hashes[name] != base_hashes.get(name)}
reused = sorted(set(hashes) - set(changed))
if not changed or any(not name.startswith("site/studio/") for name in changed):
    raise SystemExit("Expected only changed frontend files")

version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-studio-v7"
manifest = {"version": version, "sha256": hashes, "base_version": base["version"], "reuse": reused}
out = root / "artifacts/studio-release"
out.mkdir(parents=True, exist_ok=True)
archive = out / (version + ".tar.gz")
with tarfile.open(archive, "w:gz") as tar:
    for name, path in sorted(changed.items()):
        tar.add(path, arcname=name)
    data = (json.dumps(manifest, indent=2) + "\n").encode()
    info = tarfile.TarInfo("manifest.json")
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))
meta = {"version": version, "archive": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": len(hashes), "changed_frontend": len(changed), "reused": len(reused), "base_version": base["version"]}
(out / "latest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
print(json.dumps(meta, indent=2))
