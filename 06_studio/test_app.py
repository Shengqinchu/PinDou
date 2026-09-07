import copy
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import app as studio


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "DB_PATH", tmp_path / "studio.sqlite3")
    with TestClient(studio.app) as connection:
        yield connection
    studio.app.dependency_overrides.clear()


def visit():
    day = (datetime.now(studio.TORONTO) + timedelta(days=1)).date().isoformat()
    return {"kind": "visit", "name": "Studio QA", "contact_method": "wechat", "contact": "local-test-only", "consent": True, "booking": {"date": day, "start": "14:00", "end": "16:00", "guests": 1, "plan": "hourly"}}


def post(client, payload, key=None):
    return client.post("/studio-api/requests", json=payload, headers={"Idempotency-Key": key or str(uuid.uuid4())})


def test_visit_saved_once_and_replay_does_not_duplicate(client):
    key = str(uuid.uuid4())
    first = post(client, visit(), key)
    assert first.status_code == 201
    assert first.json()["status"] == "pending"
    assert first.headers["cache-control"] == "no-store"
    replay = post(client, visit(), key)
    assert replay.json()["id"] == first.json()["id"]
    changed = visit()
    changed["name"] = "Different guest"
    assert post(client, changed, key).status_code == 409
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_requests").fetchone()[0] == 1


@pytest.mark.parametrize("change", ["past", "backwards", "bad_time", "pair", "no_consent", "email", "phone", "unknown", "negative", "honeypot"])
def test_invalid_requests_are_not_saved(client, change):
    payload = visit()
    if change == "past": payload["booking"]["date"] = "2000-01-01"
    if change == "backwards": payload["booking"]["end"] = "13:00"
    if change == "bad_time": payload["booking"]["start"] = "25:99"
    if change == "pair": payload["booking"]["plan"] = "pair"
    if change == "no_consent": payload["consent"] = False
    if change == "email": payload.update(contact_method="email", contact="not-an-email")
    if change == "phone": payload.update(contact_method="phone", contact="+++-------")
    if change == "unknown": payload.update(kind="pickup", booking=None, items=[{"id": "invented", "quantity": 1}])
    if change == "negative": payload.update(kind="pickup", booking=None, items=[{"id": "starter", "quantity": -1}])
    if change == "honeypot": payload["website"] = "spam.invalid"
    assert post(client, payload).status_code == 422
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_requests").fetchone()[0] == 0


def test_pickup_quantity_and_payload_are_preserved(client):
    payload = visit()
    payload.update(kind="pickup", booking=None, items=[{"id": "beads", "quantity": 2}, {"id": "findings", "quantity": 1}])
    ref = post(client, payload).json()["id"]
    assert ref.startswith("PUP-")
    studio.app.dependency_overrides[studio.admin_actor] = lambda: "test-admin"
    result = client.get("/studio-api/manage/requests").json()
    assert result["total"] == 1
    assert result["items"][0]["payload"]["items"] == payload["items"]


def test_admin_auth_required_and_mutation_is_versioned_and_audited(client):
    ref = post(client, visit()).json()["id"]
    assert client.get("/studio-api/manage/requests").status_code == 401
    update = {"status": "confirmed", "staff_note": "Guest contacted and time agreed.", "version": 1}
    assert client.patch(f"/studio-api/manage/requests/{ref}", json=update).status_code == 401
    studio.app.dependency_overrides[studio.admin_actor] = lambda: "test-admin"
    assert client.patch(f"/studio-api/manage/requests/{ref}", json=update).json()["version"] == 2
    assert client.patch(f"/studio-api/manage/requests/{ref}", json=update).status_code == 409
    assert client.get("/studio-api/manage/requests?status=confirmed").json()["total"] == 1
    with studio.database() as db:
        audit = db.execute("SELECT * FROM studio_audit").fetchone()
        assert audit["actor"] == "test-admin"
        assert audit["previous_status"] == "pending"
        assert audit["new_status"] == "confirmed"


def test_rate_limit_and_duplicate_retry(client):
    payload = visit()
    key = str(uuid.uuid4())
    assert post(client, payload, key).status_code == 201
    for _ in range(7):
        assert post(client, payload).status_code == 201
    assert post(client, payload).status_code == 429
    assert post(client, payload, key).status_code == 201


def test_sql_like_filters_rejected(client):
    studio.app.dependency_overrides[studio.admin_actor] = lambda: "test-admin"
    assert client.get("/studio-api/manage/requests", params={"status": "' OR 1=1--"}).status_code == 422
