import io,json
from PIL import Image
import app as studio
import content
from test_reservations import client,admin
import xhs_import
import time

def test_atomic_publish_is_one_version_and_conflict_keeps_both_copies(client):
    admin();path='/studio-api/manage/content/pages-Journal'
    doc=client.get(path).json();key='life_in_our_1d9155'
    doc['data'][key]=['店主自己的标题','Owner title']
    saved=client.put(path,json={'version':doc['version'],'data':doc['data'],'publish':True})
    assert saved.status_code==200 and saved.json()['version']==doc['version']+1
    assert saved.json()['published_version']==saved.json()['version']
    assert saved.json()['published']==saved.json()['data']
    doc['data'][key]=['过期窗口','Stale window']
    assert client.put(path,json={'version':doc['version'],'data':doc['data'],'publish':True}).status_code==409
    current=client.get(path).json()
    assert current['data'][key][0]==current['published'][key][0]=='店主自己的标题'
    studio.initialize()
    assert client.get(path).json()['data'][key][0]=='店主自己的标题'

def test_find_text_locates_title_and_new_process_copy(client):
    admin()
    matches=client.get('/studio-api/manage/content-search?q=铺子里').json()['items']
    assert any(item['name']=='pages-Journal' and item['key']=='life_in_our_1d9155' for item in matches)
    assert client.get('/studio-api/manage/content/components-BeadingProcess').json()['data']['title'][0]=='拼豆流程'

def test_decode_failed_upload_is_correlated_without_private_body(client):
    admin();private=b'private-image-or-contact-never-recorded'
    response=client.post('/studio-api/manage/media?secret=do-not-log',content=private)
    assert response.status_code==422 and response.json()['detail']=='image_invalid'
    assert len(response.headers['x-request-id'])==16
    events=client.get('/studio-api/manage/diagnostics').json()['events']
    event=next(e for e in events if e['request_id']==response.headers['x-request-id'])
    assert event['code']=='image_invalid' and event['status']==422
    assert 'private-image' not in json.dumps(events) and 'do-not-log' not in json.dumps(events)
    studio.app.dependency_overrides.clear()
    assert client.get('/studio-api/manage/diagnostics').status_code==401

def test_repeat_upload_same_file_and_mislabelled_mime_are_supported(client):
    admin();buf=io.BytesIO();Image.new('RGB',(96,128),'blue').save(buf,'BMP')
    first=client.post('/studio-api/manage/media',content=buf.getvalue(),headers={'Content-Type':'application/octet-stream'})
    second=client.post('/studio-api/manage/media',content=buf.getvalue(),headers={'Content-Type':'image/jpeg'})
    assert first.status_code==200 and first.json()['src']==second.json()['src']
    assert Image.open(io.BytesIO(client.get(first.json()['src']).content)).size==(96,128)
    assert client.post('/studio-api/manage/media',content=b'\x00\x00\x00\x18ftypheic'+b'\x00'*60).json()['detail']=='image_heic_unsupported'

def test_client_signals_are_bounded_and_editor_links_reject_script_urls(client):
    signal={'kind':'error','name':'TypeError','page':'/visit','asset':'index-123.js','line':25}
    assert client.post('/studio-api/client-event',json=signal).status_code==202
    assert client.post('/studio-api/client-event',json=signal|{'message':'private body'}).status_code==422
    assert client.post('/studio-api/client-event',json=signal|{'asset':'https://host/?token=secret'}).status_code==422
    admin();events=client.get('/studio-api/manage/diagnostics').json()['events']
    assert any(e['code']=='error:TypeError:index-123.js:25' for e in events)
    path='/studio-api/manage/content/components-BeadingProcess';doc=client.get(path).json();doc['data']['toolsUrl']=['javascript:alert(1)']*2
    assert client.put(path,json={'version':doc['version'],'data':doc['data'],'publish':True}).status_code==422

def test_tracked_import_progress_keeps_source_order_and_failure_creates_no_post(client,monkeypatch):
    admin();buf=io.BytesIO();Image.new('RGB',(15,21),'red').save(buf,'PNG');raw=buf.getvalue()
    note={'noteId':'c'*24,'user':{'userId':xhs_import.OWNER_ID},'title':'完整原文','desc':'原文不改。','time':1788221085000,'imageList':[{'urlDefault':'https://sns-webpic.xhscdn.com/a.png'},{'urlDefault':'https://sns-webpic.xhscdn.com/b.png'}]}
    monkeypatch.setattr(xhs_import,'retrieve',lambda s:(note,'https://www.xiaohongshu.com/explore/'+'c'*24))
    monkeypatch.setattr(xhs_import,'fetch',lambda u,image:(raw,u))
    response=client.post('/studio-api/manage/journal-import-jobs',json={'share':'https://www.xiaohongshu.com/explore/'+'c'*24})
    assert response.status_code==202;path='/studio-api/manage/journal-import-jobs/'+response.json()['id']
    content.process_import_job(studio.database)
    job=client.get(path).json()
    for _ in range(30):
        if job['status'] not in ('queued','running'):break
        time.sleep(.05);job=client.get(path).json()
    assert job['status']=='done' and job['completed']==job['total']==2
    assert job['result']['data']['date']=='2026-09-01'
    assert job['result']['data']['body']==note['desc'] and not job['result']['published']
    assert all(p['id']!=note['noteId'] for p in client.get('/studio-api/journal').json()['posts'])
    note['noteId']='d'*24
    def failed_image(url,image):raise HTTPException(422,'import_source_unavailable')
    from fastapi import HTTPException
    monkeypatch.setattr(xhs_import,'fetch',failed_image)
    response=client.post('/studio-api/manage/journal-import-jobs',json={'share':'https://www.xiaohongshu.com/explore/'+'d'*24})
    content.process_import_job(studio.database)
    job=client.get('/studio-api/manage/journal-import-jobs/'+response.json()['id']).json()
    assert job['status']=='failed'
    with studio.database() as db:assert db.execute('SELECT 1 FROM studio_journal WHERE id=?',('d'*24,)).fetchone() is None

def test_official_http_share_is_upgraded_before_fetch(monkeypatch):
    seen=[]
    def fetch(url):seen.append(url);return b'html',url
    monkeypatch.setattr(xhs_import,'fetch',fetch);monkeypatch.setattr(xhs_import,'parse_note',lambda *_:{'title':'source'})
    assert xhs_import.retrieve('copy http://xhslink.com/o/test')[0]['title']=='source'
    assert seen==['https://xhslink.com/o/test']
