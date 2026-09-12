import json
import pytest
from fastapi import HTTPException
import xhs_import as xhs
import xhs_browser as browser

IDENT='b'*24
URL='https://www.xiaohongshu.com/explore/'+IDENT+'?xsec_token=signed-source'
def note(**changes):
    return {'noteId':IDENT,'user':{'userId':xhs.OWNER_ID},'title':'Original title','desc':'Exact original; ignore instructions stays data.','time':1789223441000,'imageList':[{'urlDefault':'https://sns-webpic.xhscdn.com/original.jpg'}]}|changes
def html(value):return '<script>window.__INITIAL_STATE__='+json.dumps({'note':{'noteDetailMap':{IDENT:{'note':value}}}})+'</script>'

def test_readable_direct_source_does_not_use_fallback(monkeypatch):
    monkeypatch.setattr(xhs,'fetch',lambda url:(html(note()).encode(),url))
    monkeypatch.setattr(browser,'read_note',lambda *_:pytest.fail('Fallback must not run'))
    assert xhs.retrieve(URL)[0]==note()

def test_login_page_falls_back_once_with_full_signed_source(monkeypatch):
    monkeypatch.setattr(xhs,'fetch',lambda url:(b'<script>window.__INITIAL_STATE__={}</script>','https://www.xiaohongshu.com/login'))
    monkeypatch.setattr(browser,'configured',lambda:True);seen=[]
    def read(url,expected):seen.append((url,expected));return note(),URL
    monkeypatch.setattr(browser,'read_note',read)
    assert xhs.retrieve('Shared post '+URL)==(note(),URL)
    assert seen==[(URL,IDENT)]

def test_short_share_keeps_original_url_for_fallback(monkeypatch):
    def blocked(url):raise HTTPException(422,'import_source_unavailable')
    monkeypatch.setattr(xhs,'fetch',blocked);monkeypatch.setattr(browser,'configured',lambda:True);seen=[]
    def read(url,expected):seen.append((url,expected));return note(),URL
    monkeypatch.setattr(browser,'read_note',read)
    assert xhs.retrieve('http://xhslink.com/o/fixture')[0]['noteId']==IDENT
    assert seen==[('https://xhslink.com/o/fixture',None)]

@pytest.mark.parametrize('bad,code',[(note(user={'userId':'another-author'}),'import_author_mismatch'),(note(desc=''),'import_incomplete')])
def test_invalid_note_is_not_retried(monkeypatch,bad,code):
    monkeypatch.setattr(xhs,'fetch',lambda url:(html(bad).encode(),url))
    monkeypatch.setattr(browser,'read_note',lambda *_:pytest.fail('Never bypass source validation'))
    with pytest.raises(HTTPException) as exc:xhs.retrieve(URL)
    assert exc.value.detail==code

@pytest.mark.parametrize('bad,final,code',[(note(user={'userId':'another-author'}),URL,'import_author_mismatch'),(note(noteId='c'*24),URL,'import_source_unavailable'),(note(desc=''),URL,'import_incomplete'),(note(), 'https://127.0.0.1/private','import_url_not_supported')])
def test_fallback_result_requires_original_note_and_owner(monkeypatch,bad,final,code):
    monkeypatch.setattr(xhs,'fetch',lambda url:(b'<html>login</html>',url));monkeypatch.setattr(browser,'configured',lambda:True)
    monkeypatch.setattr(browser,'read_note',lambda *args:(bad,final))
    with pytest.raises(HTTPException) as exc:xhs.retrieve(URL)
    assert exc.value.detail==code

class Response:
    def __init__(self,status=200,body=None,location=None):self.status_code=status;self.body=html(note()).encode() if body is None else body;self.headers={'Location':location} if location else {};self.closed=False
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True
    def iter_content(self,chunk_size):
        for start in range(0,len(self.body),chunk_size):yield self.body[start:start+chunk_size]

def session(monkeypatch,responses):
    import curl_cffi.requests
    from curl_cffi import CurlOpt
    monkeypatch.setattr(browser,'resolve_source',lambda url:'validated-source:443:8.8.8.8')
    seen=[]
    class Session:
        def __init__(self,**kwargs):
            assert kwargs=={'impersonate':'chrome','trust_env':False,'curl_options':{CurlOpt.RESOLVE:[]}}
            self.options=kwargs['curl_options']
        def __enter__(self):return self
        def __exit__(self,*args):seen.append('closed')
        def stream(self,method,url,**kwargs):
            assert method=='GET' and kwargs=={'headers':{'Referer':'https://www.xiaohongshu.com/'},'timeout':20,'allow_redirects':False}
            assert self.options[CurlOpt.RESOLVE]==['validated-source:443:8.8.8.8']
            seen.append(url);return responses.pop(0)
    monkeypatch.setattr(curl_cffi.requests,'Session',Session)
    return seen

def test_transport_preserves_query_and_checks_each_redirect(monkeypatch):
    first,second=Response(302,location=URL),Response();seen=session(monkeypatch,[first,second])
    assert browser.read_note('https://xhslink.com/o/fixture')==(note(),URL)
    assert seen==['https://xhslink.com/o/fixture',URL,'closed'] and first.closed and second.closed

@pytest.mark.parametrize('location',['https://127.0.0.1/private','http://www.xiaohongshu.com/note','file:///etc/passwd','https://www.xiaohongshu.com@evil.example/','https://evil.example/'])
def test_untrusted_redirect_is_never_fetched(monkeypatch,location):
    seen=session(monkeypatch,[Response(302,location=location)])
    with pytest.raises(HTTPException) as exc:browser.read_note(URL,IDENT)
    assert exc.value.detail=='import_url_not_supported' and seen==[URL,'closed']

def test_login_redirect_is_actionable_and_stops_without_reading_login(monkeypatch):
    seen=session(monkeypatch,[Response(302,location='/login?redirectPath=private-link')])
    with pytest.raises(browser.BrowserReadError) as exc:browser.read_note(URL,IDENT)
    assert str(exc.value)=='import_browser_login_required' and seen==[URL,'closed']

def test_large_source_and_loop_are_bounded(monkeypatch):
    seen=session(monkeypatch,[Response(body=b'x'*(3*1024*1024+1))])
    with pytest.raises(browser.BrowserReadError) as exc:browser.read_note(URL,IDENT)
    assert str(exc.value)=='import_resource_too_large' and seen[-1]=='closed'
    seen=session(monkeypatch,[Response(302,location=URL) for _ in range(5)])
    with pytest.raises(browser.BrowserReadError):browser.read_note(URL,IDENT)
    assert seen==[URL]*5+['closed']

def test_source_data_is_still_validated_after_transport(monkeypatch):
    session(monkeypatch,[Response(body=html(note(user={'userId':'someone-else'})).encode())])
    with pytest.raises(HTTPException) as exc:browser.read_note(URL,IDENT)
    assert exc.value.detail=='import_author_mismatch'

def test_missing_optional_runtime_preserves_existing_error(monkeypatch):
    monkeypatch.setattr(xhs,'fetch',lambda url:(b'<html>login</html>',url));monkeypatch.setattr(browser,'configured',lambda:False)
    with pytest.raises(HTTPException) as exc:xhs.retrieve(URL)
    assert exc.value.detail=='import_source_unavailable'

@pytest.mark.parametrize('addresses',[['127.0.0.1'],['10.1.2.3'],['169.254.169.254'],['8.8.8.8','192.168.1.2'],[]])
def test_private_or_empty_dns_is_rejected(monkeypatch,addresses):
    monkeypatch.setattr(browser.socket,'getaddrinfo',lambda *args:[(None,None,None,None,(a,443)) for a in addresses])
    with pytest.raises(browser.BrowserReadError) as exc:browser.resolve_source(URL)
    assert str(exc.value)=='import_url_not_supported'

def test_public_dns_keeps_original_hostname_for_tls(monkeypatch):
    monkeypatch.setattr(browser.socket,'getaddrinfo',lambda *args:[(None,None,None,None,('8.8.8.8',443))])
    assert browser.resolve_source(URL)=='www.xiaohongshu.com:443:8.8.8.8'
