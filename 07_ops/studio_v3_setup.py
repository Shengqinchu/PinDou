"""Apply the owner's VISION3 weekly hours once and reuse PinDou translation config.

Run on the origin AFTER the reviewed release is deployed. Does not modify the old
generator's environment, credentials, service or database. Never prints secrets.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,os,re,shutil,sqlite3,subprocess,sys

root=Path('/opt/pindou/studio');release=sys.argv[1]
if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',release):raise SystemExit('Invalid release')
backup=root/'backups'/release
if not backup.is_dir():raise SystemExit('Run the release deployment first')
db_path=root/'shared/studio.sqlite3'
with sqlite3.connect(db_path) as db:
    db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS studio_migrations(name TEXT PRIMARY KEY,applied_at TEXT NOT NULL)')
    already=db.execute("SELECT 1 FROM studio_migrations WHERE name='vision3-weekly-hours'").fetchone()
    if not already:
        values=db.execute('SELECT settings FROM reservation_policy WHERE id=1').fetchone()
        settings=json.loads(values[0])
        hours=settings.get('weekly_hours',[{'weekday':i,'enabled':True,'open':'10:00','close':'22:00'} for i in range(7)])
        for row in hours:
            if row['weekday'] in (2,3):row['close']='16:00' if row['weekday']==2 else '18:00'
        today=datetime.now(ZoneInfo('America/Toronto')).date().isoformat()
        for (encoded,) in db.execute("SELECT payload FROM studio_reservations WHERE status='confirmed' AND json_extract(payload,'$.booking.date')>=?",(today,)):
            booking=json.loads(encoded)['booking'];weekday=datetime.strptime(booking['date'],'%Y-%m-%d').weekday()
            opening=next(h for h in hours if h['weekday']==weekday)
            if booking['end']>opening['close'] or booking['start']<opening['open'] or not opening['enabled']:
                raise SystemExit('An existing confirmed visit conflicts with VISION3 hours; no policy was changed')
        settings['weekly_hours']=hours
        db.execute('UPDATE reservation_policy SET settings=?,version=version+1 WHERE id=1',(json.dumps(settings),))
        db.execute('INSERT INTO studio_migrations VALUES(?,?)',('vision3-weekly-hours',datetime.now(ZoneInfo('America/Toronto')).isoformat()))
destination=root/'shared/.env';source=Path('/opt/pindou/shared/.env')
old=destination.read_text() if destination.exists() else ''
if destination.exists():
    shutil.copyfile(destination,backup/'studio.env');(backup/'studio.env').chmod(0o600)
keys={'XIAOCHI_GPT_BASE_URL','XIAOCHI_GPT_API_KEY'}
lines=[]
for line in source.read_text().splitlines():
    key=line.split('=',1)[0].strip()
    if key in keys and not re.search(r'^'+re.escape(key)+r'\s*=',old,re.M):lines.append(line)
if not re.search(r'^STUDIO_TRANSLATION_MODEL\s*=',old,re.M):lines.append('STUDIO_TRANSLATION_MODEL=gpt-5.6-luna')
if lines:
    temp=destination.with_suffix('.v3.tmp');temp.write_text(old.rstrip()+'\n'+'\n'.join(lines)+'\n');temp.chmod(0o600);os.replace(temp,destination)
    subprocess.run(['systemctl','restart','pindou-studio'],check=True)
print(json.dumps({'weekly_hours_applied':not bool(already),'translation_config_available':all(re.search(r'^'+key+r'\s*=',destination.read_text(),re.M) for key in keys),'old_generator_modified':False}))
