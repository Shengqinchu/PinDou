"""Owner-requested manual orders: money, variants, inventory and access boundaries."""
import json
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

import app as studio
import commerce
import shop_orders
from test_commerce import FakeGateway


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, 'DB_PATH', tmp_path/'manual.sqlite3')
    monkeypatch.setattr(commerce, 'PUBLIC_SALES_ENABLED', False)
    gateway=FakeGateway()
    monkeypatch.setattr(commerce, 'gateway', gateway)
    studio.app.dependency_overrides[studio.admin_actor]=lambda:'test-owner'
    with TestClient(studio.app) as client:
        seeds=json.loads((Path(__file__).parents[1]/'07_ops/shop-finished-20260913.json').read_text(encoding='utf8'))
        with studio.database() as db:
            db.execute('UPDATE shop_order_settings SET enabled=1')
            for value in seeds:
                p=commerce.Product.model_validate(value)
                db.execute('INSERT INTO commerce_products VALUES(?,?)',(p.id,p.model_dump_json()))
        client.gateway=gateway
        yield client
    studio.app.dependency_overrides.clear()


def item(variant='1',quantity=1,product='gift-small',choice=''):
    return {'product_id':product,'variant_id':variant,'choice_id':choice,'quantity':quantity}


def quote(client,items):
    return client.post('/studio-api/shop/cart/quote',json={'items':items})


def payload(client,items=None):
    items=items or [item()]
    result=quote(client,items)
    assert result.status_code==200,result.text
    return {'items':items,'quote_id':result.json()['quote_id'],'access_key':secrets.token_hex(32),
            'name':'Test customer','contact':'test@example.com','notes':'No custom request',
            'delivery_method':'pickup','address':''}


def place(client,body,key=None):
    return client.post('/studio-api/shop/orders',json=body,headers={'Idempotency-Key':key or str(uuid.uuid4())})


def product(client,ident='gift-small'):
    return next(p for p in client.get('/studio-api/manage/shop').json()['products'] if p['id']==ident)


def update_order(client,order,status):
    return client.patch('/studio-api/manage/shop/orders/'+order['id'],json={'status':status,'version':order['version'],'staff_note':'Local QA'})


def test_mixed_variants_discount_and_odd_remainder(client):
    q=quote(client,[item('1'),item('2',2),item('1',1,'gift-medium'),item('4',1,'gift-medium')]).json()
    assert q['subtotal_cents']==1700 and q['total_cents']==1500 and q['discount_cents']==200
    assert sum(x['total_cents'] for x in q['lines'])==q['total_cents']
    assert [x['total_cents'] for x in q['lines']]==[250,550,350,350]
    assert q['lines'][0]['variant_zh']=='1 · 发夹'
    assert quote(client,[item('1',4)]).json()['total_cents']==1000


@pytest.mark.parametrize('items',[[item('bogus')],[item('')],[item('1',product='gift-swinging-cats')],
                                [item('1',choice='bogus')],[item('',product='service-ironing')],
                                [item('',product='kit-144')],[item('',product='starter')]])
def test_invalid_or_unpriced_hidden_and_service_products_rejected(client,items):
    assert quote(client,items).status_code in {409,422}


def test_custom_finish_required_and_snapshotted(client):
    q=quote(client,[item('custom',product='gift-swinging-cats',choice='magnet')])
    assert q.status_code==200
    assert q.json()['lines'][0]['choice_en']=='Fridge magnet'
    assert q.json()['lines'][0]['variant_en']=='Custom'
    assert q.json()['total_cents']==600


def test_pickup_order_idempotency_and_no_payment(client):
    body=payload(client,[item('1'),item('2')]);key=str(uuid.uuid4())
    first=place(client,body,key);assert first.status_code==201,first.text
    order=first.json();assert order['status']=='manual_pending' and order['paid_at'] is None
    assert order['customer']['delivery_method']=='pickup' and order['customer']['address']==''
    assert order['quote']['total_cents']==500 and 'payment_url' not in order
    assert place(client,body,key).json()['id']==order['id']
    assert place(client,{**body,'name':'Changed'},key).status_code==409
    assert client.get('/studio-api/orders/'+order['id']).status_code==404
    assert client.get('/studio-api/orders/'+order['id'],headers={'X-Order-Key':body['access_key']}).status_code==200
    assert client.gateway.creates==0
    with pytest.raises(HTTPException):commerce.settle(order['id'],'invalid-payment','test')
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM commerce_orders').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM studio_wallet_ledger').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==0


def test_delivery_details_required_before_order_and_courier_address_private(client):
    body=payload(client)
    for changes in ({'name':' '},{'contact':' '},{'notes':' '},{'delivery_method':'courier'},
                    {'delivery_method':'postal','address':'Hamilton'}):
        assert place(client,body|changes).status_code==422
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM commerce_orders').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM commerce_stock').fetchone()[0]==0
    courier=place(client,body|{'delivery_method':'courier','address':'  1 Main St, Hamilton  '}).json()
    assert courier['customer']['delivery_method']=='courier'
    assert courier['customer']['address']=='1 Main St, Hamilton'
    assert client.get('/studio-api/orders/'+courier['id']).status_code==404
    assert client.get('/studio-api/manage/shop/orders').json()['items'][0]['customer']['address']=='1 Main St, Hamilton'


def test_contact_privacy_version_and_admin_visibility(client):
    body=payload(client);order=place(client,body).json()
    path='/studio-api/shop/orders/'+order['id']+'/contact'
    data={'name':'Test','contact':'微','notes':'Custom note','version':order['version']}
    assert client.patch(path,json=data).status_code==404
    r=client.patch(path,json=data,headers={'X-Order-Key':body['access_key']})
    assert r.status_code==200 and r.json()['customer']['contact']=='微'
    assert client.patch(path,json=data,headers={'X-Order-Key':body['access_key']}).status_code==409
    owner=client.get('/studio-api/manage/shop/orders').json()['items'][0]
    assert owner['customer']['notes']=='Custom note'


def test_owned_orders_claim_across_devices_and_private_boundaries(client, monkeypatch):
    import customer_auth
    monkeypatch.setattr(customer_auth, 'upstream', lambda path, request, token=None, **kwargs: {
        'user_id': 'qa-'+str(token), 'email': str(token)+'@example.test', 'nickname':str(token)})
    own={'Authorization':'Bearer first'}
    other={'Authorization':'Bearer second'}
    body=payload(client)
    ordered=client.post('/studio-api/shop/orders',json=body,headers={'Idempotency-Key':str(uuid.uuid4()),**own})
    assert ordered.status_code==201, ordered.text
    ident=ordered.json()['id']
    assert [row['id'] for row in client.get('/studio-api/auth/shop/orders',headers=own).json()['items']]==[ident]
    assert client.get('/studio-api/auth/shop/orders/'+ident,headers=other).status_code==404
    assert client.post('/studio-api/auth/shop/orders/'+ident+'/claim',json={'access_key':body['access_key']},headers=other).status_code==404
    assert client.get('/studio-api/auth/shop/orders',headers=other).json()['items']==[]
    guest_body=payload(client)
    guest=place(client,guest_body).json()['id']
    assert client.get('/studio-api/auth/shop/orders/'+guest,headers=own).status_code==404
    assert client.post('/studio-api/auth/shop/orders/claim',json={'items':[{'id':guest,'access_key':'0'*64}]},headers=own).json()['claimed']==0
    assert client.post('/studio-api/auth/shop/orders/claim',json={'items':[{'id':guest,'access_key':guest_body['access_key']}]},headers=own).json()['claimed']==1
    assert client.get('/studio-api/auth/shop/orders/'+guest,headers=own).status_code==200
    assert client.get('/studio-api/auth/shop/orders/'+guest,headers=other).status_code==404


def test_stale_optional_login_does_not_block_guest_checkout(client, monkeypatch):
    import customer_auth
    def expired(*_args, **_kwargs):
        raise HTTPException(401, 'expired')
    monkeypatch.setattr(customer_auth, 'require_customer', expired)
    body=payload(client)
    response=client.post('/studio-api/shop/orders',json=body,headers={'Idempotency-Key':str(uuid.uuid4()),'Authorization':'Bearer expired'})
    assert response.status_code==201, response.text
    with studio.database() as db:
        assert db.execute('SELECT owner_id FROM commerce_orders WHERE id=?',(response.json()['id'],)).fetchone()[0]==''


def test_order_progress_and_soft_delete_release_stock_with_audit(client):
    product_row=product(client);product_row['stock']=1
    assert client.put('/studio-api/manage/products/'+product_row['id'],json=product_row).status_code==200
    body=payload(client);order=place(client,body).json()
    preparing=update_order(client,order,'manual_preparing').json()
    assert preparing['fulfillment']=='preparing'
    assert quote(client,[item()]).status_code==409
    ready=update_order(client,preparing,'manual_ready').json()
    assert ready['fulfillment']=='ready'
    assert client.request('DELETE','/studio-api/manage/shop/orders/'+ready['id'],json={'version':ready['version']-1}).status_code==409
    deleted=client.request('DELETE','/studio-api/manage/shop/orders/'+ready['id'],json={'version':ready['version']})
    assert deleted.status_code==200 and deleted.json()['deleted']
    assert client.get('/studio-api/manage/shop/orders').json()['items']==[]
    assert client.get('/studio-api/orders/'+ready['id'],headers={'X-Order-Key':body['access_key']}).status_code==404
    assert quote(client,[item()]).status_code==200
    assert product(client)['stock']==1
    with studio.database() as db:
        assert db.execute('SELECT status FROM commerce_orders WHERE id=?',(ready['id'],)).fetchone()[0]=='manual_deleted'
        assert db.execute("SELECT count(*) FROM commerce_events WHERE order_id=? AND event='manual_order_deleted'",(ready['id'],)).fetchone()[0]==1


def test_stock_hold_completion_once_and_cancel_release(client):
    p=product(client);p['stock']=4
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==200
    order=place(client,payload(client,[item('1'),item('2')])).json()
    assert quote(client,[item('3',3)]).status_code==409
    p=product(client);p['stock']=1
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==409
    confirmed=update_order(client,order,'manual_confirmed').json()
    completed=update_order(client,confirmed,'manual_completed').json()
    assert completed['status']=='manual_completed' and product(client)['stock']==2
    assert update_order(client,confirmed,'manual_completed').status_code==409
    assert update_order(client,completed,'manual_completed').status_code==200
    assert product(client)['stock']==2
    assert update_order(client,completed,'manual_pending').status_code==409
    other=place(client,payload(client,[item('3',2)])).json()
    assert quote(client,[item()]).status_code==409
    cancelled=update_order(client,other,'manual_cancelled').json()
    assert cancelled['status']=='manual_cancelled'
    assert quote(client,[item('4',2)]).status_code==200 and product(client)['stock']==2


def test_price_change_and_tampering_do_not_create_order(client):
    body=payload(client)
    p=product(client);p.update(price_cents=400)
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==200
    assert place(client,body).json()['detail']=='price_changed'
    body=payload(client);body['items'][0]['price_cents']=1
    assert place(client,body).status_code==422
    with studio.database() as db:assert db.execute('SELECT count(*) FROM commerce_orders').fetchone()[0]==0


def test_concurrent_last_stock_has_one_winner(client):
    p=product(client);p['stock']=1
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==200
    a,b=payload(client),payload(client)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda body:place(client,body).status_code,[a,b]))
    assert sorted(results)==[201,409]


def test_visibility_and_category_changes_close_stale_quote(client):
    body=payload(client)
    p=product(client);p['shop_visible']=False
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==200
    assert place(client,body).status_code==409


def test_admin_auth_and_manual_switch_independent(client):
    studio.app.dependency_overrides.clear()
    assert client.get('/studio-api/manage/shop/orders').status_code==401
    assert client.get('/studio-api/shop/catalog').json()['manual_ordering_ready'] is True
    assert client.get('/studio-api/shop/catalog').json()['checkout_ready'] is False
    with studio.database() as db:db.execute('UPDATE shop_order_settings SET enabled=0')
    assert quote(client,[item()]).status_code==409


def test_options_offer_editing_and_version_guard(client):
    p=product(client);p['variants'].append({'id':'8','zh':'8','en':'8'})
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==200
    assert quote(client,[item('8')]).status_code==200
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==409
    p=product(client);p['quantity_offer']['price_cents']=600
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code==422


def test_booking_status_order_before_pagination_and_filters(client):
    with studio.database() as db:
        for i in range(36):
            state=['cancelled','completed','confirmed','pending'][i%4]
            value={'booking':{'date':'2026-09-14','start':'10:00','end':'12:00','guests':1,'plan':'hourly'},'name':'Test','contact_method':'wechat','contact':'x'}
            db.execute('INSERT INTO studio_reservations(id,created_at,updated_at,status,payload,visitor_hash,idempotency_key,payload_hash,owner_id) VALUES(?,?,?,?,?,?,?,?,?)',
                       (f'VIS-QA{i:03}',f'2026-09-13T{i%24:02}:00:00','2026-09-13T10:00:00',state,json.dumps(value),'qa',str(uuid.uuid4()),'qa','qa'))
    first=client.get('/studio-api/manage/reservations').json()
    second=client.get('/studio-api/manage/reservations?page=2').json()
    states=[x['status'] for x in first['items']+second['items']]
    assert states==['pending']*9+['confirmed']*9+['completed']*9+['cancelled']*9
    assert all(x['status']=='completed' for x in client.get('/studio-api/manage/reservations?status=completed').json()['items'])


def test_catalog_import_is_atomic_preserves_details_and_never_restocks_on_replay(client):
    import importlib.util
    source=Path(__file__).parents[1]/'07_ops/studio_finished_catalog.py'
    spec=importlib.util.spec_from_file_location('finished_import',source)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    seeds=json.loads(source.with_name('shop-finished-20260913.json').read_text(encoding='utf8'))
    with studio.database() as db:
        for p in seeds:db.execute('DELETE FROM commerce_products WHERE id=?',(p['id'],))
    with studio.database() as db:
        report,_=migration.plan(db,seeds)
        existing={p['id']:p for p in commerce.products_for(db)}
        protected=migration.protected_hashes(db)
        with pytest.raises(ValueError):migration.apply(db,seeds,'0'*64)
        applied=migration.apply(db,seeds,report['catalog_sha256'])
        assert applied['applied'] and migration.protected_hashes(db)==protected
        current={p['id']:p for p in commerce.products_for(db)}
        for ident,p in existing.items():
            assert {k:v for k,v in current[ident].items() if k not in {'stock','version'}}=={k:v for k,v in p.items() if k not in {'stock','version'}}
            if p.get('shop_collection'):assert current[ident]['stock']==999
        changed=current['gift-small'];changed['stock']=997
        db.execute('UPDATE commerce_products SET payload=? WHERE id=?',(json.dumps(changed),'gift-small'))
        db.commit()
        assert migration.apply(db,seeds,report['catalog_sha256'])['already_applied']
        assert next(p for p in commerce.products_for(db) if p['id']=='gift-small')['stock']==997
