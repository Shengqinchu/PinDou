"""Reassemble separately transferred release parts in /tmp, verifying the local hash.

This performs no deployment. The normal reviewed studio_deploy.py still validates
the assembled archive, its paths and each file before switching the live release.
"""
from pathlib import Path
import hashlib, json, re, shutil, sys

version, count, expected = sys.argv[1:4]
if not re.fullmatch(r'[0-9]{14}-studio-v[1234567]', version) or not re.fullmatch(r'[a-f0-9]{64}', expected):
    raise SystemExit('Invalid release arguments')
count=int(count)
if not 1 <= count <= 50: raise SystemExit('Invalid part count')
root=Path('/tmp')
target=root/(version+'.tar.gz')
if target.exists():
    if hashlib.sha256(target.read_bytes()).hexdigest()!=expected: raise SystemExit('Different archive already exists')
else:
    temporary=root/(version+'.assembling')
    with temporary.open('wb') as output:
        for index in range(count):
            with (root/(version+f'.part-{index:02d}')).open('rb') as part:
                shutil.copyfileobj(part,output)
    if hashlib.sha256(temporary.read_bytes()).hexdigest()!=expected: raise SystemExit('Assembled archive hash mismatch')
    temporary.replace(target)
print(json.dumps({'archive':str(target),'sha256':expected,'parts':count}))
