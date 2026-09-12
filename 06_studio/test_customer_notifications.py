"""Booking lifecycle, subscription identity and retry tests; no external deliveries."""
import asyncio,json,uuid
from datetime import datetime
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from fastapi.testclient import TestClient
import app as studio
import customer_auth,customer_notifications as notices,studio_messages,owner_notifications,owner_wechat,miniapp_login as mini,reservations,sms_inbox as sms
from auth_fixture import fake_upstream,reject_legacy_admin
from test_sms_inbox import bridge,claim,begin
from test_owner_wechat import ticket,APP_ID


@pytest.fixture
def setup(tmp_path,monkeypatch):
    studio.app.dependency_overrides.clear()
    monkeypatch.setattr(studio,'DB_PATH',tmp_path/'studio.sqlite3')
    monkeypatch.setattr(customer_auth,'upstream',fake_upstream)
    monkeypatch.setattr(studio,'urlopen',reject_legacy_admin)
    monkeypatch.setattr(reservations,'COOKIE_SECURE',False)
    now=[datetime(2026,9,10,9,tzinfo=reservations.ZONE).timestamp()]
    monkeypatch.setattr(reservations,'now_local',lambda:datetime.fromtimestamp(now[0],reservations.ZONE))
    clock=SimpleNamespace(time=lambda:now[0])
    monkeypatch.setattr(notices,'time',clock);monkeypatch.setattr(sms,'time',clock)
    monkeypatch.setattr(studio_messages,'time',clock)
    monkeypatch.setattr(mini,'config',lambda:SimpleNamespace(app_id=APP_ID,environment='trial'))
    monkeypatch.setenv('STUDIO_CUSTOMER_TEMPLATES_FILE',str(tmp_path/'missing.json'))
    async def paused(*args):await asyncio.Event().wait()
    for module in (notices,owner_notifications,owner_wechat):monkeypatch.setattr(module,'worker',paused)
    calls=[]
    monkeypatch.setattr(notices,'send_email',lambda job,payload:(calls.append((job,payload)) or ('accepted','','local-email')))
    with TestClient(studio.app) as client:
        client.headers['Authorization']='Bearer qa-owner'
        client.get('/studio-api/reservation-calendar')
        yield client,now,calls
    studio.app.dependency_overrides.clear()


def host():studio.app.dependency_overrides[studio.admin_actor]=lambda:'test-admin'


def pref(client,**changes):
    current=client.get('/studio-api/auth/notifications').json()
    data={k:current[k] for k in ('email','phone','email_enabled','sms_enabled','version')}
    return client.put('/studio-api/auth/notifications',json=data|changes)


def create(client,key=None):
    result=client.post('/studio-api/reservations',headers={'Idempotency-Key':key or str(uuid.uuid4())},json={
      'booking':{'date':'2026-09-11','start':'14:00','end':'16:00','plan':'hourly','guests':2},
      'name':'Local <Guest>','contact_method':'wechat','contact':'local-test','consent':True,'locale':'en'})
    assert result.status_code==201,result.text
    return result.json()['id']


def status(client,ident,value):
    host();version=client.get('/studio-api/reservations/'+ident).json()['version']
    result=client.patch('/studio-api/manage/reservations/'+ident,json={'version':version,'status':value})
    assert result.status_code==200,result.text


def jobs():
    with studio.database() as db:return [dict(r) for r in db.execute('SELECT * FROM studio_customer_notification_jobs ORDER BY created_at,id')]


def drain():
    for _ in range(30):
        if not notices.process_one(studio.database):return
    raise AssertionError('Worker did not become idle')


def setup_wechat():
    headers=ticket()
    with studio.database() as db:
        db.execute('INSERT INTO studio_miniapp_identities VALUES(?,?,?,?)',(APP_ID,'local-openid-'+'1'*18,'qa-owner',0))
        for kind in notices.KINDS:db.execute('INSERT INTO studio_customer_notification_templates VALUES(?,?,?,?)',(kind,'T'*25+kind,kind,json.dumps({'thing1':'place','time2':'start','time3':'end','thing4':'service','thing5':'note'})))
    return headers


def test_contact_preferences_opt_in_and_version(setup):
    client,_,_=setup
    first=client.get('/studio-api/auth/notifications').json()
    assert not first['sms_enabled'] and first['email_enabled'] and first['email']=='qa-owner@example.test'
    # An old +86 contact does not block bookings when phone notices are off.
    assert pref(client,phone='+8619558948263',email='invalid',email_enabled=False).status_code==200
    assert pref(client,sms_enabled=True,phone='+8619558948263').status_code==422
    assert pref(client,email_enabled=True,email='bad').status_code==422
    saved=pref(client,sms_enabled=True,phone='(416) 555-0123').json()
    assert saved['phone']=='+14165550123'
    assert pref(client,version=0).status_code==409
    client.headers['Authorization']='Bearer qa-other'
    assert client.get('/studio-api/auth/notifications').json()['version']==0
    assert client.get('/studio-api/manage/customer-notifications').status_code==401


def test_pending_confirmation_reminder_cancel_are_distinct_and_idempotent(setup):
    client,now,calls=setup
    assert pref(client,email_enabled=True,email='local@example.test').status_code==200
    key=str(uuid.uuid4());ident=create(client,key);assert create(client,key)==ident
    assert [r['kind'] for r in jobs()]==['pending']
    drain();assert calls[0][1]['title']=='Booking request received'
    assert 'confirmed' not in calls[0][1]['title'].lower()
    status(client,ident,'confirmed');drain()
    assert len(calls)==2 and calls[-1][1]['title']=='Booking confirmed'
    assert calls[-1][1]['url'].endswith(ident)
    reminder=next(r for r in jobs() if r['kind']=='reminder')
    assert reminder['due_at']==datetime(2026,9,11,12,tzinfo=reservations.ZONE).timestamp()
    status(client,ident,'cancelled');drain();assert calls[-1][1]['title']=='Booking cancelled'
    now[0]=reminder['due_at']+1;drain();assert len(calls)==3
    assert next(r for r in jobs() if r['kind']=='reminder')['state']=='skipped'
    messages=client.get('/studio-api/auth/messages').json()['items']
    assert len(messages)==3 and all(r['sender_role']=='system' for r in messages)


def test_queued_email_is_stopped_after_opt_out(setup):
    client,_,calls=setup
    pref(client,email_enabled=True,email='local@example.test');create(client)
    pref(client,email_enabled=False);drain()
    assert not calls and jobs()[0]['state']=='skipped'


def test_sms_is_idempotent_and_rechecks_cancellation_before_physical_send(setup):
    client,_,_=setup
    pref(client,sms_enabled=True,phone='+14165550123');bridge()
    ident=create(client);drain()
    job=claim(client);assert job and 'waiting' in job['content']
    status(client,ident,'cancelled')
    assert begin(client,job).json()['send'] is False
    with studio.database() as db:assert db.execute('SELECT state FROM studio_sms_messages WHERE id=?',(job['message_id'],)).fetchone()[0]=='skipped'
    drain()
    cancelled=claim(client);assert cancelled and 'cancelled' in cancelled['content']
    assert begin(client,cancelled).json()['send'] is True
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_sms_jobs').fetchone()[0]==2
        assert db.execute("SELECT count(*) FROM studio_sms_messages WHERE source='notification'").fetchone()[0]==2


def test_wechat_grants_bound_to_account_and_one_time_nonce(setup,monkeypatch):
    client,_,_=setup;proof=setup_wechat()
    session=client.post('/studio-api/auth/notifications/wechat/session',headers=proof).json()
    assert len(session['templates'])==3
    data={'nonce':session['nonce'],'results':{t['template_id']:'accept' for t in session['templates']}}
    client.headers['Authorization']='Bearer qa-other'
    assert client.post('/studio-api/auth/notifications/wechat/session',headers=proof).status_code==403
    assert client.post('/studio-api/auth/notifications/wechat/subscribe',json=data).status_code==409
    client.headers['Authorization']='Bearer qa-owner'
    assert client.post('/studio-api/auth/notifications/wechat/subscribe',json=data).status_code==200
    assert client.post('/studio-api/auth/notifications/wechat/subscribe',json=data).status_code==200
    with studio.database() as db:assert [r[0] for r in db.execute('SELECT grants FROM studio_customer_wechat_grants')]==[1,1,1]
    sent=[];monkeypatch.setattr(owner_wechat,'provider',lambda path,payload:sent.append(payload) or {'errcode':0})
    ident=create(client);status(client,ident,'confirmed');drain()
    assert len(sent)==1 and sent[0]['page']=='pages/studio/reservation?id='+ident
    assert sent[0]['miniprogram_state']=='trial'
    with studio.database() as db:assert db.execute("SELECT grants FROM studio_customer_wechat_grants WHERE kind='confirmed'").fetchone()[0]==0
    drain();assert len(sent)==1


def test_wechat_unknown_send_is_never_retried(setup,monkeypatch):
    client,now,_=setup;proof=setup_wechat()
    data=client.post('/studio-api/auth/notifications/wechat/session',headers=proof).json()
    client.post('/studio-api/auth/notifications/wechat/subscribe',json={'nonce':data['nonce'],'results':{'T'*25+'confirmed':'accept'}})
    count=[]
    def unavailable(*args):count.append(1);raise TimeoutError()
    monkeypatch.setattr(owner_wechat,'provider',unavailable)
    ident=create(client);status(client,ident,'confirmed');drain()
    now[0]+=120;drain()
    assert len(count)==1 and next(r for r in jobs() if r['kind']=='confirmed' and r['channel']=='wechat')['state']=='unknown'


def test_email_claim_does_not_hold_db_and_is_not_double_sent(setup,monkeypatch):
    client,_,_=setup;pref(client,email_enabled=True,email='local@example.test');create(client)
    started=threading.Event();finish=threading.Event();calls=[]
    def slow(job,payload):calls.append(job['id']);started.set();assert finish.wait(5);return ('accepted','','local')
    monkeypatch.setattr(notices,'send_email',slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future=pool.submit(notices.process_one,studio.database)
        try:
            assert started.wait(5)
            assert client.get('/studio-api/auth/notifications').status_code==200
            assert notices.process_one(studio.database) is False
        finally:finish.set()
        future.result(5)
    assert len(calls)==1


def test_reminder_is_skipped_if_completed_or_booking_changed(setup):
    client,now,calls=setup;pref(client,email_enabled=True,email='local@example.test')
    ident=create(client);status(client,ident,'confirmed');drain()
    with studio.database() as db:db.execute("UPDATE studio_reservations SET status='completed' WHERE id=?",(ident,))
    now[0]=datetime(2026,9,11,12,tzinfo=reservations.ZONE).timestamp();drain()
    assert len(calls)==1 and next(r for r in jobs() if r['kind']=='reminder')['state']=='skipped'


def test_site_message_privacy_replay_read_bounds_and_offline_alert(setup):
    client,now,calls=setup;pref(client,email_enabled=True,email='local@example.test')
    ident=create(client);drain();calls.clear()
    request={'content':'Question about arrival','request_id':str(uuid.uuid4()),'reservation_id':ident}
    first=client.post('/studio-api/auth/messages',json=request);assert first.status_code==201
    assert client.post('/studio-api/auth/messages',json=request).json()['id']==first.json()['id']
    assert client.post('/studio-api/auth/messages',json=request|{'content':'Changed'}).status_code==409
    client.headers['Authorization']='Bearer qa-other'
    assert client.get('/studio-api/auth/messages').json()['items']==[]
    assert client.post('/studio-api/auth/messages',json=request|{'request_id':str(uuid.uuid4())}).status_code==404
    client.headers['Authorization']='Bearer qa-owner';host()
    thread=client.get('/studio-api/manage/site-messages').json()['items'][0]
    assert thread['unread']==1
    reply=client.post('/studio-api/manage/site-messages/'+thread['id'],json={'content':'See you then','request_id':str(uuid.uuid4())}).json()
    # Reading the conversation cancels a queued offline alert.
    client.post('/studio-api/auth/messages/read',json={'seq':10**9})
    with studio.database() as db:assert db.execute('SELECT customer_read FROM studio_conversations').fetchone()[0]==reply['seq']
    now[0]+=61;drain();assert not calls
    second=client.post('/studio-api/manage/site-messages/'+thread['id'],json={'content':'One more detail','request_id':str(uuid.uuid4())})
    assert second.status_code==201
    now[0]+=61;drain();assert len(calls)==1 and calls[0][1]['url'].endswith('/messages')
    visible=client.get('/studio-api/auth/messages?after='+str(first.json()['seq'])).json()['items']
    assert [r['body'] for r in visible]==['See you then','One more detail']


def test_owner_site_message_alert_uses_separate_sender(setup):
    client,now,_=setup;bridge('owner_alert')
    with studio.database() as db:db.execute("UPDATE studio_sms_settings SET owner_enabled=1,owner_phone='+14165550100'")
    assert client.post('/studio-api/auth/messages',json={'content':'Hello','request_id':str(uuid.uuid4())}).status_code==201
    now[0]+=61;drain();job=claim(client,'owner_alert')
    assert job and job['recipient']=='+14165550100' and 'manage?view=messages' in job['content']
    assert begin(client,job,'owner_alert').json()['send'] is True


def test_email_transport_identity_idempotency_and_html_escaping(monkeypatch):
    import io
    monkeypatch.setenv('STUDIO_EMAIL_API_KEY','local-test-key')
    monkeypatch.setenv('STUDIO_EMAIL_FROM','PinDou <local@example.test>')
    requests=[]
    def transport(request,**kwargs):
        requests.append(request)
        return io.BytesIO(b'{"id":"local-provider-id"}')
    monkeypatch.setattr(notices,'urlopen',transport)
    job={'id':'repeatable-test','recipient':'local@example.test'}
    payload={'title':'<script>test</script>','body':'<img src=x>','url':'https://pindoupuppy.com/messages','locale':'en'}
    for _ in range(2):assert notices.send_email(job,payload)==('accepted','','local-provider-id')
    assert requests[0].get_header('User-agent')=='PinDouStudio/1.0'
    assert requests[0].get_header('Idempotency-key')==requests[1].get_header('Idempotency-key')=='booking-repeatable-test'
    body=json.loads(requests[0].data);assert '<script>' not in body['html'] and '&lt;img' in body['html']


def test_provided_contacts_are_automatic_but_explicit_opt_out_is_kept(setup):
    client,_,_=setup
    with studio.database() as db:
        db.execute("INSERT INTO studio_booking_profiles(owner_id,name,contact_method,contact,version,updated_at,source_reservation_id) VALUES('qa-owner','Local','phone','+14165550123',1,'2026-09-10','')")
    initial=client.get('/studio-api/auth/notifications').json()
    assert initial['email_enabled'] and initial['sms_enabled']
    assert initial['email']=='qa-owner@example.test' and initial['phone']=='+14165550123'
    pref(client,sms_enabled=False,email_enabled=False)
    again=client.get('/studio-api/auth/notifications').json()
    assert not again['sms_enabled'] and not again['email_enabled']
    create(client)
    assert not jobs()


def test_first_booking_automatically_captures_registered_email_and_phone(setup):
    client,_,_=setup
    response=client.post('/studio-api/reservations',headers={'Idempotency-Key':str(uuid.uuid4())},json={
      'booking':{'date':'2026-09-11','start':'14:00','end':'16:00','plan':'hourly','guests':1},
      'name':'Local first booking','contact_method':'phone','contact':'+14165550123','consent':True})
    assert response.status_code==201,response.text
    assert {(r['channel'],r['recipient']) for r in jobs()}=={('email','qa-owner@example.test'),('sms','+14165550123')}
