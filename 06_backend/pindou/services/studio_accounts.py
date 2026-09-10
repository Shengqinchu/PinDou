"""Account operations available only through the authenticated Studio bridge.

Recovery codes have their own purpose-specific table. They cannot be redeemed
by the generator's legacy email-login endpoints or used to create an account.
"""
import asyncio,hashlib,hmac,os,secrets,time
import requests
from sqlalchemy import select,text,func,or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pindou.config import get_settings
from pindou.db.models import User
from pindou.services.password_auth import hash_password
from pindou.services.rate_limit_service import consume_rate_limits,RateLimitRule,RateLimitExceeded


def wechat_account(db:Session,key:str):
    from pindou.services.user_service import UserService
    return UserService(db).register_or_login(openid='wechat_authing_'+key)


def password_account(db:Session,email:str,password:str,ip:str):
    from pindou.services.email_verification import validate_email_or_raise
    from pindou.services.user_service import email_openid
    from pindou.services.credit_service import grant_registration_gift
    email=validate_email_or_raise(email)
    try:
        consume_rate_limits(db,[RateLimitRule('studio_register:ip:minute',ip,limit=3,window_seconds=60),
            RateLimitRule('studio_register:ip:day',ip,limit=30,window_seconds=86400),
            RateLimitRule('studio_register:global:hour','all',limit=100,window_seconds=3600)])
    except RateLimitExceeded:return {'error':'account_rate_limited'}
    # These addresses carry generator entitlements and require an existing,
    # verified account. Unverified public registration must not claim them.
    if email in get_settings().unlimited_credit_email_set:
        return {'error':'account_already_registered'}
    openid=email_openid(email)
    digest=hash_password(password)
    db.execute(text('BEGIN IMMEDIATE'))
    # Never reuse the legacy "register or complete password" operation: it
    # may overwrite the password of an existing account after email proof.
    existing=db.scalar(select(User).where(or_(func.lower(User.email)==email,User.openid==openid)))
    if existing is not None:
        db.rollback();return {'error':'account_already_registered'}
    try:
        user=User(openid=openid,email=email,password_hash=digest,nickname=email.split('@',1)[0][:32],avatar='')
        db.add(user);db.flush();grant_registration_gift(db,user);db.commit();db.refresh(user)
        return user
    except IntegrityError:
        db.rollback();return {'error':'account_already_registered'}


def code_hash(email,code):
    return hmac.new(os.environ['PINDOU_STUDIO_AUTH_BRIDGE_KEY'].encode(),f'password-recovery:{email}:{code}'.encode(),hashlib.sha256).hexdigest()


def table(db):
    db.execute(text('''CREATE TABLE IF NOT EXISTS studio_recovery_codes (
      email TEXT PRIMARY KEY,code_hash TEXT NOT NULL,sent_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,used INTEGER NOT NULL DEFAULT 0)'''))


def deliver_recovery(email,code):
    settings=get_settings()
    key=settings.resend_api_key.get_secret_value() if settings.resend_api_key else ''
    if not key:return False
    try:
        response=requests.post('https://api.resend.com/emails',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},
            json={'from':f'{settings.sender_name} <{settings.sender_email}>','to':[email],
                'subject':'小狗拼豆铺 · 找回账号 / Reset your password',
                'text':f'找回账号验证码：{code}，5 分钟内有效，仅用于重设密码。\nPassword reset code: {code}. Valid for 5 minutes, for password recovery only.\n如非本人操作，请忽略本邮件。If you did not request this, ignore this email.'},timeout=10)
        return 200<=response.status_code<300
    except requests.RequestException:return False


async def send_recovery(db,email,ip):
    from pindou.services.email_verification import validate_email_or_raise
    email=validate_email_or_raise(email)
    try:
        consume_rate_limits(db,[RateLimitRule('studio_recovery:ip:minute',ip,limit=3,window_seconds=60),
            RateLimitRule('studio_recovery:ip:day',ip,limit=15,window_seconds=86400),
            RateLimitRule('studio_recovery:email:hour',email,limit=5,window_seconds=3600),
            RateLimitRule('studio_recovery:global:hour','all',limit=100,window_seconds=3600)])
    except RateLimitExceeded:return {'error':'account_rate_limited'}
    result={'success':True,'cooldown_seconds':60,'expires_in_seconds':300}
    user=db.scalar(select(User).where(User.email==email))
    # Do not send mail to unknown addresses, and do not reveal account existence.
    if user is None:return result
    table(db);db.commit();db.execute(text('BEGIN IMMEDIATE'));now=int(time.time())
    record=db.execute(text('SELECT sent_at FROM studio_recovery_codes WHERE email=:email'),{'email':email}).first()
    if record and now-record.sent_at<60:
        db.rollback();return {'error':'account_rate_limited'}
    code=f'{secrets.randbelow(1000000):06d}';digest=code_hash(email,code)
    db.execute(text('INSERT INTO studio_recovery_codes(email,code_hash,sent_at,expires_at) VALUES(:email,:hash,:now,:exp) ON CONFLICT(email) DO UPDATE SET code_hash=:hash,sent_at=:now,expires_at=:exp,attempts=0,used=0'),
        {'email':email,'hash':digest,'now':now,'exp':now+300})
    db.commit()
    if not await asyncio.to_thread(deliver_recovery,email,code):
        db.execute(text('DELETE FROM studio_recovery_codes WHERE email=:email AND code_hash=:hash'),{'email':email,'hash':digest});db.commit()
        return {'error':'account_email_unavailable'}
    return result


def reset_password(db,email,code,password):
    from pindou.services.email_verification import validate_email_or_raise
    email=validate_email_or_raise(email);table(db);db.commit()
    # A write lock covers attempt counting, single-use consumption and password
    # replacement so concurrent submissions cannot redeem one code twice.
    db.execute(text('BEGIN IMMEDIATE'))
    record=db.execute(text('SELECT * FROM studio_recovery_codes WHERE email=:email'),{'email':email}).mappings().first()
    user=db.scalar(select(User).where(User.email==email))
    if not record or not user or record['used'] or record['attempts']>=5:
        db.rollback();return {'error':'account_code_invalid'}
    if record['expires_at']<=int(time.time()):
        db.rollback();return {'error':'account_code_expired'}
    if not hmac.compare_digest(record['code_hash'],code_hash(email,code)):
        db.execute(text('UPDATE studio_recovery_codes SET attempts=attempts+1 WHERE email=:email'),{'email':email});db.commit()
        return {'error':'account_code_invalid'}
    user.password_hash=hash_password(password)
    db.execute(text('UPDATE studio_recovery_codes SET used=1,code_hash=\'\' WHERE email=:email'),{'email':email})
    db.commit()
    return {'success':True}
