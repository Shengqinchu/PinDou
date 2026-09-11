import json
import time
import uuid

import pytest
import app as studio
import studio_finance as finance
import studio_staff
import authing_login
import miniapp_login
import finance_fx
from datetime import date
from test_owner_notifications import setup, host, create


def new(**changes):
    return {'request_id':str(uuid.uuid4()),'kind':'expense','category':'expense','occurred_on':'2026-09-11',
            'items':['Beads','Storage boxes'],'amount_cents':2580,**changes}


def test_authentication_and_minor_units(setup):
    client,_,_=setup
    assert client.get('/studio-api/manage/finance').status_code==401
    host()
    assert client.post('/studio-api/manage/finance',json=new(amount_cents=25.80)).status_code==422
    assert client.post('/studio-api/manage/finance',json=new(amount_cents=-1)).status_code==422
    assert client.post('/studio-api/manage/finance',json=new(amount_cents=None)).status_code==422
    assert client.post('/studio-api/manage/finance',json=new(items=[''])).status_code==422


def test_income_expenses_filters_and_retry(setup):
    client,_,_=setup;host()
    payload=new();response=client.post('/studio-api/manage/finance',json=payload)
    assert response.status_code==201,response.text
    assert client.post('/studio-api/manage/finance',json=payload).json()['id']==response.json()['id']
    assert client.post('/studio-api/manage/finance',json={**payload,'amount_cents':999}).status_code==409
    income=client.post('/studio-api/manage/finance',json=new(kind='income',category='finished',amount_cents=5990,customer_name='Local',items=['Cat keyring'],payment_method='cash'))
    assert income.status_code==201,income.text
    page=client.get('/studio-api/manage/finance?start=2026-09-01&end=2026-09-30').json()
    assert page['total']==2 and page['summary']['income_cents']==5990 and page['summary']['expense_cents']==2580
    assert page['summary']['balance_cents']==3410
    assert client.get('/studio-api/manage/finance?start=2026-09-01&end=2026-09-30&kind=income&category=finished&search=Local').json()['total']==1


def test_completion_imports_once_and_never_overwrites_manual_edits(setup):
    client,_,_=setup;host()
    r=create(client);assert r.status_code==201,r.text
    ident=r.json()['id']
    assert client.patch('/studio-api/manage/reservations/'+ident,json={'version':1,'status':'confirmed','staff_note':''}).status_code==200
    assert client.patch('/studio-api/manage/reservations/'+ident,json={'version':2,'status':'completed','staff_note':''}).status_code==200
    with studio.database() as db:
        row=db.execute('SELECT * FROM studio_reservations WHERE id=?',(ident,)).fetchone()
        finance.from_completed(db,row,'local-qa')
        finance.from_completed(db,row,'local-qa')
        entries=db.execute('SELECT * FROM studio_finance_entries').fetchall()
        assert len(entries)==1 and entries[0]['amount_cents'] is None
        entry=finance.public(entries[0]);original_payload=row['payload']
    edit={k:entry[k] for k in finance.EditEntry.model_fields}
    edit.update(customer_name='Changed name',occurred_on='2026-09-01',items=['Custom session'],amount_cents=4000,payment_method='e-transfer')
    saved=client.put('/studio-api/manage/finance/'+entry['id'],json=edit)
    assert saved.status_code==200,saved.text
    assert client.put('/studio-api/manage/finance/'+entry['id'],json=edit).status_code==409
    finance.initialize(studio.database)
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_finance_entries').fetchone()[0]==1
        assert db.execute('SELECT payload FROM studio_reservations WHERE id=?',(ident,)).fetchone()[0]==original_payload
    detail=client.get('/studio-api/manage/finance/'+entry['id']).json()
    assert detail['entry']['customer_name']=='Changed name' and detail['entry']['amount_cents']==4000
    assert len(detail['history'])==2 and detail['history'][1]['snapshot']['amount_cents'] is None
    assert client.request('DELETE','/studio-api/manage/finance/'+entry['id'],json={'version':2,'reason':'Duplicate cash record'}).status_code==200
    finance.initialize(studio.database)
    assert client.get('/studio-api/manage/finance?start=2020-01-01&end=2029-01-01').json()['total']==0


def test_new_category_and_null_draft_excluded_from_totals(setup):
    client,_,_=setup;host()
    response=client.post('/studio-api/manage/finance/categories',json={'zh':'Classes','en':'Classes'})
    assert response.status_code==201,response.text
    category=response.json()['id']
    assert client.post('/studio-api/manage/finance',json=new(kind='income',category=category,amount_cents=0)).status_code==201
    assert client.post('/studio-api/manage/finance',json=new(kind='income',category='missing')).status_code==422
    assert client.get('/studio-api/manage/finance?start=2026-09-12&end=2026-09-11').status_code==422


def test_native_admin_requires_explicit_role_and_revocation_is_immediate(setup,monkeypatch):
    client,_,_=setup
    appid='wx'+'b'*16;openid='owner-openid-123456789';token='t'*43;owner='wechat_authing_'+'b'*64
    monkeypatch.setattr(miniapp_login,'config',lambda:type('Config',(),{'app_id':appid})())
    with studio.database() as db:
        db.execute('INSERT INTO studio_miniapp_tickets VALUES(?,?,?,?)',(authing_login.digest(token),appid,openid,int(time.time())+600))
        db.execute('INSERT INTO studio_miniapp_identities VALUES(?,?,?,?)',(appid,openid,owner,int(time.time())))
    headers={'X-Pindou-Miniapp':token}
    assert client.get('/studio-api/manage/session',headers=headers).status_code==403
    assert client.get('/studio-api/manage/finance',headers={'X-Pindou-Miniapp':'x'*43}).status_code==401
    with studio.database() as db:
        db.execute('INSERT INTO studio_staff_accounts VALUES(?,\'admin\',1,?,?,?,?)',(owner,'Local',time.time(),time.time(),'test'))
    assert client.get('/studio-api/manage/session',headers=headers).json()['admin'] is True
    assert client.get('/studio-api/manage/finance',headers=headers).status_code==200
    with studio.database() as db:db.execute('UPDATE studio_staff_accounts SET enabled=0 WHERE user_id=?',(owner,))
    assert client.get('/studio-api/manage/finance',headers=headers).status_code==403


def test_shared_customer_role_is_studio_only_and_mobile_update_aliases(setup):
    client,_,_=setup
    assert client.get('/studio-api/auth/me').json()['user']['is_admin'] is False
    assert client.get('/studio-api/manage/session').status_code==401

    with studio.database() as db:
        db.execute("INSERT INTO studio_staff_accounts VALUES('qa-owner','admin',1,'Local',?,?,?)",(time.time(),time.time(),'test'))
    assert client.get('/studio-api/auth/me').json()['user']['is_admin'] is True
    assert client.get('/studio-api/manage/session').json()['actor']=='studio:qa-owner'
    booking=create(client).json()
    result=client.post('/studio-api/manage/reservations/'+booking['id']+'/update',json={'version':1,'status':'confirmed','staff_note':'Mobile update'})
    assert result.status_code==200,result.text
    profile=client.get('/studio-api/manage/members/qa-owner').json()
    note=client.post('/studio-api/manage/members/qa-owner/update',json={'version':profile['account']['version'],'staff_note':'New mobile note'})
    assert note.status_code==200 and note.json()['account']['staff_note']=='New mobile note'
    with studio.database() as db:db.execute("UPDATE studio_staff_accounts SET enabled=0 WHERE user_id='qa-owner'")
    assert client.get('/studio-api/manage/session').status_code==401


def test_rmb_income_expense_conversion_and_method_inference(setup,monkeypatch):
    client,_,_=setup;host()
    monkeypatch.setattr(finance_fx,'fetch_quote',lambda day:{'rate':'0.2067','rate_date':'2026-09-11','source':'Bank of Canada'})
    income=client.post('/studio-api/manage/finance',json=new(kind='income',category='experience',payment_method='WeChat / Alipay',amount_cents=10000))
    assert income.status_code==201,income.text
    assert income.json()['currency']=='CNY' and income.json()['payment_method']=='wechat_alipay'
    assert income.json()['cad_amount_cents']==2067 and income.json()['fx_rate']=='0.2067'
    expense=client.post('/studio-api/manage/finance',json=new(currency='CNY',amount_cents=9000))
    assert expense.status_code==201,expense.text
    assert expense.json()['cad_amount_cents']==1860
    assert client.post('/studio-api/manage/finance',json=new(kind='income',category='other',payment_method='EMT',amount_cents=2000)).json()['currency']=='CAD'
    listing=client.get('/studio-api/manage/finance?start=2026-09-01&end=2026-09-30').json()
    assert listing['summary']['currency']=='CAD'
    assert listing['summary']['income_cents']==4067 and listing['summary']['expense_cents']==1860
    assert listing['summary']['balance_cents']==2207
    assert client.post('/studio-api/manage/finance',json=new(kind='income',payment_method='wechat_alipay',currency='CAD')).status_code==422
    assert client.post('/studio-api/manage/finance',json=new(kind='income',payment_method='cash',currency='CNY')).status_code==422
    assert finance_fx.cad_cents(5,'0.1')==1


def test_rate_is_frozen_for_edits_and_retry_and_reselected_for_new_date(setup,monkeypatch):
    client,_,_=setup;host()
    calls=[]
    def rate(day):
        calls.append(day)
        return {'rate':'0.2' if len(calls)==1 else '0.3','rate_date':day.isoformat(),'source':'Bank of Canada'}
    monkeypatch.setattr(finance_fx,'fetch_quote',rate)
    payload=new(currency='CNY',amount_cents=10000)
    entry=client.post('/studio-api/manage/finance',json=payload).json()
    assert entry['cad_amount_cents']==2000
    legacy={key:entry[key] for key in finance.EditEntry.model_fields if key!='currency'}
    assert client.put('/studio-api/manage/finance/'+entry['id'],json=legacy).status_code==409
    finance.initialize(studio.database)
    assert client.post('/studio-api/manage/finance',json=payload).json()['cad_amount_cents']==2000
    edit={key:entry[key] for key in finance.EditEntry.model_fields}
    changed=client.put('/studio-api/manage/finance/'+entry['id'],json={**edit,'amount_cents':15000,'note':'Only change original amount'}).json()
    assert changed['cad_amount_cents']==3000 and len(calls)==1
    edit.update(version=changed['version'],occurred_on='2026-09-10')
    dated=client.put('/studio-api/manage/finance/'+entry['id'],json=edit).json()
    assert dated['cad_amount_cents']==3000 and dated['fx_rate']=='0.3' and len(calls)==2
    history=client.get('/studio-api/manage/finance/'+entry['id']).json()['history']
    assert history[-1]['snapshot']['fx_rate']=='0.2'


def test_missing_rate_never_saves_wrong_currency_or_amount(setup,monkeypatch):
    client,_,_=setup
    assert client.get('/studio-api/manage/finance/exchange-rate?on=2026-09-11').status_code==401
    host()
    def unavailable(day):raise OSError('offline')
    monkeypatch.setattr(finance_fx,'fetch_quote',unavailable)
    response=client.post('/studio-api/manage/finance',json=new(currency='CNY'))
    assert response.status_code==503 and response.json()['detail']=='finance_rate_unavailable'
    assert client.get('/studio-api/manage/finance').json()['total']==0
    assert client.get('/studio-api/manage/finance/exchange-rate?on=2099-09-11').status_code==422
    assert client.post('/studio-api/manage/finance',json=new()).status_code==201


def test_legacy_cad_migration_preserves_original_values_and_audit(setup):
    client,_,_=setup;host()
    payload=new(amount_cents=12345)
    entry=client.post('/studio-api/manage/finance',json=payload).json()
    with studio.database() as db:
        history=[tuple(r) for r in db.execute('SELECT * FROM studio_finance_events')]
        for name in ('currency','fx_rate','fx_date','fx_source','cad_amount_cents'):
            db.execute('ALTER TABLE studio_finance_entries DROP COLUMN '+name)
    finance.initialize(studio.database)
    finance.initialize(studio.database)
    saved=client.get('/studio-api/manage/finance/'+entry['id']).json()['entry']
    assert saved['currency']=='CAD' and saved['amount_cents']==saved['cad_amount_cents']==12345
    assert saved['version']==1
    with studio.database() as db:assert [tuple(r) for r in db.execute('SELECT * FROM studio_finance_events')]==history
    assert client.post('/studio-api/manage/finance',json=payload).json()['id']==entry['id']


def test_fx_uses_latest_prior_business_day_and_never_future_or_invalid(monkeypatch):
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,_):return json.dumps({'observations':[
          {'d':'2026-09-14','FXCNYCAD':{'v':'0.25'}},
          {'d':'2026-09-11','FXCNYCAD':{'v':'0.2067'}},
          {'d':'2026-09-12','FXCNYCAD':{'v':'NaN'}},
          {'d':'2026-09-10','FXCNYCAD':{'v':'0.2061'}}]}).encode()
    monkeypatch.setattr(finance_fx,'urlopen',lambda *args,**kwargs:Response())
    value=finance_fx.fetch_quote(date(2026,9,13))
    assert value=={'rate':'0.2067','rate_date':'2026-09-11','source':'Bank of Canada'}
