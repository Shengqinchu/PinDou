"""Native wire format against the real reservation routes, isolated DB/worker."""
import uuid
import app as studio
from test_owner_notifications import setup, configure, jobs


def native_body(version=0):
    return dict(booking=dict(date='2026-09-11', start='14:00', end='16:00', plan='hourly', guests=2),
                name='Native booking QA', contact_method='wechat', contact='local-ui-only',
                contact_profile_version=version, notes='', locale='zh', website='')


def calendar_cookie(client):
    client.cookies.clear()
    result=client.get('/studio-api/reservation-calendar?guests=2')
    assert result.status_code==200
    value=client.cookies.get('puppy_reservation_session')
    client.cookies.clear()  # wx.request sends its retained cookie explicitly.
    return 'puppy_reservation_session='+value


def test_native_submission_replay_profile_host_queue_and_cancellation(setup):
    client, sent, _path=setup
    assert configure(client).status_code==200
    context=client.get('/studio-api/auth/reservation-context').json()
    assert context['profile']['owner_id']=='qa-owner'
    cookie=calendar_cookie(client)
    body=native_body(context['profile']['version']);key=str(uuid.uuid4())
    assert client.post('/studio-api/reservations',json=body,headers={'Idempotency-Key':key}).json()['detail']=='reservation_session_missing'
    headers={'Idempotency-Key':key,'Cookie':cookie}
    response=client.post('/studio-api/reservations',json=body,headers=headers)
    assert response.status_code==201,response.text
    receipt=response.json();ident=receipt['id']
    assert receipt['status']=='pending' and receipt['booking']['guests']==2
    assert client.get('/studio-api/auth/reservations').json()['items'][0]['id']==ident
    assert client.get('/studio-api/auth/booking-profile').json()['contact']=='local-ui-only'
    assert client.get('/studio-api/manage/reservations').json()['items'][0]['id']==ident
    assert len(jobs())==1 and not sent
    # After an app restart, a fresh visitor cookie plus the same account and
    # exact idempotency key must recover the receipt, even after profile changes.
    refreshed_cookie=calendar_cookie(client)
    replay=client.post('/studio-api/reservations',json=body,headers={'Idempotency-Key':key,'Cookie':refreshed_cookie})
    assert replay.json()==receipt and len(jobs())==1
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM commerce_orders').fetchone()[0]==0
    assert client.patch('/studio-api/manage/reservations/'+ident,json={'status':'confirmed','version':1}).status_code==200
    assert client.get('/studio-api/reservations/'+ident).json()['status']=='confirmed'
    policy=client.get('/studio-api/reservations/'+ident+'/cancellation').json()
    assert policy['eligible'] and policy['limit']==3 and policy['used']==0
    canceled=client.post('/studio-api/reservations/'+ident+'/cancel',json={'version':policy['version']})
    assert canceled.status_code==200 and canceled.json()['policy']['used']==1
    assert client.post('/studio-api/reservations/'+ident+'/cancel',json={'version':policy['version']}).json()['policy']['used']==1
    client.headers['Authorization']='Bearer qa-other'
    assert client.get('/studio-api/reservations/'+ident).status_code==404
    assert client.get('/studio-api/reservations/'+ident+'/cancellation').status_code==404
    assert client.get('/studio-api/auth/reservations').json()['items']==[]
    assert not sent
