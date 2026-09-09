"""Small first-party operational record. Never store bodies, query strings or tokens."""
import hashlib,json, logging, re, time, uuid
from pathlib import Path
from starlette.responses import JSONResponse
from fastapi import Depends, Request, HTTPException
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal

log=logging.getLogger('uvicorn.error')

def route_name(path):
    # Use bounded route names, never a customer receipt, account or media identifier.
    parts=path.strip('/').split('/')
    if len(parts)>3:parts=parts[:3]+[':item']
    return '/'+ '/'.join(parts)

def initialize(database):
    with database() as db:
        db.execute('CREATE TABLE IF NOT EXISTS studio_diagnostics (id INTEGER PRIMARY KEY, request_id TEXT, created_at INTEGER, route TEXT, method TEXT, status INTEGER, elapsed_ms INTEGER, code TEXT)')
        db.execute('CREATE INDEX IF NOT EXISTS diagnostics_created ON studio_diagnostics(created_at)')
        db.execute('CREATE TABLE IF NOT EXISTS studio_diagnostic_limits (client TEXT PRIMARY KEY,bucket INTEGER,count INTEGER)')

class ClientEvent(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['error','unhandledrejection']
    name:Literal['Error','TypeError','ReferenceError','SyntaxError','RangeError','Other']
    page:Literal['/','/visit','/details','/journal','/shop','/manage','/reservation','/order','/other']
    asset:str=Field(default='',pattern=r'^(?:[A-Za-z0-9_-]{1,100}\.js)?$')
    line:int=Field(default=0,ge=0,le=1000000)

def install(app,database,admin_actor):
    @app.post('/studio-api/client-event',status_code=202)
    def client_event(payload:ClientEvent,request:Request):
        bucket=int(time.time())//3600
        # Short-lived salted identifier, not a raw IP or account identifier.
        client=hashlib.sha256(f'{bucket}:{request.client.host if request.client else "unknown"}'.encode()).hexdigest()
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            count=db.execute('SELECT count FROM studio_diagnostic_limits WHERE client=?',(client,)).fetchone()
            if count and count[0]>=20:raise HTTPException(429,'telemetry_limit')
            db.execute('DELETE FROM studio_diagnostic_limits WHERE bucket<?',(bucket-1,))
            db.execute('INSERT INTO studio_diagnostic_limits VALUES(?,?,1) ON CONFLICT(client) DO UPDATE SET count=count+1',(client,bucket))
            db.execute('INSERT INTO studio_diagnostics(request_id,created_at,route,method,status,elapsed_ms,code) VALUES(?,?,?,?,?,?,?)',(request.state.request_id,int(time.time()),payload.page,'CLIENT',0,0,f'{payload.kind}:{payload.name}:{payload.asset}:{payload.line}'))
            db.execute('DELETE FROM studio_diagnostics WHERE id NOT IN (SELECT id FROM studio_diagnostics ORDER BY id DESC LIMIT 2000)')
        return {'recorded':True}
    @app.middleware('http')
    async def monitor(request,call_next):
        ident=uuid.uuid4().hex[:16];request.state.request_id=ident
        request.state.error_code='';start=time.perf_counter();status=500
        try:
            response=await call_next(request);status=response.status_code
        except Exception as exc:
            # The exception class is sufficient for correlation; its message could
            # contain a signed source URL or submitted personal data.
            request.state.error_code=type(exc).__name__
            response=JSONResponse({'detail':'server_error'},status_code=500)
        elapsed=round((time.perf_counter()-start)*1000)
        code=re.sub(r'[^a-zA-Z0-9_\-]','',request.state.error_code)[:80]
        response.headers['X-Request-ID']=ident
        response.headers['Server-Timing']=f'app;dur={elapsed}'
        if not request.url.path.startswith('/studio-api/media/'):
            response.headers['Cache-Control']='no-store'
        if request.url.path.startswith('/studio-api/manage/') and not request.url.path.endswith('/diagnostics'):
            row={'request_id':ident,'route':route_name(request.url.path),'method':request.method,'status':status,'elapsed_ms':elapsed,'code':code}
            log.info('studio_request %s',json.dumps(row,separators=(',',':')))
            # Read-only routine polling is not persisted; retain mutations/failures.
            if request.method!='GET' or status>=400:
                try:
                    with database() as db:
                        db.execute('INSERT INTO studio_diagnostics(request_id,created_at,route,method,status,elapsed_ms,code) VALUES(?,?,?,?,?,?,?)',(ident,int(time.time()),row['route'],row['method'],status,elapsed,code))
                        db.execute('DELETE FROM studio_diagnostics WHERE id NOT IN (SELECT id FROM studio_diagnostics ORDER BY id DESC LIMIT 2000)')
                except Exception:
                    log.warning('studio_diagnostics_write_failed request_id=%s',ident)
        return response

    @app.get('/studio-api/manage/diagnostics')
    def diagnostics(_actor=Depends(admin_actor)):
        with database() as db:
            events=[dict(r) for r in db.execute('SELECT request_id,created_at,route,method,status,elapsed_ms,code FROM studio_diagnostics ORDER BY id DESC LIMIT 30')]
            db.execute('SELECT 1')
        return {'status':'ok','database':'ok','retained_events':2000,'events':events}
