import time
import uuid

import pytest

import app as studio
import sms_inbox as sms
from test_owner_notifications import setup, host

CUSTOMER_TOKEN = "A" * 43
OWNER_TOKEN = "B" * 43
CUSTOMER_NUMBER = "+14165550123"
STUDIO_NUMBER = "+14165550100"


def bridge(role="customer", **kwargs):
    sms.configure_bridge(studio.database, role=role,
        sender=STUDIO_NUMBER if role == "customer" else "+16475550101",
        token=CUSTOMER_TOKEN if role == "customer" else OWNER_TOKEN,
        enabled=True, send_enabled=True, **kwargs)


def auth(role="customer"):
    return {"Authorization": "Bearer " + (CUSTOMER_TOKEN if role == "customer" else OWNER_TOKEN)}


def thread(client, number=CUSTOMER_NUMBER):
    host()
    response = client.post("/studio-api/manage/messages/threads", json={"phone": number, "name": "Local customer"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def send(client, ident, key=None, content="Local test draft"):
    return client.post(f"/studio-api/manage/messages/threads/{ident}/messages",
        json={"request_id": key or str(uuid.uuid4()), "content": content})


def incoming(ident, guid="local-message-1", **kwargs):
    return {"thread_id": ident, "phone": CUSTOMER_NUMBER, "external_id": guid, "direction": "inbound",
            "channel": "SMS", "content": "Local test reply", "timestamp": time.time(), **kwargs}


def ingest(client, item, role="customer"):
    return client.post("/studio-api/message-bridge/messages", headers=auth(role), json={"messages": [item]})


def claim(client, role="customer"):
    return client.post("/studio-api/message-bridge/claim", headers=auth(role)).json()["job"]


def begin(client, job, role="customer"):
    return client.post(f"/studio-api/message-bridge/jobs/{job['id']}/begin", headers=auth(role), json={"claim_token": job["claim_token"]})


def result(client, job, **kwargs):
    return client.post(f"/studio-api/message-bridge/jobs/{job['id']}/result", headers=auth(),
                       json={"claim_token": job["claim_token"], "state": "submitted", **kwargs})


def test_admin_and_bridge_credentials_are_separate(setup):
    client, _, _ = setup
    assert client.get("/studio-api/manage/messages/threads").status_code == 401
    assert client.post("/studio-api/message-bridge/claim").status_code == 401
    bridge()
    assert client.get("/studio-api/manage/messages/settings", headers=auth()).status_code == 401
    host()
    body = client.get("/studio-api/manage/messages/settings").text
    assert CUSTOMER_TOKEN not in body and sms.digest(CUSTOMER_TOKEN) not in body


def test_supported_number_normalization_does_not_merge_accounts(setup):
    client, _, _ = setup
    ident = thread(client, "(416) 555-0123")
    assert thread(client, CUSTOMER_NUMBER) == ident
    assert sms.phone("1 416 555 0123") == CUSTOMER_NUMBER
    for invalid in ["+8613955500000", "+442071234567", "415123", "https://example.com"]:
        assert client.post("/studio-api/manage/messages/threads", json={"phone": invalid}).status_code == 422
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_sms_threads").fetchone()[0] == 1


def test_reservation_association_and_owner_alert_share_transaction(setup):
    client, _, _ = setup
    host(); bridge(); bridge("owner_alert")
    response = client.put("/studio-api/manage/messages/settings", json={"version": 1, "owner_enabled": True, "owner_phone": STUDIO_NUMBER})
    assert response.status_code == 200, response.text
    key = str(uuid.uuid4())
    payload = {"booking": {"date": "2026-09-11", "start": "14:00", "end": "16:00", "plan": "hourly", "guests": 2},
               "name": "Local guest", "contact_method": "phone", "contact": CUSTOMER_NUMBER, "consent": True}
    first = client.post("/studio-api/reservations", headers={"Idempotency-Key": key}, json=payload)
    assert first.status_code == 201, first.text
    assert client.post("/studio-api/reservations", headers={"Idempotency-Key": key}, json=payload).json()["id"] == first.json()["id"]
    threads = client.get("/studio-api/manage/messages/threads").json()["items"]
    assert len(threads) == 1 and threads[0]["reservations"][0]["id"] == first.json()["id"]
    with studio.database() as db:
        jobs = db.execute("SELECT * FROM studio_sms_jobs").fetchall()
        assert len(jobs) == 1 and jobs[0]["state"] == "queued"
        assert jobs[0]["recipient"] == STUDIO_NUMBER and CUSTOMER_NUMBER not in jobs[0]["content"]
    assert claim(client) is None
    job = claim(client, "owner_alert")
    assert job["recipient"] == STUDIO_NUMBER


def test_owner_alert_cannot_use_same_sender_and_recipient(setup):
    client, _, _ = setup
    host(); bridge("owner_alert")
    response = client.put("/studio-api/manage/messages/settings", json={"version": 1, "owner_enabled": True, "owner_phone": "+16475550101"})
    assert response.status_code == 409


def test_observed_device_outcome_checks_sender_and_does_not_regress_delivery(setup):
    client, _, _ = setup
    ident = thread(client); bridge()
    send(client, ident)
    job = claim(client)
    assert begin(client, job).json()["send"]
    assert result(client, job).status_code == 200
    path = f"/studio-api/message-bridge/jobs/{job['id']}/observation"
    payload = {"claim_token": job["claim_token"], "external_id": "actual-guid", "sender": CUSTOMER_NUMBER, "state": "sent"}
    assert client.post(path, headers=auth(), json=payload).status_code == 409
    payload.update(sender=STUDIO_NUMBER, state="delivered", channel="iMessage")
    assert client.post(path, headers=auth(), json=payload).status_code == 200
    payload["state"] = "sent"
    assert client.post(path, headers=auth(), json=payload).status_code == 200
    detail = client.get(f"/studio-api/manage/messages/threads/{ident}").json()
    assert detail["items"][0]["state"] == "delivered"
    assert detail["items"][0]["channel"] == "iMessage"
    assert result(client, job).status_code == 200
    assert claim(client) is None


def test_send_idempotency_payload_conflict_and_no_send_before_enabled(setup):
    client, _, _ = setup
    ident = thread(client)
    assert send(client, ident).status_code == 409
    bridge()
    key = str(uuid.uuid4())
    first = send(client, ident, key)
    assert first.status_code == 202, first.text
    assert send(client, ident, key).json()["id"] == first.json()["id"]
    assert send(client, ident, key, "Different message").status_code == 409
    other = thread(client, "+14165550124")
    assert send(client, other, key).status_code == 409
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_sms_jobs").fetchone()[0] == 1


def test_begin_is_one_shot_and_results_are_idempotent(setup):
    client, _, _ = setup
    ident = thread(client); bridge(); send(client, ident)
    job = claim(client)
    assert claim(client) is None
    assert begin(client, job).json()["send"] is True
    assert begin(client, job).json()["send"] is False
    assert result(client, job).status_code == 200
    assert result(client, job).status_code == 200
    assert result(client, job, state="failed").status_code == 409
    assert claim(client) is None


def test_started_crash_is_unknown_not_replayed(setup):
    client, _, _ = setup
    ident = thread(client); bridge(); message = send(client, ident).json()
    job = claim(client); begin(client, job)
    with studio.database() as db:
        db.execute("UPDATE studio_sms_jobs SET lease_until=0 WHERE id=?", (job["id"],))
    assert claim(client) is None
    items = client.get(f"/studio-api/manage/messages/threads/{ident}").json()["items"]
    assert items[0]["id"] == message["id"] and items[0]["state"] == "unknown"
    # A late durable result can still be acknowledged, without another send.
    assert result(client, job, state="unknown", error="interrupted").status_code == 200


def test_only_unstarted_lease_is_reclaimable_and_old_token_is_rejected(setup):
    client, _, _ = setup
    ident = thread(client); bridge(); send(client, ident)
    first = claim(client)
    with studio.database() as db:
        db.execute("UPDATE studio_sms_jobs SET lease_until=0 WHERE id=?", (first["id"],))
    second = claim(client)
    assert first["id"] == second["id"] and first["claim_token"] != second["claim_token"]
    assert begin(client, first).status_code == 409
    assert begin(client, second).json()["send"] is True


def test_inbox_scope_dedupe_channel_and_read_cursor(setup):
    client, _, _ = setup
    ident = thread(client); bridge(); bridge("owner_alert")
    event = incoming(ident, channel="iMessage")
    first = ingest(client, event)
    assert first.status_code == 200, first.text
    assert ingest(client, event).json() == first.json()
    assert ingest(client, event, "owner_alert").status_code == 403
    assert ingest(client, {**event, "external_id": "bad-phone", "phone": "+14165550129"}).status_code == 422
    assert ingest(client, {**event, "external_id": "old-private", "timestamp": 1000}).status_code == 422
    assert ingest(client, {**event, "content": "Changed"}).status_code == 409
    detail = client.get(f"/studio-api/manage/messages/threads/{ident}").json()
    assert len(detail["items"]) == 1 and detail["items"][0]["channel"] == "iMessage"
    assert detail["thread"]["unread"] == 1
    assert client.post(f"/studio-api/manage/messages/threads/{ident}/read", json={"through_seq": 999999}).status_code == 422
    assert client.post(f"/studio-api/manage/messages/threads/{ident}/read", json={"through_seq": detail["items"][0]["seq"]}).status_code == 200
    assert client.get("/studio-api/manage/messages/threads?unread=true").json()["items"] == []


def test_phone_echo_updates_existing_bubble(setup):
    client, _, _ = setup
    ident = thread(client); bridge()
    original = send(client, ident).json(); job = claim(client); begin(client, job)
    item = incoming(ident, "phone-echo", direction="outbound", content="Local test draft", job_id=job["id"], sent=True)
    assert ingest(client, item).status_code == 200
    assert result(client, job).status_code == 200
    items = client.get(f"/studio-api/manage/messages/threads/{ident}").json()["items"]
    assert len(items) == 1 and items[0]["id"] == original["id"] and items[0]["state"] == "sent"
    assert ingest(client, {**item, "external_id": "other-echo"}).status_code == 409


def test_batch_scope_failure_rolls_back_and_pagination_is_stable(setup):
    client, _, _ = setup
    ident = thread(client); bridge()
    bad = client.post("/studio-api/message-bridge/messages", headers=auth(), json={"messages": [incoming(ident), incoming("wrong-thread", "bad")]})
    assert bad.status_code == 422
    assert client.get(f"/studio-api/manage/messages/threads/{ident}").json()["items"] == []
    for n in range(4):
        assert ingest(client, incoming(ident, f"local-{n}")).status_code == 200
    latest = client.get(f"/studio-api/manage/messages/threads/{ident}?limit=2").json()
    older = client.get(f"/studio-api/manage/messages/threads/{ident}?limit=2&before={latest['next_before']}").json()
    assert latest["has_more"] and not older["has_more"]
    assert {m["id"] for m in latest["items"]}.isdisjoint({m["id"] for m in older["items"]})


def test_bridge_cannot_begin_other_role_job_or_change_reported_sender(setup):
    client, _, _ = setup
    ident = thread(client); bridge(); bridge("owner_alert"); send(client, ident)
    job = claim(client)
    assert begin(client, job, "owner_alert").status_code == 409
    response = client.post("/studio-api/message-bridge/heartbeat", headers=auth(), json={"sender": CUSTOMER_NUMBER, "version": "test"})
    assert response.status_code == 409
