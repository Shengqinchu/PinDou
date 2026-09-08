"""Local tests only; never included in a production release."""
import hashlib
import io
from urllib.error import HTTPError
from fastapi import HTTPException
profiles={}

def reject_legacy_admin(req,**kwargs):
    raise HTTPError(req.full_url,401,'Local user is not an admin',{},io.BytesIO(b'{}'))

def fake_upstream(path,request,body=None,token=""):
    if path=="email/send-code":return {"cooldown_seconds":60}
    if path=="profile":
        if token not in ("qa-owner","qa-other") and not token.startswith("qa-email-"):
            raise HTTPException(401,"account_login_required")
        email=token+"@example.test"
    else:
        if body.get("code","123456")!="123456":raise HTTPException(400,"account_code_invalid")
        if path=="email-login" and body["password"]!="local-password":raise HTTPException(401,"account_password_invalid")
        token="qa-email-"+hashlib.sha256(body['email'].encode()).hexdigest()[:12]
        email=body['email']
    user=profiles.get(token) or {"user_id":token,"email":email,"nickname":"Local QA"}
    profiles[token]=user
    return user if path=="profile" else {"token":token,"user":user}
