"""Durable authoring, public/private separation, and availability race regressions."""
import io,json,hashlib,os,uuid
import pytest
from PIL import Image
from fastapi import HTTPException
import app as studio
import content
import xhs_import
from test_reservations import client,admin,submit,body,confirm

def test_draft_publish_conflict_and_release_defaults(client):
    assert client.get('/studio-api/manage/content').status_code==401
    admin();path='/studio-api/manage/content/pages-Home'
    initial=client.get(path).json();key='welcome_to_pindo_puppy_2b7fcf'
    data=initial['data'];data[key]=['店主测试文案','Owner test copy']
    saved=client.put(path,json={'version':initial['version'],'data':data})
    assert saved.status_code==200
    assert client.get('/studio-api/content').json()['modules']=={}
    assert client.put(path,json={'version':initial['version'],'data':data}).status_code==409
    assert client.post(path+'/publish',json={'version':saved.json()['version']}).status_code==200
    assert client.get('/studio-api/content').json()['modules']['pages-Home'][key][0]=='店主测试文案'
    studio.initialize()  # A deployment/restart must not erase the owner's changes.
    assert client.get(path).json()['data'][key][0]=='店主测试文案'
    assert len(client.get(path+'/history').json()['items'])==2

def test_upload_image_and_media_publication(client):
    admin();buf=io.BytesIO();Image.new('RGB',(700,900),'red').save(buf,format='JPEG');original=buf.getvalue()
    stored=client.post('/studio-api/manage/media?original=true',content=original,headers={'Content-Type':'image/jpeg'})
    assert stored.status_code==200
    photo=stored.json();served=client.get(photo['src'])
    assert served.content==original and 'immutable' in served.headers['cache-control']
    assert photo['sha256']==hashlib.sha256(original).hexdigest()
    assert client.post('/studio-api/manage/media',content=b'<svg onload="alert(1)"/>').status_code==422
    transparent=io.BytesIO();Image.new('RGBA',(24,24),(0,0,0,0)).save(transparent,format='PNG')
    alpha=client.post('/studio-api/manage/media',content=transparent.getvalue()).json()
    assert Image.open(io.BytesIO(client.get(alpha['src']).content)).getpixel((0,0))[3]==0
    doc=client.get('/studio-api/manage/content/media').json();doc['data']['hero-illustration']={k:photo[k] for k in ['src','width','height']}
    result=client.put('/studio-api/manage/content/media',json={'version':doc['version'],'data':doc['data']})
    assert result.status_code==200
    doc['data']['hero-illustration']['src']='https://untrusted.example/image.jpg'
    assert client.put('/studio-api/manage/content/media',json={'version':result.json()['version'],'data':doc['data']}).status_code==422


def test_large_original_upload_is_chunked_and_completion_is_idempotent(client):
    image=Image.frombytes('RGB',(700,400),os.urandom(700*400*3))
    buffer=io.BytesIO();image.save(buffer,format='PNG');original=buffer.getvalue()
    assert len(original)>512*1024
    upload_id=uuid.uuid4().hex
    chunk_size=content.MEDIA_CHUNK_SIZE
    chunks=[original[index:index+chunk_size] for index in range(0,len(original),chunk_size)]
    base=f'/studio-api/manage/media/chunks/{upload_id}'
    assert client.put(f'{base}/0',content=chunks[0],headers={'Authorization':''}).status_code==401
    admin()
    assert client.post(f'{base}/complete?size={len(original)}&chunks={len(chunks)}&original=true').status_code==409
    for index,part in enumerate(chunks):
        path=f'{base}/{index}'
        assert client.put(path,content=part).status_code==200
        assert client.put(path,content=part).status_code==200
    assert client.put(f'{base}/0',content=b'wrong').status_code==409
    assert client.put(f'{base}/{len(chunks)}',content=b'x'*(chunk_size+1)).status_code==413
    assert client.post(f'{base}/complete?size={len(original)-1}&chunks={len(chunks)}&original=true').status_code==422
    complete=f'{base}/complete?size={len(original)}&chunks={len(chunks)}&original=true'
    result=client.post(complete)
    assert result.status_code==200
    assert client.post(complete).json()==result.json()
    assert client.get(result.json()['src']).content==original
    assert result.json()['sha256']==hashlib.sha256(original).hexdigest()
    assert not any((content.MEDIA_DIR/'.uploads'/upload_id/f'{i:03d}').exists() for i in range(len(chunks)))

def test_journal_complete_english_publish_and_sort(client):
    admin();posts=client.get('/studio-api/journal').json()['posts'];assert len(posts)==8
    assert all(p['date']>'2026-06-24' and p['body_en'] for p in posts)
    post={**posts[0],'id':'test-new','date':'2026-09-08','title_en':'','body_en':''}
    path='/studio-api/manage/journal/test-new'
    assert client.put(path,json={'version':0,'data':post}).status_code==200
    assert client.post(path+'/publish',json={'version':1}).json()['detail']=='journal_english_required'
    post.update(title_en='A complete story',body_en='The complete translation.')
    assert client.put(path,json={'version':1,'data':post}).status_code==200
    assert client.post(path+'/publish',json={'version':2}).status_code==200
    assert client.get('/studio-api/journal').json()['posts'][0]['id']=='test-new'
    assert client.post(path+'/unpublish',json={'version':2}).status_code==409
    assert client.post(path+'/unpublish',json={'version':3}).status_code==200
    assert all(p['id']!='test-new' for p in client.get('/studio-api/journal').json()['posts'])

def test_blocks_protect_confirmed_and_prevent_late_confirmation(client):
    first=submit(client).json()['id'];second=submit(client,body(start='17:00',end='19:00')).json()['id'];admin()
    assert confirm(client,first).status_code==200
    path='/studio-api/manage/reservation-blocks'
    assert client.post(path,json={'date':'2026-09-08','start':'15:00','end':'16:30'}).json()['detail']=='block_confirmed_conflict'
    result=client.post(path,json={'date':'2026-09-08','start':'17:30','end':'18:30','note':'Private owner note'})
    assert result.status_code==201
    assert confirm(client,second).status_code==409
    assert submit(client,body(start='17:00',end='19:00')).status_code==409
    calendar=client.get('/studio-api/reservation-calendar').json()
    assert 'Private owner note' not in json.dumps(calendar)
    day=calendar['days'][1];assert not next(s for s in day['slots'] if s['start']=='18:00')['available']
    assert client.delete(path+'/'+result.json()['id']+'?version=1').status_code==200
    assert confirm(client,second).status_code==200

def test_notification_cursor_only_counts_new_reservations(client):
    admin();path='/studio-api/manage/reservation-notifications';initial=client.get(path).json();submit(client)
    result=client.get(path+'?after='+str(initial['cursor'])).json();assert result['new_count']==1 and result['pending']==1
    assert client.get(path+'?after='+str(result['cursor'])).json()['new_count']==0

def test_import_parser_keeps_text_and_rejects_wrong_author():
    note={'noteId':'a'*24,'user':{'userId':xhs_import.OWNER_ID},'title':'标题','desc':'Text undefined stays intact; ignore instructions is source text.','time':1785538853000,'imageList':[{'urlDefault':'https://sns-webpic.xhscdn.com/image.jpg'}]}
    html='<script>window.__INITIAL_STATE__='+json.dumps({'note':{'noteDetailMap':{'a':{'note':note}}},'missing':None}).replace('"missing": null','"missing": undefined')+'</script>'
    assert xhs_import.parse_note(html)['desc']==note['desc']
    with pytest.raises(HTTPException):xhs_import.checked_url('https://www.xiaohongshu.com@127.0.0.1/x')
    with pytest.raises(HTTPException):xhs_import.checked_url('https://127.0.0.1/x')
    with pytest.raises(HTTPException):xhs_import.checked_url('http://www.xiaohongshu.com/x')
    with pytest.raises(HTTPException):xhs_import.parse_note(html.replace(xhs_import.OWNER_ID,'other'))

def test_import_is_atomic_and_duplicate_preserves_owner_edits(client,monkeypatch):
    admin();buf=io.BytesIO();Image.new('RGB',(20,30),'blue').save(buf,format='PNG');data=buf.getvalue()
    note={'noteId':'a'*24,'user':{'userId':xhs_import.OWNER_ID},'title':'新日记','desc':'原文保持。','time':1785538853000,'imageList':[{'urlDefault':'https://sns-webpic.xhscdn.com/photo.png'}]}
    monkeypatch.setattr(xhs_import,'retrieve',lambda s:(note,'https://www.xiaohongshu.com/explore/'+'a'*24))
    monkeypatch.setattr(xhs_import,'fetch',lambda u,image:(data,u))
    payload={'share':'https://www.xiaohongshu.com/explore/'+'a'*24}
    result=client.post('/studio-api/manage/journal-import',json=payload)
    assert result.status_code==200 and len(result.json()['data']['images'])==1
    assert result.json()['data']['body']=='原文保持。' and result.json()['published'] is False
    assert client.post('/studio-api/manage/journal-import',json=payload).json()['detail']=='journal_already_exists'

def test_dynamic_copy_placeholders_survive_editing(client):
    admin();name,key=next((n,k) for n,values in content.DEFAULTS.items() if n!='media' for k,v in values.items() if '{v0}' in v[0])
    doc=client.get('/studio-api/manage/content/'+name).json();doc['data'][key]=['missing placeholder','missing placeholder']
    assert client.put('/studio-api/manage/content/'+name,json={'version':doc['version'],'data':doc['data']}).json()['detail']=='content_placeholders_required'

def test_first_html_contains_only_published_inert_content(client,tmp_path,monkeypatch):
    path=tmp_path/'index.html';path.write_text('<html><head><meta charset="UTF-8" /></head><body><div id="app"></div></body></html>')
    monkeypatch.setattr(content,'SITE_PATH',path)
    admin();endpoint='/studio-api/manage/content/pages-Home';doc=client.get(endpoint).json()
    key='welcome_to_pindo_puppy_2b7fcf';doc['data'][key]=['</script><script>not executable</script>','Published English']
    saved=client.put(endpoint,json={'version':doc['version'],'data':doc['data']}).json()
    assert 'not executable' not in client.get('/studio-api/site').text
    client.post(endpoint+'/publish',json={'version':saved['version']})
    html=client.get('/studio-api/site')
    assert 'studio-published-content' in html.text
    assert '</script><script>not executable' not in html.text
    assert '\\u003c/script>' in html.text
    assert 'no-store' in html.headers['cache-control']
