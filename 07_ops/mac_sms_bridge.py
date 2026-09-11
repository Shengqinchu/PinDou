"""Selected-contact Mac bridge using the upstream imsg CLI.

Run in the paired macOS user's local Terminal/GUI session. The server queues
business work; this process does not expose an HTTP listener or whole inbox.
Transport attempts and upload checkpoints survive restarts. Only unstarted
work can be retried; an ambiguous physical send is never repeated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


def normalize(value):
    value = re.sub(r"[\s().-]", "", str(value))
    if re.fullmatch(r"1[2-9]\d{2}[2-9]\d{6}", value):
        value = "+" + value
    if not re.fullmatch(r"\+1[2-9]\d{2}[2-9]\d{6}", value):
        raise ValueError("unsupported_phone")
    return value


def load_config(path):
    path = Path(path)
    if os.name != "nt" and path.stat().st_mode & 0o077:
        raise ValueError("private_config_required")
    value = json.loads(path.read_text(encoding="utf-8"))
    parsed = urlparse(value.get("server", ""))
    if parsed.scheme != "https" or parsed.netloc != "pindoupuppy.com" or parsed.path.rstrip("/") != "/studio-api/message-bridge" or parsed.query or parsed.fragment:
        raise ValueError("trusted_server_required")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", value.get("token", "")):
        raise ValueError("bridge_token_required")
    if value.get("role") not in ("customer", "owner_alert") or value.get("user") not in ("pindou_sms", "chix"):
        raise ValueError("bridge_role_required")
    if type(value.get("allow_send")) is not bool:
        raise ValueError("explicit_send_setting_required")
    value["sender"] = normalize(value["sender"])
    value["server"] = value["server"].rstrip("/")
    value.setdefault("imsg", "/usr/local/libexec/pindou-imsg/0.15.3/imsg")
    value.setdefault("service", "sms")
    if value["service"] not in ("sms", "imessage"):
        raise ValueError("explicit_message_service_required")
    if not PurePosixPath(value["imsg"]).is_absolute():
        raise ValueError("absolute_imsg_path_required")
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ApiError(Exception):
    def __init__(self, status=0):
        self.status = status
        super().__init__("bridge_api_unavailable")


class Api:
    def __init__(self, config):
        self.config = config
        self.opener = build_opener(NoRedirect())

    def call(self, path, body=None):
        request = Request(self.config["server"] + path,
            data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
            headers={"Authorization": "Bearer " + self.config["token"], "Content-Type": "application/json", "User-Agent": "PinDouMacBridge/1.0"})
        try:
            with self.opener.open(request, timeout=12) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError()
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except HTTPError as exc:
            raise ApiError(exc.code) from None
        except Exception:
            raise ApiError() from None


def command(arguments, timeout=40):
    """No shell. Bound and terminate the process group, including osascript."""
    process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            process.communicate()
        return -1, "", "", True


def iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class MessageStore:
    def __init__(self, path, imsg, runner=command):
        self.path, self.imsg, self.runner = Path(path), imsg, runner

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=3)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def identity(self):
        info = self.path.stat()
        return f"{info.st_dev}:{info.st_ino}"

    def accessible(self):
        try:
            with self.connect() as db:
                return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='message'").fetchone())
        except (OSError, sqlite3.Error):
            return False

    def chats(self, number):
        """Resolve only a selected number; exclude chats with other participants."""
        number = normalize(number)
        with self.connect() as db:
            rows = db.execute("""SELECT DISTINCT c.ROWID AS chat_id,c.guid FROM chat c
              JOIN chat_handle_join j ON j.chat_id=c.ROWID JOIN handle h ON h.ROWID=j.handle_id
              WHERE h.id IN (?,?) ORDER BY c.ROWID""", (number, number[1:])).fetchall()
            result = []
            for row in rows:
                values = db.execute("SELECT h.id FROM handle h JOIN chat_handle_join j ON j.handle_id=h.ROWID WHERE j.chat_id=?", (row["chat_id"],)).fetchall()
                if len(values) == 1 and str(values[0][0]).lstrip("+") == number[1:]:
                    result.append(dict(row))
            return result

    def target(self, number, service="sms"):
        chats = self.chats(number)
        prefix = "SMS;" if service == "sms" else "iMessage;"
        matching = [row for row in chats if row["guid"].startswith(prefix)]
        if matching:
            return ["--chat-guid", matching[-1]["guid"]]
        # The upstream CLI supports first-contact SMS through Messages.app.
        # This path remains separately subject to device acceptance testing.
        return ["--to", normalize(number)]

    def batch(self, contact, cursor):
        chats = self.chats(contact["phone"])
        if not chats:
            return [], cursor
        ids = [row["chat_id"] for row in chats]
        with self.connect() as db:
            columns = {r[1] for r in db.execute("PRAGMA table_info(message)")}
            predicates = []
            if "associated_message_type" in columns:
                predicates.append("COALESCE(m.associated_message_type,0)=0")
            if "balloon_bundle_id" in columns:
                predicates.append("COALESCE(m.balloon_bundle_id,'')!='com.apple.messages.URLBalloonProvider'")
            filters = " AND " + " AND ".join(predicates) if predicates else ""
            placeholders = ",".join("?" for _ in ids)
            rows = db.execute(f"""SELECT m.ROWID AS rowid,m.guid,m.service,m.is_from_me,m.is_sent,m.is_delivered,
              m.error,m.destination_caller_id,MIN(j.chat_id) AS chat_id,
              (CASE WHEN m.date>100000000000 THEN m.date/1000000000.0 ELSE m.date END)+978307200 AS stamp
              FROM message m JOIN chat_message_join j ON j.message_id=m.ROWID
              WHERE j.chat_id IN ({placeholders}) AND m.ROWID>? AND stamp>=? {filters}
              GROUP BY m.ROWID ORDER BY m.ROWID LIMIT 100""", (*ids, cursor, contact["sync_since"])).fetchall()
        if not rows:
            return [], cursor
        decoded = {}
        for chat_id in sorted({r["chat_id"] for r in rows}):
            subset = [r for r in rows if r["chat_id"] == chat_id]
            args = [self.imsg, "history", "--db", str(self.path), "--chat-id", str(chat_id), "--limit", "1000",
                    "--start", iso(min(r["stamp"] for r in subset) - 1), "--end", iso(max(r["stamp"] for r in subset) + 1), "--json"]
            code, output, _, timed_out = self.runner(args, timeout=15)
            if code or timed_out:
                raise ValueError("message_decode_unavailable")
            for line in output.splitlines():
                item = json.loads(line)
                if isinstance(item, dict) and isinstance(item.get("id"), int):
                    decoded[item["id"]] = item
        result = []
        for row in rows:
            item = decoded.get(row["rowid"])
            if not item:
                # A partially written row or bounded decode gap must not move
                # the checkpoint past an unread message.
                raise ValueError("message_decode_incomplete")
            body = item.get("text", "")
            if not isinstance(body, str):
                raise ValueError("message_decode_invalid")
            if not body.strip():
                if item.get("attachments"):
                    body = contact.get("attachment_placeholder", "[Attachment: view on phone]")
                else:
                    continue
            if row["service"] not in ("SMS", "iMessage", "RCS"):
                continue
            result.append({"rowid": row["rowid"], "caller": row["destination_caller_id"] or "", "message": {
                "thread_id": contact["id"], "external_id": row["guid"], "phone": contact["phone"],
                "direction": "outbound" if row["is_from_me"] else "inbound", "channel": row["service"],
                "content": body[:4000], "timestamp": row["stamp"], "sent": bool(row["is_sent"]),
                "delivered": bool(row["is_delivered"]), "error": bool(row["error"])}})
        return result, rows[-1]["rowid"]

    def find_sent(self, job, started):
        records, _ = self.batch({"id": "", "phone": job["recipient"], "sync_since": started - 3}, 0)
        matches = [r for r in records if r["message"]["direction"] == "outbound"
                   and r["message"]["content"] == job["content"] and r["message"]["timestamp"] <= started + 180]
        return matches[0] if len(matches) == 1 else None


class Bridge:
    def __init__(self, config, directory, store=None, api=None, runner=command):
        self.config, self.directory, self.runner = config, Path(directory), runner
        self.directory.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            os.chmod(self.directory, 0o700)
        self.api = api or Api(config)
        self.store = store or MessageStore(Path.home() / "Library/Messages/chat.db", config["imsg"], runner)
        self.state_path = self.directory / "bridge.sqlite3"
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checkpoints (thread_id TEXT PRIMARY KEY,rowid_value INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS dispatches (id TEXT PRIMARY KEY,job TEXT NOT NULL,phase TEXT NOT NULL,
              started_at REAL NOT NULL DEFAULT 0,finished_at REAL NOT NULL DEFAULT 0,result TEXT NOT NULL DEFAULT '',
              guid TEXT NOT NULL DEFAULT '');
            """)
        if os.name != "nt":
            os.chmod(self.state_path, 0o600)
        self.last_automation_check = 0
        self.automation = False
        self.last_error = ""
        self.last_observe = 0
        self.last_receipts = 0

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.state_path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover(self):
        with self.db() as db:
            for row in db.execute("SELECT * FROM dispatches WHERE phase='sending'").fetchall():
                job = json.loads(row["job"])
                result = {"claim_token": job["claim_token"], "state": "unknown", "error": "interrupted", "external_id": ""}
                db.execute("UPDATE dispatches SET phase='result',result=?,finished_at=? WHERE id=?", (json.dumps(result), time.time(), row["id"]))

    def flush_results(self):
        with self.db() as db:
            rows = db.execute("SELECT * FROM dispatches WHERE phase='result' ORDER BY started_at LIMIT 10").fetchall()
        for row in rows:
            try:
                self.api.call("/jobs/" + row["id"] + "/result", json.loads(row["result"]))
            except ApiError as error:
                if error.status not in (404, 409):
                    raise
                phase = "needs_review"
            else:
                phase = "acknowledged"
            with self.db() as db:
                db.execute("UPDATE dispatches SET phase=? WHERE id=?", (phase, row["id"]))

    def correlate(self, record):
        message = record["message"]
        if message["direction"] != "outbound":
            return
        caller = str(record.get("caller", "")).lstrip("+")
        if message["channel"] == "SMS" and caller and caller != self.config["sender"][1:]:
            self.last_error = "sender_mismatch"
            return
        with self.db() as db:
            candidates = []
            for row in db.execute("SELECT * FROM dispatches WHERE started_at BETWEEN ? AND ?",
                                  (message["timestamp"] - 180, message["timestamp"] + 3)):
                job = json.loads(row["job"])
                if job["recipient"] == message["phone"] and job["content"] == message["content"] and (not row["guid"] or row["guid"] == message["external_id"]):
                    candidates.append(row)
            # Ambiguous matching must never merge two separately sent texts.
            if len(candidates) == 1:
                row = candidates[0]
                db.execute("UPDATE dispatches SET guid=? WHERE id=?", (message["external_id"], row["id"]))
                message["job_id"] = row["id"]

    def sync(self, contacts):
        identity = self.store.identity()
        with self.db() as db:
            previous = db.execute("SELECT value FROM metadata WHERE name='message_store'").fetchone()
            if previous and previous[0] != identity:
                db.execute("DELETE FROM checkpoints")
            db.execute("INSERT OR REPLACE INTO metadata VALUES('message_store',?)", (identity,))
        refresh_receipts = time.monotonic() - self.last_receipts > 30
        if refresh_receipts:
            self.last_receipts = time.monotonic()
        for contact in contacts:
            with self.db() as db:
                row = db.execute("SELECT rowid_value FROM checkpoints WHERE thread_id=?", (contact["id"],)).fetchone()
            records, checkpoint = self.store.batch(contact, row[0] if row else 0)
            if refresh_receipts and row:
                # Revisit recent rows because delivery/error flags can change
                # without adding a new message row. Upload remains GUID-idempotent.
                recent, _ = self.store.batch({**contact, "sync_since": max(contact["sync_since"], time.time() - 300)}, 0)
                records = list({r["message"]["external_id"]: r for r in [*records, *recent]}.values())
            for record in records:
                self.correlate(record)
            for start in range(0, len(records), 10):
                self.api.call("/messages", {"messages": [r["message"] for r in records[start:start + 10]]})
            # A failed upload leaves the checkpoint untouched; GUID deduplication
            # makes a subsequent replay harmless, including after a restart.
            with self.db() as db:
                db.execute("INSERT OR REPLACE INTO checkpoints VALUES(?,?)", (contact["id"], checkpoint))

    def readiness(self):
        readable = self.store.accessible()
        if not readable:
            self.automation = False
            self.last_error = "permission_required"
        elif time.monotonic() - self.last_automation_check > 60:
            self.last_automation_check = time.monotonic()
            # This checks Apple Events permission without enumerating accounts
            # or private conversations. Actual SMS outcome is checked separately.
            code, output, _, expired = self.runner(["/usr/bin/osascript", "-e",
                'tell application id "com.apple.MobileSMS" to return version'], timeout=8)
            self.automation = not code and not expired and bool(output.strip())
            if self.last_error != "sender_mismatch":
                self.last_error = "" if self.automation else "account_unavailable"
        self.api.call("/heartbeat", {"readable": readable, "automation": self.automation,
            "sender": self.config["sender"], "version": "1.0/imsg-0.15.3", "error": self.last_error})
        return readable and self.automation and not self.last_error

    def observe_dispatches(self):
        if time.monotonic() - self.last_observe < 20:
            return
        self.last_observe = time.monotonic()
        with self.db() as db:
            rows = db.execute("SELECT * FROM dispatches WHERE phase IN ('acknowledged','observed','needs_review') AND started_at>? ORDER BY started_at DESC LIMIT 50", (time.time() - 86400,)).fetchall()
        for row in rows:
            job = json.loads(row["job"])
            found = self.store.find_sent(job, row["started_at"])
            if not found:
                continue
            try:
                caller = normalize(found["caller"])
            except ValueError:
                continue
            if caller != self.config["sender"]:
                self.last_error = "sender_mismatch"
                continue
            message = found["message"]
            state = "failed" if message["error"] else "delivered" if message["delivered"] else "sent" if message["sent"] else ""
            if not state:
                continue
            self.api.call("/jobs/" + row["id"] + "/observation", {"claim_token": job["claim_token"], "external_id": message["external_id"], "sender": caller, "channel": message["channel"], "state": state})
            with self.db() as db:
                db.execute("UPDATE dispatches SET phase='observed',guid=? WHERE id=?", (message["external_id"], row["id"]))

    def dispatch(self, job):
        if normalize(job["sender"]) != self.config["sender"]:
            self.last_error = "sender_mismatch"
            return
        recipient = normalize(job["recipient"])
        if not re.fullmatch(r"[a-f0-9]{32}", job["id"]) or not isinstance(job["content"], str) or not 0 < len(job["content"]) <= 2000:
            raise ValueError("invalid_job")
        if job["expires_at"] <= time.time():
            return
        with self.db() as db:
            prior = db.execute("SELECT phase FROM dispatches WHERE id=?", (job["id"],)).fetchone()
            if prior and prior[0] != "prepared":
                return
            db.execute("INSERT OR REPLACE INTO dispatches(id,job,phase) VALUES(?,?,'prepared')", (job["id"], json.dumps(job)))
        # Resolve before beginning. Database errors cannot become send attempts.
        service = self.config.get("service", "sms")
        target = self.store.target(recipient, service)
        begin = self.api.call("/jobs/" + job["id"] + "/begin", {"claim_token": job["claim_token"]})
        if not begin.get("send"):
            with self.db() as db:
                db.execute("UPDATE dispatches SET phase='not_started' WHERE id=?", (job["id"],))
            return
        started = time.time()
        with self.db() as db:
            db.execute("UPDATE dispatches SET phase='sending',started_at=? WHERE id=?", (started, job["id"]))
        # The durable 'sending' record must exist before any physical side effect.
        try:
            code, _, _, expired = self.runner([self.config["imsg"], "send", *target,
                "--text", job["content"], "--service", service, "--no-sms-fallback", "--json"], timeout=40)
            state, error = ("unknown", "send_timeout") if expired else (("unknown", "send_rejected") if code else ("submitted", ""))
        except OSError:
            state, error = "failed", "transport_unavailable"
        except Exception:
            state, error = "unknown", "interrupted"
        result = {"claim_token": job["claim_token"], "state": state, "error": error, "external_id": ""}
        with self.db() as db:
            db.execute("UPDATE dispatches SET phase='result',finished_at=?,result=? WHERE id=?", (time.time(), json.dumps(result), job["id"]))
        self.flush_results()

    def cycle(self):
        self.flush_results()
        contacts = self.api.call("/contacts")
        if contacts["role"] != self.config["role"] or normalize(contacts["sender"]) != self.config["sender"]:
            self.last_error = "sender_mismatch"
            raise ValueError("sender_mismatch")
        ready = self.readiness()
        if self.store.accessible():
            self.observe_dispatches()
            if self.config["role"] == "customer":
                self.sync(contacts["items"])
        if ready and not self.last_error and self.config["allow_send"] and contacts["send_enabled"]:
            job = self.api.call("/claim", {}).get("job")
            if job:
                self.dispatch(job)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This bridge runs only in the paired macOS user session.")
    import fcntl
    import pwd
    config = load_config(args.config)
    if pwd.getpwuid(os.getuid()).pw_name != config["user"] or str(Path.home()) != "/Users/" + config["user"]:
        parser.error("Wrong macOS user; refusing to use another account's Messages.")
    directory = args.config.resolve().parent
    os.umask(0o077)
    with (directory / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        bridge = Bridge(config, directory)
        bridge.recover()
        failures = 0
        while True:
            try:
                latest = load_config(args.config)
                if any(latest[k] != config[k] for k in ("user", "role", "sender", "imsg")):
                    raise ValueError("paired_configuration_changed")
                config.update(latest)
                bridge.cycle()
                failures = 0
                status = {"ok": True, "error": bridge.last_error}
            except Exception as exc:
                failures += 1
                # Never log tokens, telephone numbers, message content or command
                # output. This small status file is for the local service guard.
                status = {"ok": False, "error": "api_unavailable" if isinstance(exc, ApiError) else "local_unavailable"}
            status.update({"checked_at": time.time(), "pid": os.getpid(), "user": config["user"]})
            temporary = directory / "status.next.json"
            temporary.write_text(json.dumps(status), encoding="utf-8")
            temporary.replace(directory / "status.json")
            if args.once:
                return 0 if status["ok"] else 1
            time.sleep(min(60, 5 * 2 ** min(failures, 4)))


if __name__ == "__main__":
    raise SystemExit(main())
