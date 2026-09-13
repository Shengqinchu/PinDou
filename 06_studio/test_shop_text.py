import json
import pytest
from fastapi.testclient import TestClient
import app as studio


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'DB_PATH',tmp_path/'shop-text.sqlite3')
    studio.app.dependency_overrides[studio.admin_actor]=lambda:'long-text-local-qa'
    with TestClient(studio.app) as client:
        yield client
    studio.app.dependency_overrides.clear()


def payload():
    return {'id':'qa-long-copy','kind':'physical','category':'beads','zh':'长文字测试','en':'Long text test',
        'shop_collection':'home','shop_category_id':'kits','shop_visible':True,'version':1,
        'detailZh':('拼豆🐶\n'*3000)[:9998]+'结束',
        'detailEn':('Bead instructions.\n'*700)[:9994]+'EN-END'}


def test_maximum_bilingual_descriptions_survive_save_reload_and_batch(client):
    value=payload()
    assert len(value['detailZh'])==len(value['detailEn'])==10000
    value['zh']='名'*200;value['en']='N'*200
    body=json.dumps(value,ensure_ascii=True)
    assert len(body)>16000
    response=client.put('/studio-api/manage/products/qa-long-copy',content=body,headers={'Content-Type':'application/json'})
    assert response.status_code==200,response.text
    saved=response.json()
    for field in ('zh','en','detailZh','detailEn'):assert saved[field]==value[field]
    public=next(p for p in client.get('/studio-api/shop/catalog').json()['products'] if p['id']==value['id'])
    for field in ('detailZh','detailEn'):assert public[field]==value[field]
    changed=client.patch('/studio-api/manage/shop/products/batch',json={'items':[{'id':value['id'],'version':saved['version'],'price_cents':299}]})
    assert changed.status_code==200
    for field in ('detailZh','detailEn'):assert changed.json()['products'][0][field]==value[field]


def test_over_limit_rejects_without_truncating_or_overwriting(client):
    saved=client.put('/studio-api/manage/products/qa-long-copy',json=payload()).json()
    for changes in ({'detailZh':'文'*10001},{'detailEn':'e'*10001},{'zh':'名'*201},{'en':'n'*201}):
        result=client.put('/studio-api/manage/products/qa-long-copy',json=saved|changes)
        assert result.status_code==422,result.text
        actual=next(p for p in client.get('/studio-api/manage/shop').json()['products'] if p['id']==saved['id'])
        assert actual==saved


def test_larger_product_body_retains_auth_and_other_route_limits(client):
    studio.app.dependency_overrides.clear()
    body=json.dumps(payload(),ensure_ascii=True)
    assert client.put('/studio-api/manage/products/qa-long-copy',content=body,headers={'Content-Type':'application/json'}).status_code==401
    assert client.post('/studio-api/reservations',content=body,headers={'Content-Type':'application/json'}).status_code==413
    assert client.put('/studio-api/manage/products/qa-long-copy',content=b'x'*(256*1024+1),headers={'Content-Type':'application/json'}).status_code==413
