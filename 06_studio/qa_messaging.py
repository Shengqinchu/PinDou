"""Isolated loopback QA for the messaging UI. Never packaged or deployed."""
import time

import uvicorn
import qa_server
import app as studio
import sms_inbox as sms

sms.configure_bridge(studio.database, role="customer", sender="+14165550100", token="A"*43, enabled=True, send_enabled=True)
sms.configure_bridge(studio.database, role="owner_alert", sender="+16475550101", token="B"*43, enabled=True, send_enabled=True)
with studio.database() as db:
    db.execute("UPDATE studio_sms_bridges SET last_seen=?,health=?", (time.time(), '{"readable":true,"automation":true,"error":""}'))
    bridge = db.execute("SELECT * FROM studio_sms_bridges WHERE role='customer'").fetchone()
    for name, number, text in [("本地测试顾客", "+14165550123", "你好，可以提前十分钟到吗？"), ("Local QA", "+14165550124", "Thank you! This is a local UI test.")]:
        thread = sms.ensure_thread(db, number, name)
        sms.ingest(db, bridge, sms.IncomingMessage(thread_id=thread["id"], external_id="local-"+number[-4:], phone=number,
            direction="inbound", channel="SMS" if number.endswith("123") else "iMessage", content=text, timestamp=time.time()))

if __name__ == "__main__":
    uvicorn.run(studio.app, host="127.0.0.1", port=8011, access_log=False)
