import importlib.util
import json
import sqlite3
import time
import uuid
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("mac_bridge", Path(__file__).with_name("mac_sms_bridge.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

NUMBER = "+14165550123"
SENDER = "+16475550101"


class FakeApi:
    def __init__(self):
        self.calls = []
        self.fail = ""
        self.begin = True

    def call(self, path, body=None):
        self.calls.append((path, body))
        if self.fail and path.endswith(self.fail):
            raise mod.ApiError()
        return {"send": self.begin, "ok": True}


class FakeStore:
    records = []
    database_id = "same-database"

    def identity(self):
        return self.database_id

    def target(self, number, service="sms"):
        assert number == NUMBER
        return ["--chat-id", "9"]

    def batch(self, contact, cursor):
        self.cursor = cursor
        return self.records, 51


@pytest.fixture
def worker(tmp_path):
    api, store, commands = FakeApi(), FakeStore(), []
    def runner(args, **kwargs):
        commands.append(args)
        # Prove the durable journal is written before invoking the transport.
        with sqlite3.connect(tmp_path / "bridge.sqlite3") as db:
            assert db.execute("SELECT phase FROM dispatches").fetchone()[0] == "sending"
        return 0, '{"status":"sent"}', "", False
    instance = mod.Bridge({"sender": SENDER, "imsg": "/fake/imsg"}, tmp_path, store, api, runner)
    return instance, api, store, commands


def job(**values):
    return {"id": uuid.uuid4().hex, "recipient": NUMBER, "sender": SENDER, "content": "Local test only",
            "claim_token": "A" * 43, "expires_at": time.time() + 600, **values}


def test_submission_is_not_delivery_and_replayed_job_never_sends_twice(worker):
    instance, api, store, commands = worker
    item = job()
    instance.dispatch(item)
    instance.dispatch(item)
    assert len(commands) == 1 and commands[0][2:4] == ["--chat-id", "9"]
    assert api.calls[-1][1]["state"] == "submitted"


def test_lost_result_upload_is_replayed_without_repeating_sms(worker):
    instance, api, store, commands = worker
    item = job()
    api.fail = "/result"
    with pytest.raises(mod.ApiError):
        instance.dispatch(item)
    api.fail = ""
    instance.recover()
    instance.flush_results()
    instance.dispatch(item)
    assert len(commands) == 1
    assert api.calls[-1][1]["state"] == "submitted"


def test_ambiguous_begin_response_never_starts_a_physical_send(worker):
    instance, api, store, commands = worker
    api.fail = "/begin"
    with pytest.raises(mod.ApiError):
        instance.dispatch(job())
    assert not commands


def test_restart_after_transport_start_marks_unknown_without_replay(worker):
    instance, api, store, commands = worker
    item = job()
    with instance.db() as db:
        db.execute("INSERT INTO dispatches(id,job,phase,started_at) VALUES(?,?,'sending',?)", (item["id"], json.dumps(item), time.time()))
    instance.recover()
    instance.flush_results()
    instance.dispatch(item)
    assert not commands and api.calls[-1][1]["state"] == "unknown"


def test_expired_jobs_wrong_sender_and_declined_begin_do_not_send(worker):
    instance, api, store, commands = worker
    instance.dispatch(job(expires_at=1))
    instance.dispatch(job(sender=NUMBER))
    api.begin = False
    instance.dispatch(job())
    assert not commands


def test_upload_failure_preserves_checkpoint_and_database_replacement_resets_it(worker):
    instance, api, store, _ = worker
    store.records = [{"message": {"direction": "inbound", "external_id": "g1"}}]
    api.fail = "/messages"
    contact = {"id": "selected", "phone": NUMBER}
    with pytest.raises(mod.ApiError):
        instance.sync([contact])
    with instance.db() as db:
        assert not db.execute("SELECT * FROM checkpoints").fetchone()
    api.fail = ""
    instance.sync([contact])
    instance.sync([contact])
    assert store.cursor == 51
    store.database_id = "replacement"
    instance.sync([contact])
    assert store.cursor == 0


def test_echo_matches_one_job_and_checks_sender(worker):
    instance, _, _, _ = worker
    item = job()
    instance.dispatch(item)
    record = {"caller": SENDER, "message": {"direction": "outbound", "channel": "SMS", "timestamp": time.time(), "phone": NUMBER, "content": item["content"], "external_id": "mac-guid"}}
    instance.correlate(record)
    assert record["message"]["job_id"] == item["id"]
    record["caller"] = NUMBER
    record["message"].pop("job_id")
    instance.correlate(record)
    assert "job_id" not in record["message"] and instance.last_error == "sender_mismatch"


def test_reading_excludes_other_contacts_groups_old_messages_and_reactions(tmp_path):
    path = tmp_path / "chat.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
          CREATE TABLE chat(guid TEXT); CREATE TABLE handle(id TEXT);
          CREATE TABLE chat_handle_join(chat_id INTEGER,handle_id INTEGER);
          CREATE TABLE chat_message_join(chat_id INTEGER,message_id INTEGER);
          CREATE TABLE message(guid TEXT,service TEXT,is_from_me INTEGER,is_sent INTEGER,is_delivered INTEGER,error INTEGER,destination_caller_id TEXT,date REAL,associated_message_type INTEGER,balloon_bundle_id TEXT);
        """)
        db.executemany("INSERT INTO handle VALUES(?)", [(NUMBER,), ("+14165550999",)])
        db.executemany("INSERT INTO chat VALUES(?)", [("SMS;-;" + NUMBER,), ("SMS;+;group",), ("SMS;-;private",)])
        db.executemany("INSERT INTO chat_handle_join VALUES(?,?)", [(1,1), (2,1), (2,2), (3,2)])
        for index, (chat, stamp, reaction) in enumerate([(1,100,0), (1,200,0), (2,200,0), (3,200,0), (1,200,2000)], 1):
            db.execute("INSERT INTO message VALUES(?,?,?,?,?,?,?,?,?,?)", (f"guid-{index}", "SMS", 0, 0, 0, 0, SENDER, stamp, reaction, ""))
            db.execute("INSERT INTO chat_message_join VALUES(?,?)", (chat, index))
    calls = []
    def decode(args, **kwargs):
        calls.append(args)
        return 0, json.dumps({"id": 2, "text": "Selected business reply"}), "", False
    store = mod.MessageStore(path, "/fake/imsg", decode)
    records, cursor = store.batch({"id": "thread", "phone": NUMBER, "sync_since": 978307350}, 0)
    assert cursor == 2 and len(records) == 1
    assert records[0]["message"]["external_id"] == "guid-2"
    assert len(calls) == 1 and calls[0][calls[0].index("--chat-id")+1] == "1"


def test_config_rejects_redirect_hosts_roles_and_non_private_files(tmp_path):
    path = tmp_path / "config.json"
    value = {"server": "https://pindoupuppy.com.evil.invalid/studio-api/message-bridge", "token": "A"*43, "role": "customer", "user": "pindou_sms", "sender": SENDER, "allow_send": False}
    path.write_text(json.dumps(value)); path.chmod(0o600)
    with pytest.raises(ValueError):
        mod.load_config(path)
    value["server"] = "https://pindoupuppy.com/studio-api/message-bridge"
    path.write_text(json.dumps(value))
    assert mod.load_config(path)["sender"] == SENDER
