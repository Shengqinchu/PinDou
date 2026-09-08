import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
import app as studio
import reservations as visits
import commerce

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "DB_PATH", tmp_path / "visits.sqlite3")
    monkeypatch.setattr(visits, "now_local", lambda: datetime(2026, 9, 7, 9, 0, tzinfo=visits.ZONE))
    monkeypatch.setattr(visits, "COOKIE_SECURE", False)
    with TestClient(studio.app) as client:
        client.get("/studio-api/reservation-calendar")
        yield client
    studio.app.dependency_overrides.clear()

def body(day="2026-09-08", start="14:00", end="16:00", plan="hourly"):
    return {"booking":{"date":day,"start":start,"end":end,"plan":plan,"guests":2},"name":"Reservation QA","contact_method":"wechat","contact":"test-local","consent":True}

def submit(client, payload=None, key=None):
    return client.post("/studio-api/reservations",json=payload or body(),headers={"Idempotency-Key":key or str(uuid.uuid4())})

def admin():
    studio.app.dependency_overrides[studio.admin_actor] = lambda: "test-owner"

def test_calendar_window_and_blocked_hours(client):
    result=client.get("/studio-api/reservation-calendar").json()
    assert len(result["days"])==14
    assert result["days"][0]["date"]=="2026-09-07" and result["days"][-1]["date"]=="2026-09-20"
    wed=result["days"][2]; thu=result["days"][3]
    assert wed["close"]=="16:00" and thu["close"]=="18:00"
    assert all(not s["available"] for s in wed["slots"] if s["start"] >= "16:00")
    assert all(not s["available"] for s in thu["slots"] if s["start"] >= "18:00")
    assert "remaining" not in str(result)

@pytest.mark.parametrize("day,start,end,plan",[
    ("2026-09-21","10:00","12:00","hourly"),
    ("2026-09-06","10:00","12:00","hourly"),
    ("2026-09-08","10:00","11:30","hourly"),
    ("2026-09-09","15:00","17:00","hourly"),
    ("2026-09-10","17:00","19:00","hourly"),
    ("2026-09-08","21:00","23:00","hourly"),
    ("2026-09-08","10:15","12:15","hourly"),
    ("2026-09-09","10:00","22:00","day"),
])
def test_reject_unbookable_intervals(client,day,start,end,plan):
    assert submit(client,body(day,start,end,plan)).status_code==422
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_reservations").fetchone()[0]==0

def test_submission_receipt_privacy_replay_and_no_paid_order(client):
    key=str(uuid.uuid4()); first=submit(client,key=key)
    assert first.status_code==201
    ref=first.json()["id"]
    assert first.json()["status"]=="pending"
    assert submit(client,key=key).json()["id"]==ref
    assert client.get("/studio-api/reservations/"+ref).status_code==200
    with TestClient(studio.app) as other:
        assert other.get("/studio-api/reservations/"+ref).status_code==404
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_reservations").fetchone()[0]==1
        assert db.execute("SELECT count(*) FROM commerce_orders").fetchone()[0]==0
    changed=body();changed["name"]="Different"
    assert submit(client,changed,key).status_code==409

def test_manual_confirmation_and_version_conflict(client):
    ref=submit(client).json()["id"]
    assert client.get("/studio-api/manage/reservations").status_code==401
    admin()
    assert client.patch("/studio-api/manage/reservations/"+ref,json={"status":"confirmed","version":1,"staff_note":"private note"}).status_code==200
    receipt=client.get("/studio-api/reservations/"+ref).json()
    assert receipt["status"]=="confirmed" and "staff_note" not in receipt
    assert client.patch("/studio-api/manage/reservations/"+ref,json={"status":"cancelled","version":1}).status_code==409
    assert client.patch("/studio-api/manage/reservations/"+ref,json={"status":"cancelled","version":2}).status_code==200
    assert client.get("/studio-api/reservations/"+ref).json()["status"]=="cancelled"

def test_optional_exclusive_groups_is_transactional(client):
    one=submit(client).json()["id"]; two=submit(client).json()["id"]
    admin()
    assert client.put("/studio-api/manage/reservation-policy",json={"exclusive_groups":True,"version":1}).status_code==200
    assert client.patch("/studio-api/manage/reservations/"+one,json={"status":"confirmed","version":1}).status_code==200
    assert client.patch("/studio-api/manage/reservations/"+two,json={"status":"confirmed","version":1}).status_code==409
    assert submit(client).status_code==409
    day=client.get("/studio-api/reservation-calendar").json()["days"][1]
    assert all(not s["available"] for s in day["slots"] if "14:00" <= s["start"] < "16:00")
    assert client.patch("/studio-api/manage/reservations/"+one,json={"status":"cancelled","version":2}).status_code==200
    assert submit(client).status_code==201

def test_day_pass_and_sales_pause(client, monkeypatch):
    result=submit(client,body("2026-09-09","10:00","16:00","day"))
    assert result.status_code==201
    monkeypatch.setattr(commerce,"PUBLIC_SALES_ENABLED",False)
    assert client.get("/studio-api/catalog").json()["checkout_ready"] is False
    assert client.post("/studio-api/cart/quote",json={"items":[]}).status_code in (409,422)

def test_past_today_and_rate_limit(client,monkeypatch):
    monkeypatch.setattr(visits,"now_local",lambda:datetime(2026,9,7,12,0,tzinfo=visits.ZONE))
    assert submit(client,body("2026-09-07","10:00","12:00")).status_code==422
    key=str(uuid.uuid4())
    assert submit(client,key=key).status_code==201
    for _ in range(7): assert submit(client).status_code==201
    assert submit(client).status_code==429
    assert submit(client,key=key).status_code==201
