"""Read-only release/data fingerprints. Does not export customer records or secrets."""
from pathlib import Path
import json,sys,paramiko
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[1]
cfg=dotenv_values(root/'.env')
remote=r'''
from pathlib import Path
import hashlib,json,sqlite3,subprocess
result={}
for label,path in [('studio','/opt/pindou/studio/shared/studio.sqlite3'),('generator','/opt/pindou/shared/var/pindou.db')]:
 db=sqlite3.connect('file:'+path+'?mode=ro',uri=True)
 names=[x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
 tables={}
 for name in names:
  if any(word in name for word in ('account','user','artwork','wallet','credit','member','reservation','identit','binding','claim','policy','journal')) and not any(word in name for word in ('log','limit','job')):
   rows=db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid').fetchall()
   tables[name]={'rows':len(rows),'sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,default=str,separators=(',',':')).encode()).hexdigest()}
 if label=='studio':
  def fingerprint(rows):return hashlib.sha256(json.dumps(rows,ensure_ascii=False,default=str,separators=(',',':')).encode()).hexdigest()
  protected={}
  for row in db.execute('SELECT owner_id,name,email,minutes,staff_note,created_at FROM studio_members ORDER BY owner_id'):
   protected[hashlib.sha256(row[0].encode()).hexdigest()]=fingerprint(row)
  columns=[row[1] for row in db.execute('PRAGMA table_info(studio_wallet_ledger)') if row[1] not in ('redemption_use','no_promotion')]
  old_entries=db.execute('SELECT '+','.join('"'+c+'"' for c in columns)+" FROM studio_wallet_ledger WHERE kind!='registration_reward' ORDER BY rowid").fetchall()
  rewards=db.execute("SELECT count(*),coalesce(sum(points_delta),0) FROM studio_wallet_ledger WHERE kind='registration_reward'").fetchone()
  result['studio_preservation']={'existing_member_time_notes_identity':protected,'non_registration_ledger':{'rows':len(old_entries),'sha256':fingerprint(old_entries)},'registration_rewards':{'rows':rewards[0],'points':rewards[1]}}
  row=db.execute("SELECT published,draft,version,published_version FROM studio_content WHERE name='wallet'").fetchone()
  result['wallet_copy']={key:{k:v for k,v in json.loads(row[index]).items() if k in ('earn_rule','attendance_help')} for index,key in enumerate(('published','draft'))}
  result['wallet_copy']['version']=row[2];result['wallet_copy']['published_version']=row[3]
 result[label+'_data']=tables;db.close()
for label,base in [('studio','/opt/pindou/studio/current'),('generator','/opt/pindou/current')]:
 result[label+'_release']=str(Path(base).resolve())
 if label=='studio':
  manifest=json.loads((Path(base)/'manifest.json').read_text());result['studio_files']=len(manifest['sha256'])
  result['studio_files_valid']=all(hashlib.sha256((Path(base)/name).read_bytes()).hexdigest()==digest for name,digest in manifest['sha256'].items())
 else:result['generator_html_sha256']=hashlib.sha256((Path(base)/'05_web/dist/index.html').read_bytes()).hexdigest()
result['services']=subprocess.check_output(['systemctl','is-active','pindou','pindou-studio']).decode().splitlines()
result['ntp']=subprocess.check_output(['timedatectl','show','-p','NTPSynchronized']).decode().strip()
print(json.dumps(result,ensure_ascii=False,indent=2))
'''
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(cfg['PINDOU_PROD_SSH_HOST'],username='root',key_filename=cfg['PINDOU_PROD_SSH_KEY_PATH'],timeout=25)
try:
 stdin,stdout,stderr=c.exec_command('python3 -',timeout=60);stdin.write(remote);stdin.channel.shutdown_write()
 data=stdout.read().decode();err=stderr.read().decode();assert stdout.channel.recv_exit_status()==0,err
 value=json.loads(data);target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(data,encoding='utf-8')
 print(json.dumps({'saved':str(target),'studio':value['studio_release'],'generator':value['generator_release'],'files_valid':value['studio_files_valid'],'services':value['services'],'wallet_copy':value['wallet_copy']},ensure_ascii=False))
finally:c.close()
