import json,uuid
import app as studio
import customer_auth
from test_reservations import client,body,submit


def completed(owner='qa-owner',day='2026-09-05'):
    data=body(day);data.update(name='Known guest',contact_method='phone',contact='+1 416 555 0123')
    with studio.database() as db:
        db.execute("""INSERT INTO studio_reservations(id,created_at,updated_at,status,payload,visitor_hash,idempotency_key,payload_hash,owner_id,actual_minutes,actual_guests)
         VALUES(?,?,?,'completed',?,?,?,?,?,120,2)""",('VIS-PAST-'+uuid.uuid4().hex,'2026-09-05T12:00:00','2026-09-05T16:00:00',json.dumps(data),'local-fixture',str(uuid.uuid4()),'fixture',owner))


def empty():return body()|{'name':'','contact':''}


def test_new_accounts_need_contact_and_submission_saves_profile(client):
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is False
    assert submit(client,empty()).json()['detail']=='reservation_contact_required'
    assert submit(client).status_code==201
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is True
    assert submit(client,empty()|{'returning_customer':True}).status_code==422
    client.headers.pop('Authorization')
    assert client.get('/studio-api/auth/reservation-context').status_code==401
    assert submit(client,empty()).status_code==401


def test_returning_guests_can_omit_both_fields_using_own_history(client):
    completed();completed('qa-other')
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is True
    response=submit(client,empty());assert response.status_code==201,response.text
    assert response.json()['name']=='Known guest'
    with studio.database() as db:
        row=db.execute('SELECT owner_id,payload FROM studio_reservations WHERE id=?',(response.json()['id'],)).fetchone()
        data=json.loads(row['payload']);assert row['owner_id']=='qa-owner'
        assert data['contact']=='+1 416 555 0123' and data['contact_method']=='phone' and data['returning_customer'] is True
    changed=submit(client,empty()|{'name':'My new name'})
    assert changed.status_code==201 and changed.json()['name']=='My new name'
    assert submit(client,empty()|{'contact_method':'email','contact':'invalid'}).status_code==422


def test_another_account_or_future_completed_record_is_not_attendance(client):
    completed('qa-other');completed(day='2026-09-12')
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is False
    assert submit(client,empty()).status_code==422


def test_blank_retry_preserves_original_receipt_after_history_changes(client):
    completed();key=str(uuid.uuid4());one=submit(client,empty(),key).json()
    # Simulate another later reservation under this account; the saved request
    # still resolves to its original contact snapshot, never another booking.
    assert submit(client,body()|{'name':'Updated guest','contact':'new-contact'}).status_code==201
    two=submit(client,empty(),key);assert two.status_code==201 and two.json()==one
    client.headers['Authorization']='Bearer qa-other'
    assert submit(client,empty(),key).status_code==409


def usage(owner,kind='usage',minutes=-60,reverses=None):
    with studio.database() as db:
        return db.execute("""INSERT INTO studio_wallet_ledger(owner_id,created_at,effective_date,actor,kind,minutes_delta,points_delta,minutes_balance,points_balance,note,idempotency_key,request_hash,reverses_id)
         VALUES(?,'2026-09-05T12:00:00','2026-09-05','test-owner',?,?,0,0,166,'',?,'fixture',?)""",(owner,kind,minutes,str(uuid.uuid4()),reverses)).lastrowid


def test_manual_time_usage_qualifies_but_credit_gifts_and_reversals_do_not(client):
    usage('qa-owner','gift',60)
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is False
    used=usage('qa-owner')
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is True
    response=submit(client,empty());assert response.status_code==201,response.text
    with studio.database() as db:
        data=json.loads(db.execute('SELECT payload FROM studio_reservations WHERE id=?',(response.json()['id'],)).fetchone()[0])
        assert data['contact_method']=='email' and data['contact']=='qa-owner@example.test'
    usage('qa-owner','reversal',60,used)
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is False


def test_email_less_wechat_regular_can_omit_contact_without_fabricating_it(client,monkeypatch):
    ident='wechat_authing_'+'a'*64
    monkeypatch.setattr(customer_auth,'upstream',lambda *a,**kw:{'user_id':ident,'email':None,'nickname':'Known WeChat guest'})
    usage(ident)
    assert client.get('/studio-api/auth/reservation-context').json()['can_omit_details'] is True
    result=submit(client,empty());assert result.status_code==201,result.text
    assert result.json()['name']=='Known WeChat guest'
    with studio.database() as db:
        payload=json.loads(db.execute('SELECT payload FROM studio_reservations WHERE id=?',(result.json()['id'],)).fetchone()[0])
        assert payload['contact']=='' and payload['contact_method']=='other' and payload['returning_customer'] is True
