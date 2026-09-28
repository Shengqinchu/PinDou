"""Patch bookings use an independent, transactional one-group resource."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
import app as studio
import reservations as visits
import customer_notifications
from test_reservations import client, body, submit, admin


def patch(start="11:00", end="12:00"):
    return body("2026-09-08", start, end, "patch")


def calendar(client, experience="patch", day=1):
    return client.get("/studio-api/reservation-calendar", params={"experience": experience}).json()["days"][day]


def slot(day, at):
    return next(s for s in day["slots"] if s["start"] == at)


def change(client, row, status):
    return client.patch("/studio-api/manage/reservations/" + row["id"],
                        json={"status": status, "version": row["version"]})


def test_patch_calendar_fixed_hour_and_closing_boundary(client):
    result = client.get("/studio-api/reservation-calendar?experience=patch").json()
    assert result["minimum_minutes"] == 60 and result["capacity_buffer_minutes"] == 0
    assert result["offers"] == [] and result["max_guests_per_group"] == 4
    assert slot(result["days"][2], "15:00")["start_available"]
    assert not slot(result["days"][2], "15:30")["start_available"]
    assert client.get("/studio-api/reservation-calendar?experience=unknown").status_code == 422
    accepted = submit(client, body("2026-09-09", "15:00", "16:00", "patch"))
    assert accepted.status_code == 201
    assert accepted.json()["booked_minutes"] == 60


@pytest.mark.parametrize("start,end", [("11:00","11:30"),("11:00","13:00"),
    ("11:30","11:00"),("11:15","12:15"),("21:30","22:30")])
def test_patch_cannot_change_fixed_duration_or_cross_closing(client, start, end):
    assert submit(client, patch(start,end)).status_code == 422


def test_pending_patch_occupies_both_halves_and_has_no_bead_buffer(client):
    row = submit(client, patch()).json()
    day = calendar(client)
    assert not slot(day, "11:00")["available"]
    assert not slot(day, "11:30")["available"]
    assert not slot(day, "10:30")["start_available"]  # crosses occupied second half
    assert slot(day, "10:00")["start_available"]
    assert slot(day, "12:00")["start_available"]
    assert not any(s["buffered"] for s in day["slots"])
    assert submit(client, patch("10:30","11:30")).status_code == 409
    assert submit(client, patch("11:30","12:30")).status_code == 409
    assert submit(client, patch("12:00","13:00")).status_code == 201
    assert slot(calendar(client,"beads"), "11:00")["available"]
    assert row["status"] == "pending"


def test_full_bead_group_and_patch_can_coexist(client):
    admin()
    assert client.put("/studio-api/manage/reservation-policy",
                      json={"exclusive_groups":True,"version":1}).status_code == 200
    bead = submit(client, body("2026-09-08","10:00","14:00")).json()
    assert change(client, bead, "confirmed").status_code == 200
    assert not slot(calendar(client,"beads"),"11:00")["available"]
    assert slot(calendar(client),"11:00")["start_available"]
    patch_row = submit(client, patch()).json()
    assert change(client, patch_row, "confirmed").status_code == 200
    assert not slot(calendar(client),"11:00")["available"]


def test_patch_idempotency_and_concurrent_requests(client):
    key = str(uuid.uuid4())
    result = submit(client, patch(), key)
    assert result.status_code == 201
    assert submit(client, patch(), key).json()["id"] == result.json()["id"]
    assert submit(client, patch("12:00","13:00"),key).status_code == 409
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(client,patch("14:00","15:00")).status_code, range(2)))
    assert sorted(results) == [201,409]


def test_cancel_delete_restore_and_reactivate_recheck_patch_capacity(client):
    admin()
    row = submit(client, patch()).json()
    assert client.request("DELETE","/studio-api/manage/reservations/"+row["id"],
        json={"version":1,"reason":"local test"}).status_code == 200
    assert slot(calendar(client),"11:00")["start_available"]
    other = submit(client,patch()).json()
    assert client.post("/studio-api/manage/reservations/"+row["id"]+"/restore",
        json={"version":2,"reason":"local test"}).status_code == 409
    assert change(client,other,"cancelled").status_code == 200
    assert client.post("/studio-api/manage/reservations/"+row["id"]+"/restore",
        json={"version":2,"reason":"local test"}).status_code == 200
    assert change(client,other|{"version":2},"pending").status_code == 409
    assert change(client,other|{"version":2},"confirmed").status_code == 409
    assert not slot(calendar(client),"11:00")["available"]
    # Customer cancellation also frees a pending slot.
    assert client.post("/studio-api/reservations/"+row["id"]+"/cancel",
                       json={"version":3}).status_code == 200
    assert slot(calendar(client),"11:00")["start_available"]


def test_patch_filters_timetable_and_privacy(client):
    bead=submit(client,body("2026-09-08","10:00","14:00")).json()
    patch_row=submit(client,patch()).json()
    assert client.get("/studio-api/manage/reservations?experience=patch").status_code == 401
    admin()
    items=client.get("/studio-api/manage/reservations?experience=patch").json()
    assert [x["id"] for x in items["items"]] == [patch_row["id"]]
    assert items["counts"]["pending"] == 1
    assert client.get("/studio-api/manage/reservations?experience=beads").json()["items"][0]["id"] == bead["id"]
    data=client.get("/studio-api/manage/reservation-timetable?start=2026-09-07&experience=patch").json()
    assert len(data["days"][1]["bookings"]) == 1
    assert data["days"][1]["bookings"][0]["plan"] == "patch"
    assert slot(data["days"][1],"11:00")["capacity_full"]
    all_data=client.get("/studio-api/manage/reservation-timetable?start=2026-09-07").json()
    assert len(all_data["days"][1]["bookings"]) == 2
    assert not slot(all_data["days"][1],"11:00")["capacity_full"]
    assert "contact" not in json.dumps(data)
    public=client.get("/studio-api/auth/reservations").json()
    assert "staff_note" not in json.dumps(public)
    assert next(row for row in public["items"] if row["id"] == patch_row["id"])["booking"]["plan"] == "patch"


def test_patch_global_closure_and_policy_protect_pending_request(client):
    row=submit(client,patch()).json();admin()
    assert client.post("/studio-api/manage/reservation-blocks",
        json={"date":"2026-09-08","start":"11:00","end":"12:00"}).status_code == 409
    policy=client.get("/studio-api/manage/reservation-policy").json()
    policy["weekly_hours"][1]["open"]="11:30"
    assert client.put("/studio-api/manage/reservation-policy",json=policy).status_code == 409
    assert change(client,row,"cancelled").status_code == 200
    assert client.post("/studio-api/manage/reservation-blocks",
        json={"date":"2026-09-08","start":"11:00","end":"12:00"}).status_code == 201
    assert not slot(calendar(client),"11:00")["available"]
    assert not slot(calendar(client,"beads"),"11:00")["available"]


def test_admin_patch_creation_completion_finance_and_no_admin_reward(client, monkeypatch):
    client.get("/studio-api/auth/me");admin()
    payload={"kind":"booking","booking":patch()["booking"],"status":"confirmed","reason":"local admin"}
    result=client.post("/studio-api/manage/members/qa-owner/reservations",json=payload,
                      headers={"Idempotency-Key":str(uuid.uuid4())})
    assert result.status_code==201
    row=result.json()
    assert submit(client,patch()).status_code==409
    monkeypatch.setattr(visits,"now_local",lambda:datetime(2026,9,8,12,0,tzinfo=visits.ZONE))
    result=client.patch("/studio-api/manage/reservations/"+row["id"],
        json={"version":1,"status":"completed","actual_minutes":30,"actual_guests":2})
    assert result.status_code==200
    with studio.database() as db:
        entry=dict(db.execute("SELECT * FROM studio_finance_entries WHERE reservation_id=?",(row["id"],)).fetchone())
        assert json.loads(entry["items"])==["布贴DIY"]
        assert entry["amount_cents"] is None
        assert not db.execute("SELECT 1 FROM studio_wallet_ledger WHERE idempotency_key=?",("visit-reward:"+row["id"],)).fetchone()


@pytest.mark.parametrize("channel",["site","sms","email","wechat"])
@pytest.mark.parametrize("kind",["pending","confirmed","cancelled","reminder"])
def test_patch_notification_names_experience_in_english(channel,kind):
    payload={"url":"", "booking":patch()["booking"],"name":"代记录"}
    result=customer_notifications.delivery_payload(
        {"channel":channel,"kind":kind,"reservation_id":"VIS-QA"},payload)
    assert result["body"].startswith("Experience: Patch DIY\n")
    assert "Hamilton local time" in result["body"]
    assert not any("\u4e00" <= char <= "\u9fff" for char in result["title"]+result["body"])
