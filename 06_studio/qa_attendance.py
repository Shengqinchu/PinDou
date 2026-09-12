"""Disposable attendance UI QA; loopback only, never packaged for production."""
import json, uuid
from datetime import datetime
import qa_owner_workbench
import app as studio, reservations, wallet, uvicorn
reservations.now_local=lambda:datetime(2026,9,12,9,0,tzinfo=reservations.ZONE)
wallet.now=lambda:'2026-09-13T18:00:00-04:00'

@studio.app.post('/studio-api/qa/completion-seed')
def seed():
    ident='VIS-LOCAL-COMPLETION-'+uuid.uuid4().hex[:12]
    stamp=reservations.now_local().isoformat()
    payload={'name':'Local attendance QA','contact_method':'wechat','contact':'local-qa',
        'booking':{'date':'2026-09-12','start':'14:00','end':'16:00','plan':'hourly','guests':2}}
    with studio.database() as db:
        db.execute('''INSERT INTO studio_reservations(id,created_at,updated_at,status,payload,
          visitor_hash,idempotency_key,payload_hash,owner_id,actual_minutes)
          VALUES(?,?,?,?,?,?,?,?,?,?)''',(ident,stamp,stamp,'pending',json.dumps(payload),'qa',str(uuid.uuid4()),'qa','qa-owner',0))
    return {'id':ident}

if __name__=='__main__':uvicorn.run(studio.app,host='127.0.0.1',port=8011,access_log=False)
