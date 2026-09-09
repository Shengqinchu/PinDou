"""Apply only the V6 account/navigation changes to a reviewed generator tree.

Used against the saved production-source snapshot so unrelated in-progress
generator changes are never bundled into a Studio release.
"""
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
FILES=['05_web/src/main.ts','05_web/src/stores/auth.ts','05_web/src/auth/sharedSession.ts',
       '06_backend/pindou/api/__init__.py','06_backend/pindou/api/studio_session.py']


def transform(name,source):
    if name=='05_web/src/App.vue':
        source=source.replace('<RouterLink class="brand" to="/" aria-label="PinDou 首页">','<a class="brand" href="/" aria-label="PinDou 首页">')
        # The first closing RouterLink belongs to the logo link.
        source=source.replace('</RouterLink>','</a>',1)
        source=source.replace('<RouterLink class="nav-link nav-link--home" to="/">首页</RouterLink>','<a class="nav-link nav-link--home" href="/">首页</a>')
    elif name=='05_web/src/components/AccountMenu.vue':
        anchor='<div class="account-menu-list">'
        assert source.count(anchor)==1
        source=source.replace(anchor,anchor+'\n          <button type="button" role="menuitem" @click="openAccountCentre">账号中心 · 时长与积分</button>')
        source=source.replace('function toggleMenu(): void {',"function openAccountCentre(): void { window.location.assign('/account'); }\n\nfunction toggleMenu(): void {")
    elif name=='05_web/index.html':
        source=source.replace('<link rel="icon" type="image/png" href="/brand/favicon.png" />', '<link rel="icon" href="/studio-brand/puppy-v6.ico" sizes="16x16 32x32 48x48 64x64 128x128 256x256" />\n    <link rel="icon" type="image/svg+xml" href="/studio-brand/puppy-v6.svg" sizes="any" />\n    <link rel="apple-touch-icon" href="/studio-brand/puppy-icon-180-v6.png" />')
        source=source.replace('    <link rel="shortcut icon" href="/favicon.ico" />\n','')
    else: raise ValueError(name)
    return source


TRANSFORMS=['05_web/src/App.vue','05_web/src/components/AccountMenu.vue','05_web/index.html']

if __name__=='__main__':
    target=Path(sys.argv[1]).resolve()
    for name in FILES:
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,path)
    for name in TRANSFORMS:
        path=target/name;path.write_text(transform(name,path.read_text(encoding='utf8')),encoding='utf8')
    print('Applied V6 account overlay: '+str(target))
