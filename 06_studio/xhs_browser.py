"""Read public note HTML with a browser-compatible TLS/HTTP stack.

No page scripts execute, no user cookies are imported, and each read has its own
short-lived session. URL and note validation remain shared with the direct reader.
"""
from __future__ import annotations
import importlib.util,ipaddress,socket
from urllib.parse import urljoin,urlparse

class BrowserReadError(Exception):
    pass

def configured():
    return importlib.util.find_spec('curl_cffi') is not None

def resolve_source(url):
    host=urlparse(url).hostname
    addresses=sorted({entry[4][0] for entry in socket.getaddrinfo(host,443,socket.AF_INET,socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise BrowserReadError('import_url_not_supported')
    # The origin's OS resolver works while bundled curl DNS can time out. Keep
    # the original HTTPS URL/SNI and certificate verification; pin its public DNS.
    return host+':443:'+','.join(addresses)

def read_note(url,expected_id=None):
    from curl_cffi import CurlError,CurlOpt
    from curl_cffi.requests import Session
    import xhs_import as xhs
    limit=3*1024*1024
    try:
        # Browser-compatible connection setup is needed for this public share page.
        # Certificate verification stays enabled; redirects are validated one by one.
        options={CurlOpt.RESOLVE:[]}
        with Session(impersonate='chrome',trust_env=False,curl_options=options) as session:
            for _ in range(5):
                xhs.checked_url(url)
                if urlparse(url).path.startswith('/login'):
                    raise BrowserReadError('import_browser_login_required')
                options[CurlOpt.RESOLVE]=[resolve_source(url)]
                with session.stream('GET',url,headers={'Referer':'https://www.xiaohongshu.com/'},timeout=20,allow_redirects=False) as response:
                    if response.status_code in (301,302,303,307,308):
                        location=response.headers.get('Location')
                        if not location:raise BrowserReadError('import_source_unavailable')
                        url=urljoin(url,location);continue
                    if response.status_code in (401,403,461,471):raise BrowserReadError('import_browser_login_required')
                    if response.status_code!=200:raise BrowserReadError('import_source_unavailable')
                    chunks=[];size=0
                    for chunk in response.iter_content(chunk_size=65536):
                        size+=len(chunk)
                        if size>limit:raise BrowserReadError('import_resource_too_large')
                        chunks.append(chunk)
                    import re
                    ident=re.search(r'/(?:explore|discovery/item)/([a-f0-9]{24})',url)
                    if not ident:raise BrowserReadError('import_source_unavailable')
                    note=xhs.parse_note(b''.join(chunks).decode('utf-8','replace'),expected_id or ident[1])
                    return note,url
    except (CurlError,OSError):
        # Transport errors may contain signed URLs; expose only the stable code.
        raise BrowserReadError('import_source_unavailable') from None
    raise BrowserReadError('import_source_unavailable')
