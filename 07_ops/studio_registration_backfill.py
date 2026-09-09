"""Origin-only, explicitly authorized registration reward backfill; dry-run by default.

Reads the existing shared account DB. Does not expose account details in output.
Each award uses the same unique ledger key as normal sign-in.
"""
import argparse,json,os,re,sqlite3,sys
from datetime import datetime,timezone
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    base=Path('/opt/pindou/studio');dbpath=base/'shared/studio.sqlite3'
    with sqlite3.connect('file:/opt/pindou/shared/var/pindou.db?mode=ro',uri=True) as source:
        rows=source.execute('SELECT openid,email,nickname FROM users ORDER BY id').fetchall()
    eligible=[r for r in rows if isinstance(r[0],str) and 0<len(r[0])<=128 and isinstance(r[1],str) and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',r[1])]
    with sqlite3.connect(f'file:{dbpath}?mode=ro',uri=True) as db:
        existing=sum(bool(db.execute('SELECT 1 FROM studio_wallet_ledger WHERE idempotency_key=?',('registration-reward:'+r[0],)).fetchone()) for r in eligible)
    if not args.apply:
        print(json.dumps({'eligible':len(eligible),'already_awarded':existing,'to_award':len(eligible)-existing,'points_to_add':166*(len(eligible)-existing),'skipped_without_email':len(rows)-len(eligible)}));return
    backup=base/'backups'/('registration-reward-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')+'.sqlite3')
    assert backup.resolve().parent==(base/'backups').resolve() and not backup.exists()
    with sqlite3.connect(f'file:{dbpath}?mode=ro',uri=True) as source,sqlite3.connect(backup) as destination:source.backup(destination)
    backup.chmod(0o600)
    os.environ['STUDIO_DB_PATH']=str(dbpath);sys.path.insert(0,str(base/'current/service'))
    import app as studio
    import wallet
    assert wallet.REGISTRATION_REWARD==166
    count=0;created=0
    for owner,email,nickname in eligible:
        with studio.database() as db:
            db.execute('BEGIN IMMEDIATE');before=db.execute('SELECT * FROM studio_members WHERE owner_id=?',(owner,)).fetchone()
            if before is None:
                db.execute('INSERT INTO studio_members(owner_id,name,email,created_at,updated_at) VALUES(?,?,?,?,?)',(owner,nickname or email,email,wallet.now(),wallet.now()));created+=1
            awarded=wallet.reward_registration(db,owner);count+=int(awarded)
            if before is not None:
                after=db.execute('SELECT * FROM studio_members WHERE owner_id=?',(owner,)).fetchone()
                assert all(before[key]==after[key] for key in ('owner_id','name','email','minutes','staff_note','created_at'))
                assert after['points']==before['points']+(166 if awarded else 0)
                assert after['version']==before['version']+(1 if awarded else 0)
    print(json.dumps({'eligible':len(eligible),'awarded_now':count,'already_awarded':len(eligible)-count,'points_added':count*166,'members_created':created,'preserved_existing_time_notes_identity':True,'backup':str(backup)}))

if __name__=='__main__':main()
