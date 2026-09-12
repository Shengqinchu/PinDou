"""Package only the studio build/service and record hashes for the origin deployer."""
import hashlib
import io
import json
import tarfile
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/studio-release'
out.mkdir(parents=True, exist_ok=True)
version = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '-studio-v7'
dist = root / '05_studio/dist'
if not (dist / 'index.html').is_file():
    raise SystemExit('Build the studio frontend first.')
files = {'site/studio/' + p.relative_to(dist).as_posix(): p for p in dist.rglob('*') if p.is_file()}
for name in ['app.py', 'commerce.py', 'payments.py', 'reservations.py', 'reservation-offers.json', 'customer_auth.py', 'authing_login.py', 'wechat_qr.py', 'wallet.py', 'booking_profile.py', 'owner_notifications.py', 'observability.py', 'content.py', 'xhs_import.py', 'content-defaults.json', 'journal-defaults.json', 'requirements.txt', 'requirements.lock.txt']:
    files['service/' + name] = root / '06_studio' / name
files['service/owner-notification-copy.json'] = root / '05_studio/src/content/owner-notifications.json'
files['service/telegram_notifications.py'] = root / '06_studio/telegram_notifications.py'
files['service/telegram-notification-copy.json'] = root / '05_studio/src/content/telegram-notifications.json'
files['service/miniapp_login.py'] = root / '06_studio/miniapp_login.py'
files['service/shop_catalog.py'] = root / '06_studio/shop_catalog.py'
files['service/shop-categories.json'] = root / '06_studio/shop-categories.json'
files['service/shop-services.json'] = root / '06_studio/shop-services.json'
for name in ('sms_inbox.py','owner_wechat.py','studio_staff.py','studio_finance.py','finance_fx.py','studio_messages.py','customer_notifications.py'):
    files['service/'+name] = root / '06_studio' / name
for name in ('xhs_browser.py',):
    files['service/'+name] = root / '06_studio' / name
files['service/messaging-copy.json'] = root / '05_studio/src/content/messaging.json'
files['service/owner-wechat-copy.json'] = root / '05_studio/src/content/owner-wechat.json'
files['service/business-copy.json'] = root / '05_studio/src/content/business.json'
files['service/customer-notification-copy.json'] = root / '05_studio/src/content/customer-notifications.json'
files['service/studio-profile.json'] = root / '05_studio/src/content/studio-profile.json'
manifest = {'version': version, 'sha256': {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in files.items()}}
reused=set()
if len(sys.argv)>1:
    base=json.loads(Path(sys.argv[1]).read_text())
    reused={name for name,value in manifest['sha256'].items() if base['sha256'].get(name)==value}
    manifest.update(base_version=base['version'],reuse=sorted(reused))
archive = out / (version + '.tar.gz')
with tarfile.open(archive, 'x:gz') as tar:
    for name, p in files.items():
        if name not in reused:tar.add(p, arcname=name)
    data = json.dumps(manifest, indent=2).encode()
    info = tarfile.TarInfo('manifest.json')
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))
result = {'version': version, 'archive': str(archive), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': len(files)}
(out / 'latest.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result, indent=2))
