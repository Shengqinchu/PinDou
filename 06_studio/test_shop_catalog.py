import importlib.util
import io
import json
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
import app as studio
import commerce
import content


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(studio,'DB_PATH',tmp_path/'shop.sqlite3')
    studio.app.dependency_overrides[studio.admin_actor]=lambda:'shop-qa'
    with TestClient(studio.app) as c:yield c
    studio.app.dependency_overrides.clear()


def product(**overrides):
    return dict(id='qa-refill',kind='physical',category='beads',zh='A1',en='A1',
                shop_collection='home',shop_category_id='refill-a',shop_visible=True,version=1,**overrides)


def test_catalog_display_is_separate_from_payment_and_source(client):
    p=client.put('/studio-api/manage/products/qa-refill',json=product()).json()
    assert p['price_cents'] is None and p['active'] is False
    d=client.get('/studio-api/shop/catalog').json()
    assert d['checkout_ready'] is False
    assert any(x['id']=='qa-refill' for x in d['products'])
    assert 'sources' not in d
    assert client.post('/studio-api/cart/quote',json={'items':[{'product_id':'qa-refill','quantity':1}]}).json()['detail']=='shop_paused'
    assert len([x for x in d['products'] if x['shop_collection']=='services'])==2


def test_category_cycles_depth_hidden_tree_and_versions(client):
    client.put('/studio-api/manage/products/qa-refill',json=product())
    rows=client.get('/studio-api/manage/shop').json()['categories']
    a=next(x for x in rows if x['id']=='refill-a')
    root=next(x for x in rows if x['id']=='refills')
    assert client.put('/studio-api/manage/shop/categories/refills',json=root|{'parent_id':'refill-a'}).status_code==422
    assert client.put('/studio-api/manage/shop/categories/refill-a',json=a|{'parent_id':'refill-a'}).status_code==422
    assert client.put('/studio-api/manage/shop/categories/refill-a',json=a|{'parent_id':None}).status_code==409
    assert client.put('/studio-api/manage/shop/categories/refills',json=root|{'visible':False}).status_code==200
    assert client.put('/studio-api/manage/shop/categories/refills',json=root).status_code==409
    d=client.get('/studio-api/shop/catalog').json()
    assert not any(x['id']=='qa-refill' for x in d['products'])
    assert not any(x['parent_id']=='refills' for x in d['categories'])
    studio.initialize()
    assert next(x for x in client.get('/studio-api/manage/shop').json()['categories'] if x['id']=='refills')['visible'] is False


def test_product_images_paths_reassignment_and_conflicts(client):
    b=io.BytesIO();Image.new('RGB',(10,20),'red').save(b,format='PNG')
    a=client.post('/studio-api/manage/media?original=true',content=b.getvalue(),headers={'Content-Type':'image/png'}).json()
    p=product(images=[a['src']],image=a['src'])
    r=client.put('/studio-api/manage/products/qa-refill',json=p)
    assert r.status_code==200,r.text
    assert client.get(a['src']).content==b.getvalue()
    assert client.put('/studio-api/manage/products/qa-refill',json=p).status_code==409
    p=r.json()
    for update in ({'images':['https://evil.invalid/image.png']},{'images':[a['src'],a['src']]},{'images':['/studio-api/media/../.env']},{'shop_category_id':'refills'},{'shop_category_id':'missing'}):
        assert client.put('/studio-api/manage/products/qa-refill',json=p|update).status_code==422
    assert client.put('/studio-api/manage/products/qa-refill',json=p|{'shop_collection':'finished','shop_category_id':None}).status_code==200


def test_import_is_idempotent_and_preserves_owner_edits(client,tmp_path):
    spec=importlib.util.spec_from_file_location('shop_import',Path(__file__).parents[1]/'07_ops/studio_shop_import.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    row={'product':product(stock=0,price_cents=None,active=False),'source_key':'pintuanya:test','source':{'source_min_fen':59}}
    r=module.import_products(studio.database,[row],tmp_path,tmp_path/'media',True)
    assert r['inserted']==1
    p=next(p for p in client.get('/studio-api/manage/shop').json()['products'] if p['id']=='qa-refill')
    assert client.put('/studio-api/manage/products/qa-refill',json=p|{'price_cents':250,'stock':3,'zh':'edited'}).status_code==200
    assert module.import_products(studio.database,[row],tmp_path,tmp_path/'media',True)['inserted']==0
    p=next(p for p in client.get('/studio-api/shop/catalog').json()['products'] if p['id']=='qa-refill')
    assert (p['zh'],p['price_cents'],p['stock'])==('edited',250,3)
    assert 'source_min_fen' not in client.get('/studio-api/shop/catalog').text
    with studio.database() as db:assert db.execute("SELECT count(*) FROM commerce_events WHERE event='shop_product_imported'").fetchone()[0]==1


def test_shop_owner_endpoints_require_auth(client):
    studio.app.dependency_overrides.clear()
    assert client.get('/studio-api/manage/shop').status_code==401
    assert client.put('/studio-api/manage/products/qa-refill',json=product()).status_code==401
    assert client.put('/studio-api/manage/shop/categories/qa-cat',json={'id':'qa-cat','zh':'QA','en':'QA'}).status_code==401
    assert client.get('/studio-api/shop/catalog').status_code==200
