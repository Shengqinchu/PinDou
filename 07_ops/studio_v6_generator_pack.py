"""Package the narrow generator overlay built from the captured live source."""
from pathlib import Path
import json,tarfile,hashlib,io
from studio_v6_generator_overlay import FILES,TRANSFORMS
root=Path(__file__).resolve().parents[1];base=root/'artifacts/studio-auth-v6/origin-build'
release=json.loads((root/'artifacts/studio-release/latest.json').read_text())['version']
files={name:base/name for name in FILES+TRANSFORMS}
files.update({p.relative_to(base).as_posix():p for p in (base/'05_web/dist').rglob('*') if p.is_file()})
manifest={'version':release,'base_release':'20260615074539-wallet-mode-labels','files':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}}
out=root/'artifacts/studio-auth-v6/generator-overlay.tar.gz'
with tarfile.open(out,'w:gz') as tar:
    for name,p in files.items():tar.add(p,arcname=name)
    data=json.dumps(manifest).encode();item=tarfile.TarInfo('overlay-manifest.json');item.size=len(data);tar.addfile(item,io.BytesIO(data))
meta={'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,'version':release,'files':len(files)}
(out.parent/'generator-overlay.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta))
