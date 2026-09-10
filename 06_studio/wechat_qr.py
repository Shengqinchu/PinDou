"""Same-page WeChat QR login using Authing's documented WXAPP_AUTH API.

Only the server generates QR IDs, polls them and exchanges their tickets. The
browser supplies our cookie-bound state, never a provider ticket or identity.
The OIDC callback remains available for already-started hosted-page logins.
"""
import json,re,secrets,time
from urllib.parse import urlencode,urlsplit
from fastapi import HTTPException,Request,Response
import authing_login as auth
from customer_auth import limit,require_customer


def provider(path,body=None):
    c=auth.config();host=urlsplit(c.issuer)
    result=auth.fetch_json(f'{host.scheme}://{host.netloc}/api/v2/qrcode/'+path,body,
        {'x-authing-app-id':c.app_id,'x-authing-request-from':'sdk'})
    if result.get('code')!=200 or not isinstance(result.get('data'),dict):
        raise HTTPException(503,'wechat_provider_unavailable')
    return result['data']


def image_url(value):
    if not isinstance(value,str) or len(value)>2000:raise HTTPException(503,'wechat_provider_unavailable')
    url=urlsplit(value)
    if (url.scheme!='https' or url.username or url.password or url.port not in (None,443)
        or not url.hostname or not url.hostname.endswith(('.authing.cn','.authing.co'))):
        raise HTTPException(503,'wechat_provider_unavailable')
    return value


def accept_identity(database,row,subject):
    c=auth.config()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        binding=db.execute('SELECT user_id FROM studio_auth_identities WHERE issuer=? AND app_id=? AND subject=?',(c.issuer,c.app_id,subject)).fetchone()
        if row['link_user']:
            existing=db.execute('SELECT user_id,subject FROM studio_auth_identities WHERE issuer=? AND app_id=? AND (subject=? OR user_id=?)',(c.issuer,c.app_id,subject,row['link_user'])).fetchall()
            if any(b['user_id']!=row['link_user'] or b['subject']!=subject for b in existing):raise HTTPException(409,'wechat_binding_conflict')
            db.execute('INSERT OR IGNORE INTO studio_auth_identities VALUES(?,?,?,?,?)',(c.issuer,c.app_id,subject,row['link_user'],int(time.time())))
            db.execute("UPDATE studio_oauth_flows SET status='linked',subject=?,bound_user=? WHERE state_hash=?",(subject,row['link_user'],row['state_hash']))
            return
    session=auth.shared_session(binding['user_id']) if binding else None
    with database() as db:
        db.execute('UPDATE studio_oauth_flows SET status=?,subject=?,result=? WHERE state_hash=?',
            ('ready' if session else 'needs_email',subject,json.dumps(session) if session else '',row['state_hash']))


def initialize(database):
    with database() as db:
        columns={r[1] for r in db.execute('PRAGMA table_info(studio_oauth_flows)')}
        for name,definition in [('qr_id',"TEXT NOT NULL DEFAULT ''"),('poll_after','REAL NOT NULL DEFAULT 0')]:
            if name not in columns:db.execute(f'ALTER TABLE studio_oauth_flows ADD COLUMN {name} {definition}')


def register(app,database):
    @app.post('/studio-api/auth/wechat/qr/start')
    def start(payload:auth.Start,request:Request,response:Response):
        if not auth.available():raise HTTPException(503,'wechat_not_configured')
        origin=auth.same_origin(request);target=auth.safe_return(payload.return_to)
        user=require_customer(request,request.headers.get('authorization'))['id'] if payload.mode=='link' else ''
        limit(request,'wechat-qr-start',12,600)
        data=provider('gene',{'scene':'WXAPP_AUTH','autoMergeQrCode':False})
        qr=data.get('random');url=image_url(data.get('url'))
        if not isinstance(qr,str) or not re.fullmatch(r'[A-Za-z0-9_-]{6,160}',qr):raise HTTPException(503,'wechat_provider_unavailable')
        cookie=request.cookies.get(auth.COOKIE,'')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',cookie):cookie=secrets.token_urlsafe(32)
        state=secrets.token_urlsafe(32);now=int(time.time())
        with database() as db:
            db.execute('DELETE FROM studio_oauth_flows WHERE expires_at<?',(now,))
            db.execute("INSERT INTO studio_oauth_flows(state_hash,browser_hash,nonce,verifier,origin,return_to,created_at,expires_at,status,link_user,qr_id) VALUES(?,?,'','',?,?,?,?,?,?,?)",
                (auth.digest(state),auth.digest(cookie),origin,target,now,now+auth.FLOW_LIFETIME,'qr_pending',user,qr))
        response.set_cookie(auth.COOKIE,cookie,max_age=auth.FLOW_LIFETIME,httponly=True,secure=auth.config().secure,samesite='lax',path='/studio-api/auth/wechat')
        response.headers['Cache-Control']='no-store'
        return {'state':state,'image':url,'expires_in':120}

    @app.post('/studio-api/auth/wechat/qr/poll')
    def poll(payload:auth.FlowAction,request:Request):
        auth.same_origin(request)
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=auth.flow_for(db,payload.state,request)
            if row['status'] not in ('qr_pending','qr_scanned'):
                return {'status':row['status'],'error':row['error']}
            if time.time()-row['created_at']>120:
                db.execute("UPDATE studio_oauth_flows SET status='failed',error='wechat_flow_expired',qr_id='' WHERE state_hash=?",(row['state_hash'],))
                return {'status':'failed','error':'wechat_flow_expired'}
            if row['poll_after']>time.time():return {'status':row['status']}
            db.execute('UPDATE studio_oauth_flows SET poll_after=? WHERE state_hash=?',(time.time()+1.5,row['state_hash']))
        data=provider('check?'+urlencode({'random':row['qr_id']}))
        if data.get('random')!=row['qr_id']:raise HTTPException(400,'wechat_identity_invalid')
        status=data.get('status')
        if status in (0,1):
            state='qr_scanned' if status==1 else 'qr_pending'
            with database() as db:db.execute("UPDATE studio_oauth_flows SET status=? WHERE state_hash=? AND status IN ('qr_pending','qr_scanned')",(state,row['state_hash']))
            return {'status':state}
        if status==2:
            with database() as db:
                db.execute('BEGIN IMMEDIATE')
                if not db.execute("UPDATE studio_oauth_flows SET status='qr_exchanging' WHERE state_hash=? AND status IN ('qr_pending','qr_scanned')",(row['state_hash'],)).rowcount:
                    return {'status':'qr_exchanging'}
            try:
                ticket=data.get('ticket')
                if not isinstance(ticket,str) or not 1<=len(ticket)<=2048:raise HTTPException(400,'wechat_identity_invalid')
                identity=provider('userinfo',{'ticket':ticket})
                subject=identity.get('id')
                # This is a server-to-server response from the fixed app host
                # to the ticket obtained by polling our own QR ID, not a claim
                # or profile accepted from the browser.
                if not isinstance(subject,str) or not re.fullmatch(r'[a-fA-F0-9]{24}',subject):raise HTTPException(400,'wechat_identity_invalid')
                if identity.get('blocked') or identity.get('status')=='Suspended':raise HTTPException(400,'wechat_identity_invalid')
                accept_identity(database,row,subject)
            except HTTPException as exc:
                with database() as db:db.execute("UPDATE studio_oauth_flows SET status='failed',error=? WHERE state_hash=?",(str(exc.detail),row['state_hash']))
            finally:
                with database() as db:db.execute("UPDATE studio_oauth_flows SET qr_id='' WHERE state_hash=?",(row['state_hash'],))
            with database() as db:
                final=auth.flow_for(db,payload.state,request)
                return {'status':final['status'],'error':final['error']}
        error='wechat_cancelled' if status==3 else 'wechat_flow_expired'
        with database() as db:db.execute("UPDATE studio_oauth_flows SET status='failed',error=?,qr_id='' WHERE state_hash=?",(error,row['state_hash']))
        return {'status':'failed','error':error}

    @app.post('/studio-api/auth/wechat/create-account')
    def create_account(payload:auth.FlowAction,request:Request):
        auth.same_origin(request);limit(request,'wechat-create',6,600);c=auth.config()
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=auth.flow_for(db,payload.state,request)
            if row['status']!='needs_email' or not row['subject'] or row['link_user']:raise HTTPException(409,'wechat_flow_used')
            existing=db.execute('SELECT user_id FROM studio_auth_identities WHERE issuer=? AND app_id=? AND subject=?',(c.issuer,c.app_id,row['subject'])).fetchone()
            if existing:raise HTTPException(409,'wechat_binding_conflict')
            # The shared backend creates only this deterministic WeChat identity.
            # Retrying a lost response cannot create a second account or gift.
            subject_key=auth.digest(c.issuer+'|'+c.app_id+'|'+row['subject'])
            result=auth.account_action('wechat_create',subject_key=subject_key)
            user=result['user'];expected='wechat_authing_'+subject_key
            if user.get('id')!=expected:raise HTTPException(400,'wechat_identity_invalid')
            db.execute('INSERT INTO studio_auth_identities VALUES(?,?,?,?,?)',(c.issuer,c.app_id,row['subject'],expected,int(time.time())))
            db.execute("UPDATE studio_oauth_flows SET status='ready',result=? WHERE state_hash=?",(json.dumps(result),row['state_hash']))
        return {'status':'ready'}
