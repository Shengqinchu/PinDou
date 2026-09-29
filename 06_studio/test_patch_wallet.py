"""Patch attendance earns once; Patch charges are never point-redeemable."""
import json
import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

import app as studio
import wallet
import reservations
from test_reservations import client, admin, body, submit
from test_wallet import prepare, post, get
from test_admin_reservations import create, payload


def attend(client, ref):
    assert client.patch('/studio-api/manage/reservations/'+ref,
                        json={'version':1,'status':'confirmed'}).status_code == 200
    result = client.patch('/studio-api/manage/reservations/'+ref,
                          json={'version':2,'status':'completed','actual_minutes':30,'actual_guests':2})
    assert result.status_code == 200, result.text


def patch_booking(client, monkeypatch):
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-08T18:00:00-04:00')
    prepare(client)
    return submit(client,body('2026-09-08','11:00','12:00','patch')).json()['id']


@pytest.mark.parametrize('guests',[1,2,4])
def test_patch_self_booking_awards_166_once_after_attendance(client,monkeypatch,guests):
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-08T18:00:00-04:00');prepare(client)
    data=body('2026-09-08','11:00','12:00','patch');data['booking']['guests']=guests
    ref=submit(client,data).json()['id']
    assert get(client)['account']['points']==166
    attend(client,ref)
    assert client.patch('/studio-api/manage/reservations/'+ref,
                        json={'version':3,'status':'completed','actual_minutes':45,'actual_guests':guests}).status_code==200
    result=client.get('/studio-api/auth/wallet').json()
    assert result['account']['points']==332
    rewards=[e for e in result['entries'] if e['kind']=='visit_reward']
    assert len(rewards)==1 and rewards[0]['points_delta']==166 and rewards[0]['reservation_id']==ref


@pytest.mark.parametrize('use',['visit','shop'])
def test_patch_redemption_rejected_atomically_for_any_declared_use(client,monkeypatch,use):
    ref=patch_booking(client,monkeypatch);attend(client,ref)
    before=get(client)
    for _ in range(2):
        result=post(client,kind='redeem',minutes_delta=0,points_delta=-100,bill_cents=600,
                    reservation_id=ref,redemption_use=use)
        assert result.status_code==422 and result.json()['detail']=='wallet_patch_redemption_forbidden'
        assert get(client)==before
    with studio.database() as db:
        with pytest.raises(HTTPException,match='wallet_patch_redemption_forbidden'):
            wallet.append(db,'qa-owner',kind='redeem',minutes=0,points=-100,note='Patch bill',
                          actor='test-owner',key=str(uuid.uuid4()),digest='fixture',reservation_id=ref,
                          bill_cents=600,redemption_use=use,no_promotion=True)
    assert get(client)==before


def test_patch_reward_can_be_spent_on_beads_and_shop(client,monkeypatch):
    ref=patch_booking(client,monkeypatch);attend(client,ref)
    beads=submit(client,body()).json()['id'];attend(client,beads)
    assert post(client,kind='redeem',minutes_delta=0,points_delta=-100,bill_cents=888,
                reservation_id=beads,redemption_use='visit').status_code==200
    assert post(client,kind='redeem',minutes_delta=0,points_delta=-100,bill_cents=888,
                redemption_use='shop').status_code==200
    assert get(client)['account']['points']==298


def test_patch_cancelled_or_admin_created_does_not_mint_reward(client,monkeypatch):
    ref=patch_booking(client,monkeypatch)
    assert client.patch('/studio-api/manage/reservations/'+ref,
                        json={'version':1,'status':'cancelled'}).status_code==200
    data=payload();data['booking']=body('2026-09-08','11:00','12:00','patch')['booking']
    result=create(client,data);assert result.status_code==201,result.text
    ref=result.json()['id']
    assert client.patch('/studio-api/manage/reservations/'+ref,
                        json={'version':1,'status':'confirmed'}).status_code==200
    monkeypatch.setattr(reservations,'now_local',lambda:datetime(2026,9,8,18,0,tzinfo=reservations.ZONE))
    completed=client.patch('/studio-api/manage/reservations/'+ref,
                           json={'version':2,'status':'completed','actual_minutes':30,'actual_guests':2})
    assert completed.status_code==200,completed.text
    assert get(client)['account']['points']==166
    assert not [e for e in get(client)['entries'] if e['kind']=='visit_reward']


def test_previous_successful_redemption_retry_and_reversal_stay_valid(client,monkeypatch):
    ref=patch_booking(client,monkeypatch);attend(client,ref)
    # Simulate a completed pre-policy transaction without changing its ledger.
    with studio.database() as db:
        data=json.loads(db.execute('SELECT payload FROM studio_reservations WHERE id=?',(ref,)).fetchone()[0])
        data['booking']['plan']='hourly';db.execute('UPDATE studio_reservations SET payload=? WHERE id=?',(json.dumps(data),ref))
    key=str(uuid.uuid4());version=get(client)['account']['version']
    args=dict(kind='redeem',minutes_delta=0,points_delta=-100,bill_cents=600,reservation_id=ref,version=version,key=key)
    first=post(client,**args);assert first.status_code==200
    entry=first.json()['entries'][0]['id']
    with studio.database() as db:
        data['booking']['plan']='patch';db.execute('UPDATE studio_reservations SET payload=? WHERE id=?',(json.dumps(data),ref))
    assert post(client,**args).status_code==200
    assert get(client)['account']['points']==232
    result=client.post(f'/studio-api/manage/members/qa-owner/entries/{entry}/reverse',
                       json={'version':get(client)['account']['version'],'note':'Undo old redemption'},
                       headers={'Idempotency-Key':str(uuid.uuid4())})
    assert result.status_code==200 and result.json()['account']['points']==332
