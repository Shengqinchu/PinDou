"""Deploy only the reviewed shared-account bridge over the captured live release."""
from pathlib import Path
import sys,re,shutil,tarfile,hashlib,json,sqlite3,subprocess,time
from urllib.request import urlopen

ALLOWED={'06_backend/pindou/api/studio_session.py','06_backend/pindou/services/studio_accounts.py'}


def main():
    archive,version,digest=sys.argv[1:4]
    assert re.fullmatch(r'\d{14}-studio-v7',version)
    assert hashlib.sha256(Path(archive).read_bytes()).hexdigest()==digest
    root=Path('/opt/pindou');current=root/'current';old=current.resolve()
    assert old.parent==root/'releases'
    with tarfile.open(archive) as tar:
        manifest=json.load(tar.extractfile('studio-account-overlay.json'))
        assert set(manifest['files'])==ALLOWED
        assert set(tar.getnames())==ALLOWED|{'studio-account-overlay.json'}
    assert old.name==manifest['base_release'],'Live generator changed since capture'
    for name,expected in manifest['base_files'].items():
        assert name in ALLOWED and hashlib.sha256((old/name).read_bytes()).hexdigest()==expected,'Bridge source changed'
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
            assert member.isfile() and not member.issym() and not member.islnk()
            assert (release/member.name).resolve().is_relative_to(release.resolve())
            data=tar.extractfile(member).read();target=release/member.name
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o644)
    assert manifest['version']==version
    for name,expected in manifest['files'].items():
        target=release/name;assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
        compile(target.read_text(),str(target),'exec')
    # The original generator's front-end and all unrelated backend modules are
    # copied from production, never from the workstation's other in-flight work.
    differences=[]
    for source in old.rglob('*'):
        if not source.is_file() or any(x in source.parts for x in ('.venv','node_modules','.git','__pycache__')):continue
        name=source.relative_to(old).as_posix();target=release/name
        # The new manifest is validated above; it necessarily differs on a
        # second scoped account release and is not generator application code.
        if name=='studio-account-overlay.json':continue
        if source.read_bytes()!=target.read_bytes():differences.append(name)
    assert set(differences)<=ALLOWED,differences
    def switch(target):
        pending=root/('current.'+version);assert not pending.exists() and not pending.is_symlink()
        pending.symlink_to(target);pending.replace(current)
    try:
        switch(release);subprocess.run(['systemctl','restart','pindou'],check=True)
        for _ in range(20):
            try:
                with urlopen('http://127.0.0.1:8000/health',timeout=2) as response:assert response.status==200
                break
            except Exception:time.sleep(1)
        else:raise RuntimeError('Generator health failed')
    except Exception:
        switch(old);subprocess.run(['systemctl','restart','pindou'],check=True);raise
    print(json.dumps({'release':str(release),'previous':str(old),'backup':str(backup),'changed_existing_files':differences,'new_files':[name for name in sorted(ALLOWED) if not (old/name).exists()]}))


if __name__=='__main__':main()
