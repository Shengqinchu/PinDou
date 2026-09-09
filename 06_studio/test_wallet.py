"""HTTP-level wallet/attendance invariants; all accounts, bookings and DBs isolated."""
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
import app as studio
import reservations
import wallet
from test_reservations import client, admin, submit


def get(client, owner='qa-owner'):
    return client.get('/studio-api/manage/members/'+owner).json()


def prepare(client):
    client.get('/studio-api/auth/me')
    admin()


def post(client, *, key=None, owner='qa-owner', **changes):
    payload={'version':get(client,owner)['account']['version'],'kind':'topup','minutes_delta':600,
             'points_delta':0,'note':'Verified at studio','effective_date':'2026-09-07'} | changes
    return client.post('/studio-api/manage/members/'+owner+'/transactions',json=payload,
                       headers={'Idempotency-Key':key or str(uuid.uuid4())})


def complete(client, ref, version=1):
    assert client.patch('/studio-api/manage/reservations/'+ref,json={'version':version,'status':'confirmed'}).status_code==200
    return client.patch('/studio-api/manage/reservations/'+ref,json={'version':version+1,'status':'completed',
                       'actual_minutes':165,'actual_guests':2,'public_note':'165 minutes per guest','staff_note':'Private bookkeeping'})


def test_authorization_identity_and_private_notes(client):
    assert client.get('/studio-api/manage/members').status_code==401
    assert client.post('/studio-api/manage/members/qa-owner/transactions',json={}).status_code==401
    prepare(client)
    note={'version':1,'staff_note':'Private host information'}
    assert client.patch('/studio-api/manage/members/qa-owner',json=note).status_code==200
    assert post(client,kind='gift',minutes_delta=120,points_delta=188).status_code==200
    personal=client.get('/studio-api/auth/wallet').json()
    assert personal['account']['points']==188
    assert personal['account']['redeemable_cad']==1
    assert 'staff_note' not in personal['account']
    assert 'actor' not in personal['entries'][0]
    client.headers['Authorization']='Bearer qa-other'
    assert client.get('/studio-api/auth/wallet').json()['account']['points']==0
    client.headers.pop('Authorization')
    assert client.get('/studio-api/auth/wallet').status_code==401


def test_opening_topup_gift_usage_redemption_and_remainder(client):
    prepare(client)
    assert post(client,kind='opening',minutes_delta=180,points_delta=0).status_code==200
    assert post(client,kind='opening').status_code==409
    assert post(client).status_code==200
    assert post(client,kind='usage',minutes_delta=-300).status_code==200
    assert post(client,kind='gift',minutes_delta=0,points_delta=188).status_code==200
    assert post(client,kind='redeem',minutes_delta=0,points_delta=-100,bill_cents=888).status_code==200
    state=get(client)
    assert state['account']['minutes']==480 and state['account']['points']==88
    assert state['account']['redeemable_cad']==0
    assert state['total']==5
    assert client.get('/studio-api/manage/members/qa-owner?category=time').json()['total']==3
    assert client.get('/studio-api/manage/members/qa-owner?category=points').json()['total']==2
    assert sum(row['minutes_delta'] for row in state['entries'])==480


@pytest.mark.parametrize('changes',[
    {'kind':'redeem','minutes_delta':0,'points_delta':-88,'bill_cents':1000},
    {'kind':'redeem','minutes_delta':0,'points_delta':-200,'bill_cents':199},
    {'kind':'redeem','minutes_delta':0,'points_delta':-100},
    {'minutes_delta':1.5}, {'points_delta':True}, {'note':''},
    {'kind':'usage','minutes_delta':100}, {'kind':'gift','points_delta':-1},
    {'effective_date':'2099-09-08'}, {'minutes_delta':0},
])
def test_reject_invalid_amounts_without_write(client,changes):
    prepare(client)
    assert post(client,**changes).status_code==422
    assert get(client)['total']==0


def test_atomic_insufficient_funds_version_and_duplicate_retries(client):
    prepare(client)
    key=str(uuid.uuid4())
    assert post(client,key=key,version=1).status_code==200
    assert post(client,key=key,version=1).status_code==200
    assert get(client)['total']==1
    assert post(client,key=key,version=1,minutes_delta=601).status_code==409
    assert post(client,version=1).status_code==409
    assert post(client,kind='usage',minutes_delta=-601).status_code==409
    assert get(client)['account']['minutes']==600
    version=get(client)['account']['version']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:post(client,version=version,kind='usage',minutes_delta=-400).status_code,range(2)))
    assert sorted(results)==[200,409]
    assert get(client)['account']['minutes']==200


def test_reversals_are_append_only_and_cannot_double_refund(client):
    prepare(client)
    original=post(client).json()['entries'][0]['id']
    key=str(uuid.uuid4()); path=f'/studio-api/manage/members/qa-owner/entries/{original}/reverse'
    payload={'version':2,'note':'Correct duplicate cash entry'}
    first=client.post(path,json=payload,headers={'Idempotency-Key':key})
    assert first.status_code==200 and first.json()['account']['minutes']==0
    assert client.post(path,json=payload,headers={'Idempotency-Key':key}).status_code==200
    assert client.post(path,json={'version':3,'note':'again'},headers={'Idempotency-Key':str(uuid.uuid4())}).status_code==409
    assert get(client)['total']==2
    with studio.database() as db:
        with pytest.raises(sqlite3.IntegrityError): db.execute('DELETE FROM studio_wallet_ledger WHERE id=?',(original,))
        with pytest.raises(sqlite3.IntegrityError): db.execute('UPDATE studio_wallet_ledger SET minutes_delta=0 WHERE id=?',(original,))


def test_attendance_reward_once_updates_client_and_never_deducts_time(client,monkeypatch):
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-08T18:00:00-04:00')
    prepare(client)
    post(client)
    ref=submit(client).json()['id']
    assert complete(client,ref).status_code==200
    state=client.get('/studio-api/auth/wallet').json()
    assert state['account']['points']==100 and state['account']['minutes']==600
    receipt=client.get('/studio-api/reservations/'+ref).json()
    assert receipt['booked_minutes']==120 and receipt['actual_minutes']==165 and receipt['actual_guests']==2
    assert receipt['public_note']=='165 minutes per guest' and 'staff_note' not in receipt
    assert client.patch('/studio-api/manage/reservations/'+ref,json={'version':3,'status':'completed','actual_minutes':180,'actual_guests':2}).status_code==200
    assert get(client)['account']['points']==100
    # Ledger remains distinct from actual attendance; deliberate host debit only.
    assert post(client,kind='usage',minutes_delta=-360,reservation_id=ref).status_code==200
    assert get(client)['account']['minutes']==240
    assert client.patch('/studio-api/manage/reservations/'+ref,json={'version':4,'status':'cancelled'}).status_code==409


def test_future_rewards_fail_atomically_and_no_defaults_backfill(client,monkeypatch):
    prepare(client)
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-07T18:00:00-04:00')
    ref=submit(client).json()['id']
    assert complete(client,ref).status_code==422
    assert client.get('/studio-api/reservations/'+ref).json()['status']=='confirmed'
    assert get(client)['total']==0
    studio.initialize();studio.initialize()
    assert get(client)['total']==0


def test_delete_restore_and_preserve_ledgers(client,monkeypatch):
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-08T18:00:00-04:00')
    prepare(client)
    ref=submit(client).json()['id']
    path='/studio-api/manage/reservations/'+ref
    assert client.patch(path,json={'version':1,'status':'confirmed'}).status_code==200
    assert client.request('DELETE',path,json={'version':2,'reason':'mistake'}).status_code==409
    assert client.patch(path,json={'version':2,'status':'completed','actual_minutes':120,'actual_guests':2}).status_code==200
    assert client.request('DELETE',path,json={'version':3,'reason':'duplicate display'}).status_code==200
    assert client.get('/studio-api/auth/reservations').json()['items']==[]
    assert client.get('/studio-api/reservations/'+ref).status_code==404
    assert client.get('/studio-api/manage/reservations?deleted=true').json()['total']==1
    assert get(client)['account']['points']==100
    assert client.post(path+'/restore',json={'version':4,'reason':'restore record'}).status_code==200
    assert client.get('/studio-api/auth/reservations').json()['items'][0]['actual_minutes']==120
    assert get(client)['account']['points']==100


def test_reservation_link_must_match_owner_and_completed_visit(client):
    prepare(client)
    ref=submit(client).json()['id']
    assert post(client,kind='usage',minutes_delta=-60,reservation_id=ref).status_code==409
    client.headers['Authorization']='Bearer qa-other'
    client.get('/studio-api/auth/me')
    assert post(client,owner='qa-other',reservation_id=ref).status_code==422


def test_ledger_pagination_preserves_old_history(client):
    prepare(client)
    for _ in range(32): assert post(client,kind='gift',minutes_delta=1).status_code==200
    first=client.get('/studio-api/auth/wallet').json()
    second=client.get('/studio-api/auth/wallet?page=2').json()
    assert first['total']==32 and len(first['entries'])==30 and len(second['entries'])==2
    assert {row['id'] for row in first['entries']}.isdisjoint(row['id'] for row in second['entries'])
