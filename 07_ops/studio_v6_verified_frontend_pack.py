"""Preserve the actual published generator when its archived source is stale.

The isolated baseline was rebuilt from the local pre-V6 source and compared to
the old live JS and CSS. They are byte-identical after normalizing Vue's scoped
CSS identifier only. The V6 overlay is then applied to that verified baseline.
No unrelated local source is committed by this release helper.
"""
from pathlib import Path
import hashlib,json,tarfile,io

root=Path(__file__).resolve().parents[1];out=root/'artifacts/studio-auth-v6'
proof=json.loads((out/'frontend-baseline-verification.json').read_text())
assert all(proof[k]['identical_except_vue_scope_id'] for k in ('javascript','css'))
base=json.loads((out/'generator-base-files.json').read_text())
tree=out/'frontend-current-baseline'
version=json.loads((root/'artifacts/studio-release/latest.json').read_text())['version']
files={}
for directory in ('src','scripts','public','dist'):
    for p in (tree/'05_web'/directory).rglob('*'):
        if p.is_file():files[p.relative_to(tree).as_posix()]=p
for name in ('index.html','package.json','package-lock.json','tsconfig.json','vite.config.ts'):
    p=tree/'05_web'/name
    if p.is_file():files[p.relative_to(tree).as_posix()]=p
files={n:p for n,p in files.items() if hashlib.sha256(p.read_bytes()).hexdigest()!=base['files'].get(n)}
manifest={'version':version,'base_release':base['base_release'],'files':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},'baseline_proof':proof}
archive=out/'verified-frontend.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for name,p in files.items():tar.add(p,arcname=name)
    data=json.dumps(manifest).encode();info=tarfile.TarInfo('overlay-manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
meta={'version':version,'path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'files':len(files)}
(out/'verified-frontend.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta))
