import hashlib
import io
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse,parse_qs

import pytest
import app as studio
import owner_notifications as outbox
import telegram_notifications as telegram
from test_owner_notifications import setup,host,create,configure as configure_wechat

TOKEN='1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ_1234567890'
PATH='/studio-api/manage/telegram-notifications'


@pytest.fixture
def service(setup,monkeypatch):
    client,sc_sent,path=setup
    calls=[];incoming=[]
    def api(token,method,payload=None):
        calls.append((method,payload))
        if method=='getMe':return {'ok':True,'result':{'id':1234567890,'is_bot':True,'username':'PindouLocalTestBot'}}
        if method=='getWebhookInfo':return {'ok':True,'result':{'url':''}}
        if method=='getUpdates':return {'ok':True,'result':list(incoming)}
        if method=='sendMessage':return {'ok':True,'result':{'message_id':123}}
        raise AssertionError(method)
    monkeypatch.setattr(telegram,'api',api)
    return client,sc_sent,path,calls,incoming


def configure(client,**changes):
    host();version=client.get(PATH).json()['version']
    return client.put(PATH,json={'version':version,'token':TOKEN,**changes})


def begin(client):
    response=client.post(PATH+'/bind');assert response.status_code==200,response.text
    result=response.json()
    return result,parse_qs(urlparse(result['url']).query)['start'][0]


def incoming_message(challenge,who=543210001,chat_type='private',sender=None):
    return {'update_id':100,'message':{'date':int(time.time()),'text':'/start '+challenge,
            'chat':{'id':who,'type':chat_type},'from':{'id':who if sender is None else sender,'first_name':'Local Owner','is_bot':False}}}


def connect(service):
    client,_,_,_,incoming=service
    assert configure(client).status_code==200
    link,challenge=begin(client);incoming.append(incoming_message(challenge))
    result=client.post(PATH+'/bind/check',json={'id':link['id']})
    assert result.status_code==200,result.text
    assert result.json()['connected']
    return link


def all_jobs():
    with studio.database() as db:return [dict(r) for r in db.execute('SELECT * FROM studio_owner_notifications ORDER BY created_at')]


def test_admin_only_bot_validation_and_private_token(service):
    client,_,path,calls,_=service
    assert client.get(PATH).status_code==401
    assert client.post(PATH+'/bind').status_code==401
    assert client.put(PATH,json={'version':1,'token':TOKEN}).status_code==401
    assert calls==[]
    response=configure(client)
    assert response.status_code==200 and response.json()['configured'] and not response.json()['connected']
    assert TOKEN not in response.text
    with studio.database() as db:assert TOKEN not in '\n'.join(db.iterdump())
    assert (path/'telegram-secret.json').exists()
    assert configure(client,token='invalid').status_code==422
    assert configure(client,enabled=True,token='').status_code==409


@pytest.mark.parametrize('chat_type,sender,valid_token',[('group',None,True),('private',555,True),('private',None,False)])
def test_only_private_matching_pairing_challenge_is_accepted(service,chat_type,sender,valid_token):
    client,_,_,calls,incoming=service
    configure(client);link,challenge=begin(client)
    incoming.append(incoming_message(challenge if valid_token else 'unrelated',chat_type=chat_type,sender=sender))
    result=client.post(PATH+'/bind/check',json={'id':link['id']})
    assert result.status_code==200 and result.json()['connected'] is False
    assert not client.get(PATH).json()['connected']
    assert not any(c[0]=='sendMessage' for c in calls)
    with studio.database() as db:
        saved=db.execute('SELECT token_hash FROM studio_telegram_bindings WHERE id=?',(link['id'],)).fetchone()[0]
        assert saved==hashlib.sha256(challenge.encode()).hexdigest() and saved!=challenge


def test_pairing_is_one_time_and_test_uses_no_customer_booking(service):
    client,_,_,calls,_=service
    link=connect(service)
    assert client.post(PATH+'/bind/check',json={'id':link['id']}).json()['connected']
    assert len(all_jobs())==1
    with studio.database() as db:assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==0
    outbox.process_one(studio.database,'telegram')
    assert all_jobs()[0]['state']=='accepted'
    message=[p for m,p in calls if m=='sendMessage'][0]
    assert message['chat_id']=='543210001' and message['disable_notification'] is False
    assert message['reply_markup']['inline_keyboard'][0][0]['url'].startswith('https://pindoupuppy.com/manage')


def test_expiry_and_replacement_invalidate_pairing(service):
    client,_,_,_,incoming=service
    configure(client);first,challenge=begin(client);second,_=begin(client)
    incoming.append(incoming_message(challenge))
    assert client.post(PATH+'/bind/check',json={'id':first['id']}).status_code==409
    with studio.database() as db:db.execute('UPDATE studio_telegram_bindings SET expires_at=0')
    assert client.post(PATH+'/bind/check',json={'id':second['id']}).status_code==409


def test_configuration_does_not_take_over_existing_webhook(service,monkeypatch):
    client,_,path,_,_=service
    original=telegram.api
    monkeypatch.setattr(telegram,'api',lambda token,method,payload=None:{'ok':True,'result':{'url':'https://existing.example/hook'}} if method=='getWebhookInfo' else original(token,method,payload))
    assert configure(client).status_code==409
    assert not (path/'telegram-secret.json').exists()


def test_both_channels_enqueue_once_and_quota_does_not_cross(service):
    client,_,_,calls,_=service
    configure_wechat(client,daily_limit=5);connect(service)
    key=str(uuid.uuid4());first=create(client,key);assert first.status_code==201
    assert create(client,key).json()['id']==first.json()['id']
    entries=all_jobs()
    assert len([e for e in entries if e['kind']=='created'])==2
    outbox.process_one(studio.database,'telegram')
    assert client.get('/studio-api/manage/owner-notifications').json()['used']==0
    outbox.process_one(studio.database)
    assert client.get('/studio-api/manage/owner-notifications').json()['used']==1
    assert len(client.get(PATH).json()['items'])==2
    assert len(client.get('/studio-api/manage/owner-notifications').json()['items'])==1
    assert client.post('/studio-api/reservations/'+first.json()['id']+'/cancel',json={'version':1}).status_code==200
    assert len([e for e in all_jobs() if e['kind']=='cancelled'])==2


def test_telegram_timeout_does_not_block_wechat_worker(service,monkeypatch):
    client,sc_sent,_,_,_=service
    configure_wechat(client);connect(service);create(client)
    entered=threading.Event();release=threading.Event()
    def slow(*args):
        entered.set();assert release.wait(5)
        return {'ok':False,'error':'telegram_network_error','retry':True}
    monkeypatch.setattr(telegram,'deliver',slow)
    with ThreadPoolExecutor() as pool:
        pending=pool.submit(outbox.process_one,studio.database,'telegram')
        try:
            assert entered.wait(5)
            assert outbox.process_one(studio.database)
            assert len(sc_sent)==1
        finally:release.set()
        assert pending.result(5)
    assert any(r['channel']=='telegram' and r['state']=='retry' for r in all_jobs())


def test_old_pending_jobs_do_not_leak_to_changed_recipient(service):
    client,_,_,calls,_=service
    connect(service)
    with studio.database() as db:
        db.execute("UPDATE studio_telegram_settings SET chat_id='222222222',chat_label='Other owner',version=version+1")
    outbox.process_one(studio.database,'telegram')
    assert all_jobs()[0]['state']=='skipped'
    assert not any(m=='sendMessage' for m,_ in calls)


def test_token_rotation_to_other_bot_clears_recipient(service,monkeypatch):
    client,_,_,_,_=service
    connect(service);original=telegram.api
    monkeypatch.setattr(telegram,'api',lambda token,method,payload=None:{'ok':True,'result':{'id':8765432100,'is_bot':True,'username':'AnotherLocalBot'}} if method=='getMe' else original(token,method,payload))
    result=configure(client,enabled=True)
    assert result.status_code==200 and not result.json()['connected'] and not result.json()['enabled']


def test_same_bot_token_can_be_restored_without_losing_recipient(service):
    client,_,path,_,_=service
    connect(service)
    (path/'telegram-secret.json').unlink()
    restored=configure(client,enabled=True)
    assert restored.status_code==200 and restored.json()['connected'] and restored.json()['enabled']


def test_render_escapes_customer_content_and_excludes_private_details(service):
    _,_,_,calls,_=service
    connect(service)
    job={'kind':'created','reservation_id':'VIS-LOCAL','payload':json.dumps({'name':'<b>hello</b> & example','contact':'private-contact',
        'notes':'private-notes','booking':{'date':'2026-09-12','start':'14:00','end':'16:00','guests':2}})}
    assert telegram.deliver(TOKEN,'543210001',job,'en')['ok']
    message=[p for m,p in calls if m=='sendMessage'][-1]
    assert '&lt;b&gt;hello&lt;/b&gt; &amp;' in message['text']
    assert 'private-contact' not in message['text'] and 'private-notes' not in message['text']
    assert 'New reservation request' in message['text']


def test_cross_channel_retry_cannot_target_wrong_job(service):
    client,_,_,_,_=service
    configure_wechat(client);connect(service);create(client)
    jobs=all_jobs();sc=next(j for j in jobs if j['channel']=='serverchan');tg=next(j for j in jobs if j['channel']=='telegram')
    assert client.post(PATH+'/'+sc['id']+'/retry').status_code==404
    assert client.post('/studio-api/manage/owner-notifications/'+tg['id']+'/retry').status_code==404


@pytest.mark.parametrize('code,error,retry',[(401,'telegram_token_invalid',False),(403,'telegram_blocked',False),(429,'telegram_rate_limit',True),(503,'telegram_rejected',True)])
def test_adapter_classifies_failures_and_honors_retry_after(monkeypatch,code,error,retry):
    class Opener:
        def open(self,*args,**kwargs):
            body=json.dumps({'ok':False,'error_code':code,'description':TOKEN,'parameters':{'retry_after':37}}).encode()
            raise HTTPError('https://api.telegram.org/bot'+TOKEN,code,'Error',{},io.BytesIO(body))
    monkeypatch.setattr(telegram,'build_opener',lambda *args:Opener())
    response=telegram.api(TOKEN,'sendMessage',{})
    assert response['error']==error and response['retry']==retry and TOKEN not in str(response)
    if code==429:assert response['delay']==37


def test_adapter_only_accepts_valid_telegram_success(monkeypatch):
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,_size):return b'{"ok":true,"result":{"message_id":12}}'
    class Opener:
        def open(self,request,timeout):
            assert timeout==12 and request.full_url.startswith('https://api.telegram.org/bot')
            return Response()
    monkeypatch.setattr(telegram,'build_opener',lambda *args:Opener())
    assert telegram.api(TOKEN,'sendMessage')['result']['message_id']==12
    with pytest.raises(ValueError):telegram.api(TOKEN,'deleteWebhook')
