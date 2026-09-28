import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
import app as studio
import reservations as visits
import patch_promotion as promo
from test_reservations import client, body, submit, admin


def patch(hour=10, guests=2):
    value = body("2026-09-08", f"{hour:02d}:00", f"{hour+1:02d}:00", "patch")
    value["booking"]["guests"] = guests
    return value


def state(client):
    return client.get("/studio-api/patch-promotion").json()


def settings(client, quota=10, enabled=True, version=None):
    admin()
    current = client.get("/studio-api/manage/patch-promotion").json()
    return client.put("/studio-api/manage/patch-promotion",
                      json={"quota":quota,"enabled":enabled,"version":version or current["version"]})


def change(client, row, status):
    admin()
    return client.patch("/studio-api/manage/reservations/"+row["id"],
                        json={"version":row["version"],"status":status})


def gift(client, row):
    admin()
    rows=client.get("/studio-api/manage/reservations?search="+row["id"]).json()["items"]
    return rows[0]["patch_gift_guests"]


def test_person_count_and_whole_final_group(client):
    assert state(client)["remaining"] == state(client)["quota"] == 10
    for i,guests in enumerate([4,4,1,3]):
        row=submit(client,patch(10+i,guests)).json()
        assert gift(client,row)==guests
    assert state(client)["remaining"]==0
    assert client.get("/studio-api/manage/patch-promotion").json()["allocated"]==12
    row=submit(client,patch(14,2)).json()
    assert gift(client,row)==0
    timetable=client.get("/studio-api/manage/reservation-timetable?start=2026-09-08").json()
    assert sum(r["patch_gift_guests"] for r in timetable["days"][0]["bookings"])==12


def test_last_place_concurrent_groups_and_retries(client):
    settings(client,1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda hour:submit(client,patch(hour,3)),[10,12]))
    assert all(r.status_code==201 for r in responses)
    rows=[r.json() for r in responses]
    assert sorted(gift(client,r) for r in rows)==[0,3]
    assert state(client)["remaining"]==0
    key=str(uuid.uuid4())
    first=submit(client,patch(14),key).json()
    assert submit(client,patch(14),key).json()["id"]==first["id"]
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM patch_promotion_claims").fetchone()[0]==3
        assert db.execute("SELECT sum(guests) FROM patch_promotion_claims WHERE active=1").fetchone()[0]==3


def test_customer_cancel_frees_once_and_new_final_group_gets_all(client):
    settings(client,1)
    row=submit(client,patch(10,4)).json()
    assert state(client)["remaining"]==0
    for _ in range(2):
        assert client.post("/studio-api/reservations/"+row["id"]+"/cancel",json={"version":1}).status_code==200
    assert state(client)["remaining"]==1
    assert gift(client,row)==0
    assert gift(client,submit(client,patch(12,3)).json())==3
    assert state(client)["remaining"]==0


def test_old_bookings_beads_and_failed_submission_do_not_enroll(client):
    old=submit(client,patch()).json()
    # Simulate the pre-launch schema, then run the same deployment migration.
    with studio.database() as db:
        for table in ("patch_promotion_claims","patch_promotion_events","patch_promotion"):
            db.execute("DROP TABLE "+table)
    visits.initialize(studio.database)
    assert state(client)["remaining"]==10 and gift(client,old)==0
    assert change(client,old,"confirmed").status_code==200
    assert gift(client,old)==0
    assert submit(client,patch()).status_code==409
    assert submit(client,body()).status_code==201
    assert state(client)["remaining"]==10
    future=submit(client,patch(12,3)).json()
    assert gift(client,future)==3
    visits.initialize(studio.database)  # repeated releases must not reset stock
    assert state(client)["remaining"]==7


def test_quota_edits_do_not_withdraw_awards_pause_or_backfill(client):
    row=submit(client,patch(10,3)).json()
    result=settings(client,1)
    assert result.json()["remaining"]==0 and result.json()["allocated"]==3
    assert gift(client,row)==3
    settings(client,20,False)
    no=submit(client,patch(12)).json()
    assert gift(client,no)==0
    settings(client,20)
    assert gift(client,no)==0  # no retroactive claims on old requests
    assert gift(client,submit(client,patch(14,4)).json())==4
    assert state(client)["remaining"]==13


def test_admin_cancel_restore_and_pending_delete(client):
    settings(client,1)
    first=submit(client,patch()).json()
    assert change(client,first,"cancelled").status_code==200
    second=submit(client,patch(12,4)).json()
    assert change(client,first|{"version":2},"pending").status_code==200
    assert gift(client,first)==0  # cancellation relinquished the gift
    assert change(client,second,"cancelled").status_code==200
    # Editing a note later cannot claim a released gift for an already-restored booking.
    assert change(client,first|{"version":3},"pending").status_code==200
    assert gift(client,first)==0
    third=submit(client,patch(14,3)).json()
    assert gift(client,third)==3
    assert client.request("DELETE","/studio-api/manage/reservations/"+third["id"],
                          json={"version":1,"reason":"qa only"}).status_code==200
    assert state(client)["remaining"]==1
    assert client.post("/studio-api/manage/reservations/"+third["id"]+"/restore",
                       json={"version":2,"reason":"qa only"}).status_code==200
    assert gift(client,third)==3 and state(client)["remaining"]==0


def test_completed_gift_stays_counted_when_archived(client,monkeypatch):
    client.get("/studio-api/auth/me");admin()
    row=client.post("/studio-api/manage/members/qa-owner/reservations",
        json={"kind":"booking","booking":patch()["booking"],"status":"confirmed","reason":"qa"},
        headers={"Idempotency-Key":str(uuid.uuid4())}).json()
    assert gift(client,row)==2
    monkeypatch.setattr(visits,"now_local",lambda:datetime(2026,9,8,12,tzinfo=visits.ZONE))
    assert client.patch("/studio-api/manage/reservations/"+row["id"],
        json={"version":1,"status":"completed","actual_minutes":30,"actual_guests":2}).status_code==200
    assert client.request("DELETE","/studio-api/manage/reservations/"+row["id"],
        json={"version":2,"reason":"qa"}).status_code==200
    assert state(client)["remaining"]==8


def test_admin_backfill_never_claims_launch_gift(client):
    client.get("/studio-api/auth/me");admin()
    value=patch()["booking"]|{"date":"2026-09-06"}
    result=client.post("/studio-api/manage/members/qa-owner/reservations",
        json={"kind":"backfill","booking":value,"status":"completed","reason":"qa","actual_minutes":30,"actual_guests":2},
        headers={"Idempotency-Key":str(uuid.uuid4())})
    assert result.status_code==201,result.text
    assert gift(client,result.json())==0 and state(client)["remaining"]==10


def test_version_permissions_privacy_and_validation(client):
    assert client.get("/studio-api/manage/patch-promotion").status_code==401
    assert client.put("/studio-api/manage/patch-promotion",json={"quota":1,"enabled":True,"version":1}).status_code==401
    response=client.get("/studio-api/patch-promotion")
    assert response.headers["cache-control"]=="no-store"
    assert set(response.json())=={"campaign","enabled","quota","remaining"}
    first=settings(client,5).json()
    assert settings(client,5,version=1).json()==first # lost response replay
    assert settings(client,8,version=1).status_code==409
    for invalid in (-1,1.2,"3",True,100001):
        assert client.put("/studio-api/manage/patch-promotion",
            json={"quota":invalid,"enabled":True,"version":first["version"]}).status_code==422
    assert settings(client,0).json()["remaining"]==0
