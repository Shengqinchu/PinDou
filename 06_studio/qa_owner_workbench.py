"""Loopback-only UI fixtures, with fictional contacts and no live deliveries."""
import json
import time
import uuid
import uvicorn
import qa_messaging
import app as studio
import studio_finance as finance
from datetime import datetime
from zoneinfo import ZoneInfo

stamp=datetime.now(ZoneInfo('America/Toronto'));today=stamp.date().isoformat()
with studio.database() as db:
    for index,status in enumerate(['pending','confirmed','completed']):
        ident='VIS-LOCAL-WORKSPACE-'+str(index)
        payload={'name':'Local customer '+str(index),'contact_method':'phone','contact':'+14165550123',
            'notes':'Local QA booking','booking':{'date':today,'start':'14:00','end':'16:00','guests':2,'plan':'hourly'}}
        db.execute('''INSERT INTO studio_reservations(id,created_at,updated_at,status,payload,visitor_hash,idempotency_key,payload_hash,owner_id)
          VALUES(?,?,?,?,?,?,?,?,?)''',(ident,stamp.isoformat(),stamp.isoformat(),status,json.dumps(payload),'local',str(uuid.uuid4()),'local','qa-owner'))
        if status=='completed':finance.from_completed(db,db.execute('SELECT * FROM studio_reservations WHERE id=?',(ident,)).fetchone(),'qa')
    db.execute("INSERT OR IGNORE INTO studio_members(owner_id,name,email,created_at,updated_at) VALUES('qa-owner','Local customer','qa@example.test',?,?)",(stamp.isoformat(),stamp.isoformat()))
    db.execute("UPDATE studio_members SET staff_note='Preserve this private note' WHERE owner_id='qa-owner'")
    db.execute("INSERT OR IGNORE INTO studio_staff_accounts VALUES('qa-owner','admin',1,'Local admin',?,?,?)",(time.time(),time.time(),'qa'))

if __name__=='__main__':uvicorn.run(studio.app,host='127.0.0.1',port=8011,access_log=False)
