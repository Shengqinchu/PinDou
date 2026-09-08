"""Origin checks; no customer records created. Includes one small translation call."""
import os,sys,json,hashlib,subprocess,time
from pathlib import Path
from datetime import timedelta
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from dotenv import dotenv_values
for key,value in dotenv_values('/opt/pindou/shared/.env').items():
    if value is not None:os.environ[key]=value
sys.path.insert(0,'/opt/pindou/current/06_backend')
from pindou.api.security import create_access_token
tokens={role:create_access_token(subject='studio-v3-verification',role=role,expires_delta=timedelta(minutes=3)) for role in ('viewer','admin')}
def call(path,role=None,body=None):
    headers={'Content-Type':'application/json'}
    if role:headers['Authorization']='Bearer '+tokens[role]
    try:
        with urlopen(Request('http://127.0.0.1:8011/studio-api'+path,headers=headers,data=None if body is None else json.dumps(body).encode()),timeout=65) as response:
            data=response.read()
            return response.status,json.loads(data) if 'application/json' in response.headers.get('Content-Type','') else data.decode()
    except HTTPError as error:return error.code,json.load(error)
status,health=call('/health');assert status==200 and health['version']=='0.6.0'
roles={}
for path in ['/manage/content','/manage/content/pages-Home','/manage/journal','/manage/reservation-blocks','/manage/reservation-notifications','/manage/reservation-policy']:
    statuses=[call(path,role)[0] for role in [None,'viewer','admin']];assert statuses==[401,403,200],(path,statuses);roles[path]=statuses
_,calendar=call('/reservation-calendar');assert len(calendar['days'])==14
assert calendar['weekly_hours'][2]['close']=='16:00' and calendar['weekly_hours'][3]['close']=='18:00'
_,policy=call('/manage/reservation-policy','admin');assert policy['max_guests_per_group']==4 and policy['max_concurrent_groups'] is None and policy['max_concurrent_guests'] is None
_,journal=call('/journal');assert len(journal['posts'])==7 and all(p['date']>'2026-06-24' and p['body_en'] for p in journal['posts'])
status,html=call('/site');assert status==200 and 'studio-published-content' in html and 'index-BFZruLT3.js' in html
_,catalog=call('/catalog');assert catalog['checkout_ready'] is False
status,translated=call('/manage/journal-translate','admin',{'title':'拼豆小屋','body':'今天我们做了两只小狗，花了两个小时。'})
assert status==200 and translated.get('title_en') and translated.get('body_en'),(status,translated)
old=hashlib.sha256(Path('/opt/pindou/current/05_web/dist/index.html').read_bytes()).hexdigest()
assert old=='506f9bd2f9f0c37c52f08924f1504286816b93bff3198aea9f1790d0eceb36aa'
services={name:subprocess.check_output(['systemctl','is-active',name],text=True).strip() for name in ['pindou','pindou-studio']};assert all(s=='active' for s in services.values())
print(json.dumps({'health':health,'roles':roles,'calendar_days':14,'wednesday_close':'16:00','thursday_close':'18:00','group_limit':4,'aggregate_limit':None,'journal_posts':len(journal['posts']),'journal_images':sum(len(p['images']) for p in journal['posts']),'published_content_in_first_html':True,'translation_endpoint':200,'new_sales':'paused','old_index_sha256':old,'release':str(Path('/opt/pindou/studio/current').resolve()),'services':services},indent=2))
