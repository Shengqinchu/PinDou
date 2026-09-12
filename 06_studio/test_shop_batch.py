import json
import pytest
from fastapi.testclient import TestClient
import app as studio


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'DB_PATH',tmp_path/'batch.sqlite3')
    studio.app.dependency_overrides[studio.admin_actor]=lambda:'batch-qa'
    with TestClient(studio.app) as c:
        for i in range(3):
            data={'id':f'bulk-{i}','kind':'physical','category':'beads','zh':f'A{i+1}','en':f'A{i+1}','shop_collection':'home','shop_category_id':'refill-a','shop_visible':True,'stock':8,'price_cents':100,'version':1}
            assert c.put('/studio-api/manage/products/'+data['id'],json=data).status_code==200
        yield c
    studio.app.dependency_overrides.clear()


def catalog(client):
    return {p['id']:p for p in client.get('/studio-api/manage/shop').json()['products']}


def batch(client,items):
    return client.patch('/studio-api/manage/shop/products/batch',json={'items':items})


def test_batch_price_images_and_single_editor_compatibility(client):
    image='/studio-api/media/'+'a'*64+'.jpg'
    p=catalog(client)
    result=batch(client,[{'id':'bulk-0','version':p['bulk-0']['version'],'price_cents':250,'images':[image]}, {'id':'bulk-1','version':p['bulk-1']['version'],'price_cents':None}])
    assert result.status_code==200,result.text
    assert result.json()['updated']==2
    new=catalog(client)
    assert new['bulk-0']['images']==[image] and new['bulk-0']['image']==image
    assert new['bulk-0']['price_cents']==250 and new['bulk-0']['stock']==8
    assert new['bulk-0']['shop_visible'] is True and new['bulk-0']['active'] is False
    assert new['bulk-1']['price_cents'] is None
    assert new['bulk-2']==p['bulk-2']
    new['bulk-0']['zh']='Single edit after batch'
    assert client.put('/studio-api/manage/products/bulk-0',json=new['bulk-0']).status_code==200


def test_one_version_conflict_rolls_back_entire_batch(client):
    before=catalog(client)
    result=batch(client,[{'id':'bulk-0','version':2,'price_cents':299},{'id':'bulk-1','version':1,'price_cents':399}])
    assert result.status_code==409
    assert catalog(client)==before
    with studio.database() as db:assert db.execute("SELECT count(*) FROM commerce_events WHERE event='shop_product_batch_updated'").fetchone()[0]==0


def test_append_dedup_replace_and_omitted_price(client):
    a='/studio-api/media/'+'a'*64+'.jpg';b='/studio-api/media/'+'b'*64+'.jpg'
    assert batch(client,[{'id':'bulk-0','version':2,'images':[a,a]}]).status_code==200
    assert batch(client,[{'id':'bulk-0','version':3,'images':[a,b]}]).status_code==200
    p=catalog(client)['bulk-0'];assert p['images']==[a,b] and p['price_cents']==100
    assert batch(client,[{'id':'bulk-0','version':4,'images':[b],'image_mode':'replace'}]).status_code==200
    assert catalog(client)['bulk-0']['images']==[b]
    assert batch(client,[{'id':'bulk-0','version':5,'images':[],'image_mode':'replace'}]).status_code==200
    assert catalog(client)['bulk-0']['image']==''


@pytest.mark.parametrize('bad',[{'images':['https://example.com/image.png']},{'images':['/studio-api/media/../.env']},{'price_cents':0},{'price_cents':2.5},{'price_cents':True},{'stock':2}])
def test_invalid_change_cannot_partially_write(client,bad):
    before=catalog(client)
    result=batch(client,[{'id':'bulk-0','version':2,'price_cents':299},{'id':'bulk-1','version':2,**bad}])
    assert result.status_code==422
    assert catalog(client)==before


def test_batch_auth_duplicates_legacy_and_noop(client):
    assert batch(client,[{'id':'bulk-0','version':2,'price_cents':100}]).json()['updated']==0
    assert batch(client,[{'id':'bulk-0','version':2,'price_cents':200}]*2).status_code==422
    assert batch(client,[{'id':'hourly','version':1,'price_cents':299}]).status_code==422
    studio.app.dependency_overrides.clear()
    assert batch(client,[{'id':'bulk-0','version':2,'price_cents':200}]).status_code==401
