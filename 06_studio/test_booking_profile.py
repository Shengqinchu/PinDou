import json
import uuid
import booking_profile
import app as studio
from test_reservations import client, body, submit, admin


def own(client):
    response=client.get('/studio-api/auth/booking-profile')
    assert response.status_code==200,response.text
    return response.json()


def details(name='Preferred name',contact='my-wechat',method='wechat',version=0):
    return dict(name=name,contact=contact,contact_method=method,version=version)


def test_first_submission_saves_before_attendance_and_retry_is_stable(client):
    assert own(client)['version']==0
    data=body()|{'name':'Preferred name','contact':'my-wechat','contact_profile_version':0}
    key=str(uuid.uuid4());receipt=submit(client,data,key)
    assert receipt.status_code==201,receipt.text
    profile=own(client)
    assert profile['version']==1 and profile['complete'] and profile['name']=='Preferred name'
    assert profile['source_reservation_id']==receipt.json()['id'] and receipt.json()['status']=='pending'
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is True
    updated=client.put('/studio-api/auth/booking-profile',json=details(contact='new-wechat',version=1))
    assert updated.status_code==200
    assert submit(client,data,key).json()==receipt.json()
    assert own(client)['version']==2 and own(client)['contact']=='new-wechat'
    with studio.database() as db:
        snapshot=json.loads(db.execute('SELECT payload FROM studio_reservations WHERE id=?',(receipt.json()['id'],)).fetchone()[0])
        assert snapshot['contact']=='my-wechat'
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==1


def test_failed_booking_does_not_save_profile_and_stale_submission_is_atomic(client):
    invalid=body(start='21:00',end='23:00')|{'contact_profile_version':0}
    assert submit(client,invalid).status_code==422 and own(client)['version']==0
    assert client.put('/studio-api/auth/booking-profile',json=details()).status_code==200
    stale=submit(client,body()|{'contact_profile_version':0})
    assert stale.status_code==409 and stale.json()['detail']=='booking_profile_changed'
    assert own(client)['contact']=='my-wechat'
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM submission_limits WHERE client_hash LIKE 'reservation:%'").fetchone()[0]==0


def test_reuse_is_account_scoped_and_explicit_edit_updates_future_defaults(client):
    assert submit(client,body()|{'contact_profile_version':0}).status_code==201
    reused=submit(client,body()|{'name':'','contact':'','contact_profile_version':1})
    assert reused.status_code==201 and reused.json()['name']=='Reservation QA'
    changed=body()|{'name':'Updated name','contact_method':'phone','contact':'+1 416 555 0123','contact_profile_version':1}
    assert submit(client,changed).status_code==201
    assert own(client)['name']=='Updated name' and own(client)['version']==2
    client.headers['Authorization']='Bearer qa-other'
    assert not own(client)['complete']
    assert submit(client,body()|{'name':'','contact':''}).status_code==422
    assert client.get('/studio-api/auth/booking-profile?owner_id=qa-owner').json()['owner_id']=='qa-other'
    client.headers.pop('Authorization')
    assert client.get('/studio-api/auth/booking-profile').status_code==401
    assert client.put('/studio-api/auth/booking-profile',json=details()).status_code==401


def test_profile_edits_do_not_change_identity_wallet_or_old_bookings(client):
    assert submit(client).status_code==201
    before=client.get('/studio-api/auth/wallet').json()['account']
    admin();member=client.get('/studio-api/manage/members/qa-owner').json()
    result=client.put('/studio-api/manage/members/qa-owner/booking-profile',json=details(contact='host-corrected',version=1))
    assert result.status_code==200,result.text
    assert own(client)['contact']=='host-corrected'
    matches=client.get('/studio-api/manage/members?search=host-corrected').json()['items']
    assert [m['owner_id'] for m in matches]==['qa-owner']
    assert matches[0]['booking_profile']['name']=='Preferred name'
    after=client.get('/studio-api/auth/wallet').json()['account']
    assert before==after
    assert client.put('/studio-api/auth/booking-profile',json=details(contact='stale-edit',version=1)).status_code==409
    # A lost profile response may be retried when the exact value is already current.
    assert client.put('/studio-api/auth/booking-profile',json=details(contact='host-corrected',version=1)).status_code==200
    studio.app.dependency_overrides.clear()
    assert client.put('/studio-api/manage/members/qa-owner/booking-profile',json=details(version=2)).status_code in (401,403)


def test_validation_and_clear_preserves_explicit_empty_profile(client):
    for bad in [details(contact='bad',method='email'),details(contact='123',method='phone'),details(name=''),details()|{'owner_id':'qa-other'},details(version=True)]:
        assert client.put('/studio-api/auth/booking-profile',json=bad).status_code==422
    assert submit(client).status_code==201
    cleared=client.put('/studio-api/auth/booking-profile',json=details(name='',contact='',version=1))
    assert cleared.status_code==200 and cleared.json()['complete'] is False
    booking_profile.initialize(studio.database);booking_profile.initialize(studio.database)
    assert own(client)['version']==2 and own(client)['name']==''


def test_backfill_uses_latest_explicit_owned_booking_without_rewriting_it(client):
    one=submit(client,body()|{'name':'Earlier','contact':'earlier-contact'}).json()
    two=submit(client,body()|{'name':'Later','contact':'later-contact'}).json()
    with studio.database() as db:
        db.execute('DELETE FROM studio_booking_profiles')
        db.execute("UPDATE studio_reservations SET created_at='2026-09-07T09:01:00' WHERE id=?",(two['id'],))
        original=db.execute('SELECT id,payload FROM studio_reservations ORDER BY id').fetchall()
    booking_profile.initialize(studio.database)
    profile=own(client)
    assert profile['name']=='Later' and profile['source_reservation_id']==two['id'] and profile['version']==1
    booking_profile.initialize(studio.database)
    assert own(client)==profile
    with studio.database() as db:
        assert db.execute('SELECT id,payload FROM studio_reservations ORDER BY id').fetchall()==original
    client.headers['Authorization']='Bearer qa-other'
    assert not own(client)['complete']


def test_legacy_submission_can_create_but_cannot_overwrite_saved_contact(client):
    assert submit(client,body()|{'name':'Initial','contact':'initial-contact'}).status_code==201
    assert own(client)['version']==1
    assert submit(client,body()|{'name':'Old tab','contact':'outdated-contact'}).status_code==201
    assert own(client)['name']=='Initial' and own(client)['version']==1
