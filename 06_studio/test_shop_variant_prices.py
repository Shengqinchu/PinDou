"""Different prices for numbered pieces and their full set, using server quotes."""
import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
import commerce
import app as studio
from test_shop_orders import client, item, quote, payload, place, product, update_order

ROOT = Path(__file__).parents[1]
SEEDS = json.loads((ROOT/'07_ops/shop-scenery-20260913.json').read_text(encoding='utf8'))


def add_scenery():
    with studio.database() as db:
        for seed in SEEDS:
            p = commerce.Product.model_validate(seed)
            db.execute('INSERT INTO commerce_products VALUES(?,?)', (p.id,p.model_dump_json()))


@pytest.mark.parametrize('ident,single,full', [('scenery-sunset-apocalypse',1200,4500),('scenery-blue-coast',1000,3800)])
def test_every_scenery_variant_and_mixed_cart(client,ident,single,full):
    add_scenery()
    for variant in ['1','2','3','4','full-set']:
        result = quote(client,[item(variant,product=ident)])
        assert result.status_code == 200, result.text
        q = result.json()
        assert q['total_cents'] == (full if variant == 'full-set' else single)
        assert q['lines'][0]['unit_cents'] == q['total_cents']
    q = quote(client,[item('1',2,ident),item('full-set',2,ident)]).json()
    assert q['total_cents'] == q['subtotal_cents'] == 2*single + 2*full
    assert q['discount_cents'] == 0
    assert quote(client,[item('1',product=ident),item('2',product=ident),item('3',product=ident),item('4',product=ident)]).json()['total_cents'] == single*4


def test_both_full_sets_total_and_order_snapshot(client):
    add_scenery()
    body = payload(client,[item('full-set',product=p['id']) for p in SEEDS])
    order = place(client,body).json()
    assert order['quote']['total_cents'] == 8300
    assert [line['unit_cents'] for line in order['quote']['lines']] == [4500,3800]
    assert all(line['variant_zh'] == '全套（四图）' for line in order['quote']['lines'])
    saved = update_order(client,order,'manual_completed')
    assert saved.status_code == 200
    assert saved.json()['quote'] == order['quote']
    assert client.gateway.creates == 0


def test_full_set_edit_invalidates_old_quote_and_clearing_inherits(client):
    add_scenery()
    ident = SEEDS[0]['id']
    body = payload(client,[item('full-set',product=ident)])
    p = product(client,ident)
    p['variants'][-1]['price_cents'] = 4600
    assert client.put('/studio-api/manage/products/'+ident,json=p).status_code == 200
    assert place(client,body).json()['detail'] == 'price_changed'
    assert quote(client,[item('full-set',product=ident)]).json()['total_cents'] == 4600
    assert client.put('/studio-api/manage/products/'+ident,json=p).status_code == 409
    p = product(client,ident)
    p['variants'][-1]['price_cents'] = None
    assert client.put('/studio-api/manage/products/'+ident,json=p).status_code == 200
    assert quote(client,[item('full-set',product=ident)]).json()['total_cents'] == 1200


def test_explicit_variant_price_does_not_stack_regular_offer(client):
    p = product(client)
    p['variants'].append({'id':'set','zh':'Set','en':'Set','price_cents':1200})
    assert client.put('/studio-api/manage/products/'+p['id'],json=p).status_code == 200
    q = quote(client,[item('set',2),item('1'),item('2',2)]).json()
    assert q['subtotal_cents'] == 3300 and q['total_cents'] == 3200
    assert q['lines'][0]['total_cents'] == 2400 and q['lines'][0]['discount_cents'] == 0
    assert quote(client,[item('set',2)]).json()['total_cents'] == 2400


@pytest.mark.parametrize('price',[0,-100,True,12.5,1000001])
def test_invalid_variant_price_rejected(price):
    with pytest.raises(ValidationError):
        commerce.ProductVariant(id='set',zh='Set',en='Set',price_cents=price)


def test_variant_price_cannot_be_supplied_by_customer(client):
    add_scenery()
    selection = item('full-set',product=SEEDS[0]['id']) | {'price_cents':1}
    assert quote(client,[selection]).status_code == 422


def test_scenery_import_preserves_existing_goods_and_replay(client):
    source = ROOT/'07_ops/studio_scenery_catalog.py'
    spec = importlib.util.spec_from_file_location('scenery_import',source)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with studio.database() as db:
        existing = dict(db.execute('SELECT id,payload FROM commerce_products'))
        protected = migration.protected_hashes(db)
        preview,_ = migration.plan(db,SEEDS)
        with pytest.raises(ValueError):
            migration.apply(db,SEEDS,'0'*64)
        assert dict(db.execute('SELECT id,payload FROM commerce_products')) == existing
        report = migration.apply(db,SEEDS,preview['catalog_sha256'])
        assert report['applied'] and migration.protected_hashes(db) == protected
        current = dict(db.execute('SELECT id,payload FROM commerce_products'))
        assert all(current[k] == v for k,v in existing.items())
        changed = json.loads(current[SEEDS[0]['id']])
        changed['variants'][-1]['price_cents'] = 4600
        db.execute('UPDATE commerce_products SET payload=? WHERE id=?',(json.dumps(changed),changed['id']))
        db.commit()
        assert migration.apply(db,SEEDS,preview['catalog_sha256'])['already_applied']
        actual = json.loads(db.execute('SELECT payload FROM commerce_products WHERE id=?',(changed['id'],)).fetchone()[0])
        assert actual['variants'][-1]['price_cents'] == 4600
