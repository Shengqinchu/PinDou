import json
import uuid
import pytest
import app as studio
import commerce
from test_shop_orders import client, payload, place, product, update_order, quote, item


def archive(client, items, action='delete', key=None):
    return client.post('/studio-api/manage/shop/products/archive',json={'items':items,'action':action},
                       headers={'Idempotency-Key':key or str(uuid.uuid4())})


def ref(p):
    return {'id':p['id'],'version':p['version']}


def test_delete_blocks_quotes_keeps_orders_and_survives_restart(client):
    body=payload(client);order=place(client,body).json();p=product(client);key=str(uuid.uuid4())
    with studio.database() as db: before=[tuple(r) for r in db.execute('SELECT * FROM commerce_orders')]
    assert archive(client,[ref(p)],key=key).status_code==200
    assert archive(client,[ref(p)],key=key).status_code==200
    for path in ('/studio-api/shop/catalog','/studio-api/manage/shop','/studio-api/manage/commerce'):
        assert p['id'] not in [v['id'] for v in client.get(path).json()['products']]
    removed=client.get('/studio-api/manage/shop?deleted=true').json()['products']
    assert [v['id'] for v in removed]==[p['id']]
    assert quote(client,[item()]).status_code==409
    assert place(client,body).status_code==409
    assert client.put('/studio-api/manage/products/'+p['id'],json=removed[0]).status_code==409
    assert client.patch('/studio-api/manage/shop/products/batch',json={'items':[{**ref(removed[0]),'price_cents':100}]}).status_code==409
    studio.initialize()
    assert quote(client,[item()]).status_code==409
    with studio.database() as db: assert [tuple(r) for r in db.execute('SELECT * FROM commerce_orders')]==before
    # Existing orders remain fulfillable and deduct retained inventory once.
    confirmed=update_order(client,order,'manual_confirmed').json()
    completed=update_order(client,confirmed,'manual_completed')
    assert completed.status_code==200,completed.text
    p2=client.get('/studio-api/manage/shop?deleted=true').json()['products'][0]
    assert p2['stock']==p['stock']-1
    assert archive(client,[ref(p2)],'restore').status_code==200
    assert product(client)['stock']==p['stock']-1
    assert quote(client,[item()]).status_code==200
    assert archive(client,[ref(p)],key=key).status_code==200
    assert product(client)['id']==p['id']


def test_batch_atomic_versions_audit_and_auth(client):
    a=product(client);b=product(client,'gift-medium')
    items=[ref(a),{**ref(b),'version':999}]
    assert archive(client,items).status_code==409
    assert client.get('/studio-api/manage/shop?deleted=true').json()['products']==[]
    with studio.database() as db: assert db.execute('SELECT count(*) FROM studio_archive_actions').fetchone()[0]==0
    assert archive(client,[ref(a),ref(a)]).status_code==422
    assert archive(client,[ref(a),ref(b)]).json()['changed']==2
    assert len(client.get('/studio-api/manage/shop?deleted=true').json()['products'])==2
    studio.app.dependency_overrides.clear()
    assert archive(client,[ref(a)]).status_code==401
    assert client.get('/studio-api/manage/shop?deleted=true').status_code==401


def test_seed_product_not_resurrected(client):
    p=product(client,'service-ironing')
    assert archive(client,[ref(p)]).status_code==200
    studio.initialize();studio.initialize()
    assert 'service-ironing' not in [p['id'] for p in client.get('/studio-api/shop/catalog').json()['products']]
    assert archive(client,[{'id':'hourly','version':1}]).status_code==422
