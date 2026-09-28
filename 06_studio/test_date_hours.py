"""Single-date hours use the same policy in calendars, requests and confirmation."""
import pytest
from test_reservations import client, body, submit, confirm, admin
from test_capacity_buffer import configure


def override(day="2026-09-09", **changes):
    return {"date": day, "enabled": True, "open": "10:00", "close": "22:00", **changes}


def days(client, experience="beads", host=False):
    path = "/studio-api/manage/reservation-timetable?start=2026-09-07" if host else "/studio-api/reservation-calendar"
    sep = "&" if "?" in path else "?"
    response = client.get(path + sep + "experience=" + experience)
    assert response.status_code == 200, response.text
    return {d["date"]: d for d in response.json()["days"]}


@pytest.mark.parametrize("plan,start,end", [("hourly", "18:00", "20:00"), ("day", "18:00", "22:00"), ("patch", "20:00", "21:00")])
def test_only_one_wednesday_extends_and_accepts_all_plans(client, plan, start, end):
    admin()
    before = client.get("/studio-api/manage/reservation-policy").json()
    configure(client, date_overrides=[override()])
    for experience in ("beads", "patch"):
        public = days(client, experience)
        host = days(client, experience, host=True)
        assert public["2026-09-09"]["close"] == host["2026-09-09"]["close"] == "22:00"
        assert public["2026-09-16"]["close"] == "16:00"
        assert next(s for s in public["2026-09-09"]["slots"] if s["start"] == "18:00")["available"]
    result = submit(client, body("2026-09-09", start, end, plan))
    assert result.status_code == 201, result.text
    assert confirm(client, result.json()["id"]).status_code == 200
    assert submit(client, body("2026-09-16", start, end, plan)).status_code == 422
    after = client.get("/studio-api/manage/reservation-policy").json()
    assert after["weekly_hours"] == before["weekly_hours"]


def test_legacy_partial_save_keeps_override_and_cas_prevents_loss(client):
    configure(client, date_overrides=[override()])
    before = client.get("/studio-api/manage/reservation-policy").json()
    result = client.put("/studio-api/manage/reservation-policy", json={"version": before["version"], "max_guests_per_group": 6})
    assert result.status_code == 200
    assert result.json()["date_overrides"] == before["date_overrides"]
    stale = client.put("/studio-api/manage/reservation-policy", json={"version": before["version"], "date_overrides": []})
    assert stale.status_code == 409
    configure(client, date_overrides=[])
    assert days(client)["2026-09-09"]["close"] == "16:00"


@pytest.mark.parametrize("plan,confirm_first", [("hourly", True), ("patch", False)])
def test_cannot_remove_or_shorten_hours_covering_accepted_bookings(client, plan, confirm_first):
    configure(client, date_overrides=[override()])
    result = submit(client, body("2026-09-09", "18:00", "19:00" if plan == "patch" else "20:00", plan))
    assert result.status_code == 201
    if confirm_first:
        assert confirm(client, result.json()["id"]).status_code == 200
    policy = client.get("/studio-api/manage/reservation-policy").json()
    for overrides in ([], [override(close="18:30")], [override(enabled=False)]):
        result = client.put("/studio-api/manage/reservation-policy", json={"version": policy["version"], "date_overrides": overrides})
        assert result.status_code == 409, result.text
    assert client.get("/studio-api/manage/reservation-policy").json() == policy


@pytest.mark.parametrize("overrides", [
    [override(), override()],
    [override(day="invalid")],
    [override(open="10:15")],
    [override(close="11:30")],
    [override(close="09:00")],
])
def test_invalid_overrides_leave_policy_unchanged(client, overrides):
    admin()
    before = client.get("/studio-api/manage/reservation-policy").json()
    result = client.put("/studio-api/manage/reservation-policy", json={"version": before["version"], "date_overrides": overrides})
    assert result.status_code == 422
    assert client.get("/studio-api/manage/reservation-policy").json() == before


def test_special_date_extends_calendar_rows_and_can_close_one_date(client):
    configure(client, date_overrides=[override(open="08:00", close="23:00"), override("2026-09-10", enabled=False)])
    for experience in ("beads", "patch"):
        special = days(client, experience)
        wed = special["2026-09-09"]
        assert wed["slots"][0]["start"] == "08:00" and wed["slots"][-1]["end"] == "23:00"
        assert not any(s["available"] for s in special["2026-09-10"]["slots"])
        assert special["2026-09-17"]["close"] == "18:00"
