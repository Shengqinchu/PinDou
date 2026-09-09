"""Origin-only additive release for shared accounts. Existing data is preserved."""
from pathlib import Path
import os,sys,re,shutil,tarfile,hashlib,json,sqlite3,subprocess,time
from urllib.request import urlopen

def main():
    archive,version,digest=sys.argv[1:4]
    assert re.fullmatch(r'\d{14}-studio-v6',version)
    assert hashlib.sha256(Path(archive).read_bytes()).hexdigest()==digest
    root=Path('/opt/pindou');current=root/'current';old=current.resolve()
    with tarfile.open(archive) as tar:manifest=json.load(tar.extractfile('overlay-manifest.json'))
    assert old.name==manifest['base_release'],'Live source changed since capture'
    release=root/'releases'/version;assert not release.exists()
    backup=root/'backups'/version;backup.mkdir(parents=True,mode=0o700,exist_ok=True)
    (backup/'state.json').write_text(json.dumps({'previous_current':str(old)}))
    dbpath=root/'shared/var/pindou.db';assert dbpath.is_file()
    with sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True) as source:
        with sqlite3.connect(backup/'pindou.db') as dest:source.backup(dest)
    (backup/'pindou.db').chmod(0o600)
    skipped=[]
    def ignore(path,names):
        result=[]
        for name in names:
            if name in ('.venv','node_modules','.git','__pycache__'):
                result.append(name)
                if name in ('.venv','node_modules'):skipped.append(Path(path)/name)
        return result
    shutil.copytree(old,release,symlinks=True,ignore=ignore)
    for path in skipped:(release/path.relative_to(old)).symlink_to(path.resolve(),target_is_directory=True)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            assert (release/member.name).resolve().is_relative_to(release.resolve())
            assert not member.issym() and not member.islnk() and (member.isfile() or member.isdir())
        tar.extractall(release)
        for member in tar.getmembers():(release/member.name).chmod(0o755 if member.isdir() else 0o644)
    manifest=json.loads((release/'overlay-manifest.json').read_text())
    assert manifest['base_release']==old.name and manifest['version']==version
    for name,expected in manifest['files'].items():assert hashlib.sha256((release/name).read_bytes()).hexdigest()==expected
    def switch(target):
        pending=root/'current.v6-next';assert not pending.exists()
        pending.symlink_to(target);pending.replace(current)
    try:
        switch(release)
        if any(name.startswith('06_backend/') for name in manifest['files']):subprocess.run(['systemctl','restart','pindou'],check=True)
        for _ in range(20):
            try:
                with urlopen('http://127.0.0.1:8000/health',timeout=2) as response:
                    assert response.status==200
                break
            except Exception:time.sleep(1)
        else:raise RuntimeError('Generator health failed')
    except Exception:
        switch(old);subprocess.run(['systemctl','restart','pindou'],check=True);raise
    print(json.dumps({'release':str(release),'backup':str(backup),'files':len(manifest['files']),'previous':str(old)}))

if __name__=='__main__':main()
