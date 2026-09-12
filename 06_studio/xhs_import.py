"""Read the owner's publicly shared Xiaohongshu notes without executing page code.

Only allowlisted HTTPS hosts are fetched. A browser-compatible transport can read
public pages that direct requests cannot access. No user's cookies are copied.
"""
from __future__ import annotations
import json, re
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from fastapi import HTTPException

OWNER_ID = '65f8375c000000000b00c921'
PAGE_HOSTS = {'www.xiaohongshu.com','xiaohongshu.com','xhslink.com','www.xhslink.com','xhslink.cn','www.xhslink.cn'}
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'

def checked_url(url, image=False):
    p=urlparse(url)
    host=(p.hostname or '').lower()
    allowed=host in PAGE_HOSTS if not image else host.endswith('.xhscdn.com')
    if p.scheme!='https' or not allowed or p.username or p.password or p.port not in (None,443):
        raise HTTPException(422,'import_url_not_supported')
    return url

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args): return None

def fetch(url, image=False):
    limit=12*1024*1024 if image else 3*1024*1024
    opener=build_opener(NoRedirect())
    for _ in range(5):
        checked_url(url,image)
        try:
            with opener.open(Request(url,headers={'User-Agent':UA,'Referer':'https://www.xiaohongshu.com/'}),timeout=20) as response:
                data=response.read(limit+1)
                if len(data)>limit: raise HTTPException(413,'import_resource_too_large')
                return data,url
        except HTTPError as exc:
            if exc.code in (301,302,303,307,308):
                url=urljoin(url,exc.headers.get('Location',''))
                continue
            raise HTTPException(422,'import_source_unavailable') from exc
        except (URLError,TimeoutError,OSError) as exc:
            raise HTTPException(422,'import_source_unavailable') from exc
    raise HTTPException(422,'import_source_unavailable')

def parse_note(html, expected_id=None):
    match=re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script',html,re.S)
    if not match: raise HTTPException(422,'import_source_unavailable')
    # Replace JS undefined tokens, never the same text inside quoted strings.
    raw=re.sub(r'"(?:\\.|[^"\\])*"|\bundefined\b',lambda m:'null' if m[0]=='undefined' else m[0],match[1])
    try:
        state=json.loads(raw)
        notes=state['note']['noteDetailMap']
        note=next(v['note'] for v in notes.values() if v.get('note',{}).get('noteId') and (not expected_id or v['note']['noteId']==expected_id))
    except (ValueError,KeyError,TypeError,StopIteration):
        raise HTTPException(422,'import_source_unavailable')
    return validate_note(note,expected_id)


def validate_note(note,expected_id=None):
    if not isinstance(note,dict) or not isinstance(note.get('user'),dict):raise HTTPException(422,'import_incomplete')
    if not re.fullmatch(r'[a-f0-9]{24}',str(note.get('noteId',''))) or (expected_id and note['noteId']!=expected_id):raise HTTPException(422,'import_source_unavailable')
    if note.get('user',{}).get('userId')!=OWNER_ID:
        raise HTTPException(422,'import_author_mismatch')
    if not note.get('title') or not note.get('desc') or not note.get('time') or not note.get('imageList'):
        raise HTTPException(422,'import_incomplete')
    if not isinstance(note['title'],str) or not isinstance(note['desc'],str) or len(note['title'])>250 or len(note['desc'])>25000:
        raise HTTPException(422,'import_incomplete')
    if not isinstance(note['time'],(int,float)) or isinstance(note['time'],bool) or not isinstance(note['imageList'],list) or len(note['imageList'])>40:
        raise HTTPException(422,'import_incomplete')
    return note

def retrieve(share):
    found=re.search(r'https?://[^\s<>]+',share)
    if not found: raise HTTPException(422,'import_url_not_supported')
    source=found[0].rstrip('。，),]')
    parsed=urlparse(source)
    # Older official share text uses http; upgrade the known host before fetching.
    if parsed.scheme=='http' and parsed.hostname in PAGE_HOSTS:
        source=urlunparse(parsed._replace(scheme='https'))
    checked_url(source)
    expected=re.search(r'/(?:explore|discovery/item)/([a-f0-9]{24})',source)
    try:
        data,final=fetch(source)
        ident=expected or re.search(r'/(?:explore|discovery/item)/([a-f0-9]{24})',final)
        return parse_note(data.decode('utf8','replace'),ident[1] if ident else None),final
    except HTTPException as exc:
        if exc.detail!='import_source_unavailable':raise
        import xhs_browser
        if not xhs_browser.configured():raise
        try:note,final=xhs_browser.read_note(source,expected[1] if expected else None)
        except xhs_browser.BrowserReadError as error:raise HTTPException(422,str(error)) from None
        checked_url(final)
        ident=expected or re.search(r'/(?:explore|discovery/item)/([a-f0-9]{24})',final)
        if not ident:raise HTTPException(422,'import_source_unavailable')
        note=validate_note(note,ident[1])
        import logging
        logging.getLogger('uvicorn.error').info('studio_xhs_read reader=browser_transport note=%s images=%d',note['noteId'],len(note['imageList']))
        return note,final

def photo_url(photo):
    value=photo.get('urlDefault') or next((x.get('url') for x in photo.get('infoList',[]) if x.get('imageScene')=='WB_DFT'),None)
    if not value: raise HTTPException(422,'import_incomplete')
    return checked_url(value.replace('http://','https://',1),True)
