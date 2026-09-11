import re
from test_customer_auth import client
import customer_auth

def test_unnamed_accounts_have_stable_distinct_suffixes(client,monkeypatch):
    def profile(ident):
        monkeypatch.setattr(customer_auth,'upstream',lambda *a,**kw:{'user_id':'wechat_authing_'+ident*64,'email':None,'nickname':'','avatar':''})
        return client.get('/studio-api/auth/me',headers={'Authorization':'Bearer fixture'}).json()['user']
    first=profile('1');second=profile('2');again=profile('1')
    assert re.fullmatch(r'拼豆用户_[0-9A-F]{8}',first['nickname'])
    assert first['nickname']!=second['nickname'] and again['nickname']==first['nickname']
    assert first['id']==again['id'] and first['avatar']==''

def test_custom_names_are_not_rewritten(client,monkeypatch):
    for name in ['小雨','拼豆用户','My Studio Name']:
        monkeypatch.setattr(customer_auth,'upstream',lambda *a,**kw:{'user_id':'wechat_authing_'+'a'*64,'nickname':name,'email':None,'avatar':'/static/avatar.png'})
        value=client.get('/studio-api/auth/me',headers={'Authorization':'Bearer fixture'}).json()['user']
        assert value['nickname']==name and value['avatar']=='/static/avatar.png'
