import json
import time
from types import SimpleNamespace

import pytest

import app as studio
import authing_login
import owner_wechat as wx
import miniapp_login
from test_owner_notifications import setup, host, create

APP_ID = "wx" + "a" * 16
TEMPLATE = "local_template_" + "T" * 32


@pytest.fixture
def wechat(setup, monkeypatch):
    client, _, _ = setup
    calls = []
    monkeypatch.setattr(miniapp_login, "available", lambda: True)
    monkeypatch.setattr(miniapp_login, "config", lambda: SimpleNamespace(app_id=APP_ID, environment="trial"))
    monkeypatch.setattr(miniapp_login, "access_token", lambda: "local-access-token")
    monkeypatch.setattr(miniapp_login, "wx_request", lambda *a, **kw: b"\x89PNG\r\n\x1a\nlocal-qr")
    def provider(path, body=None, params=None):
        calls.append((path, body, params))
        if path.endswith("gettemplate"):
            return {"errcode": 0, "data": [{"type": 2, "title": "新预约审核通知", "priTmplId": TEMPLATE,
                    "content": "\n".join("{{" + k + ".DATA}}" for k in wx.TEMPLATE_KEYS)}]}
        return {"errcode": 0, "errmsg": "ok"}
    monkeypatch.setattr(wx, "provider", provider)
    yield client, calls


def ticket(number="1", app_id=APP_ID):
    token = ("t" + number) * 21 + "Z"
    with studio.database() as db:
        db.execute("INSERT OR REPLACE INTO studio_miniapp_tickets VALUES(?,?,?,?)",
                   (authing_login.digest(token), app_id, "local-openid-" + number * 18, int(time.time()) + 600))
    return {"X-Pindou-Miniapp": token}


def configure(client):
    host()
    response = client.post("/studio-api/manage/owner-wechat/template")
    assert response.status_code == 200, response.text
    value = response.json()
    assert client.put("/studio-api/manage/owner-wechat", json={"version": value["version"], "enabled": True}).status_code == 200


def bind(client, headers=None):
    host()
    headers = headers or ticket()
    response = client.post("/studio-api/manage/owner-wechat/bindings", json={"label": "Local owner"})
    assert response.status_code == 200, response.text
    scene = response.json()["scene"]
    result = client.post("/studio-api/owner-wechat/binding", headers=headers, json={"scene": scene, "confirm": True})
    assert result.status_code == 200, result.text
    return headers, scene


def allow(client, headers):
    state = client.get("/studio-api/owner-wechat/status", headers=headers)
    assert state.status_code == 200, state.text
    value = state.json()
    result = client.post("/studio-api/owner-wechat/subscribe", headers=headers, json={"nonce": value["nonce"], "result": "accept"})
    assert result.status_code == 200, result.text
    return value["nonce"]


def jobs():
    with studio.database() as db:
        return [dict(r) for r in db.execute("SELECT * FROM studio_owner_wechat_jobs ORDER BY created_at,id")]


def test_admin_and_native_owner_roles_are_distinct(wechat):
    client, _ = wechat
    assert client.get("/studio-api/manage/owner-wechat").status_code == 401
    headers = ticket()
    assert client.get("/studio-api/owner-wechat/status", headers=headers).json() == {"bound": False}
    assert client.get("/studio-api/owner-wechat/reservations", headers=headers).status_code == 403
    assert client.get("/studio-api/owner-wechat/reservations").status_code == 401


def test_template_reuses_matching_existing_configuration(wechat):
    client, calls = wechat
    configure(client)
    assert calls[0][0] == "wxaapi/newtmpl/gettemplate"
    assert not any(c[0].endswith("addtemplate") for c in calls)
    result = client.get("/studio-api/manage/owner-wechat").json()
    assert result["template_id"] == TEMPLATE and result["enabled"]


def test_new_template_respects_provider_scene_description_limit(wechat, monkeypatch):
    client, _ = wechat
    host()
    def provider(path, body=None, params=None):
        if path.endswith('gettemplate'):
            return {'errcode': 0, 'data': []}
        if path.endswith('getpubtemplatekeywords'):
            return {'errcode': 0, 'data': [{'kid': k, 'rule': v} for k,v in {1:'thing',2:'time',3:'time',4:'thing',5:'thing'}.items()]}
        assert path.endswith('addtemplate') and len(body['sceneDesc']) <= 15
        assert body['kidList'] == [1,2,3,4,5]
        return {'errcode': 0, 'priTmplId': TEMPLATE}
    monkeypatch.setattr(wx, 'provider', provider)
    assert client.post('/studio-api/manage/owner-wechat/template').status_code == 200


def test_binding_requires_confirmation_and_is_single_use(wechat):
    client, _ = wechat
    configure(client)
    headers, scene = bind(client)
    assert client.post("/studio-api/owner-wechat/binding", headers=ticket("2"), json={"scene": scene, "confirm": True}).status_code == 400
    state = client.get("/studio-api/owner-wechat/status", headers=headers).json()
    assert state["bound"] and not state["binding"]["authorization_available"]
    public = client.get("/studio-api/manage/owner-wechat").text
    assert "local-openid" not in public and "local-access-token" not in public


def test_refresh_does_not_invalidate_in_flight_permission_and_replay_has_no_credit(wechat):
    client, _ = wechat
    configure(client); headers, _ = bind(client)
    first = client.get("/studio-api/owner-wechat/status", headers=headers).json()
    client.get("/studio-api/owner-wechat/status", headers=headers)
    payload = {"nonce": first["nonce"], "result": "accept"}
    assert client.post("/studio-api/owner-wechat/subscribe", headers=headers, json=payload).status_code == 200
    assert client.post("/studio-api/owner-wechat/subscribe", headers=headers, json=payload).status_code == 200
    with studio.database() as db:
        assert db.execute("SELECT grants FROM studio_owner_wechat_bindings").fetchone()[0] == 1
    assert client.post("/studio-api/owner-wechat/subscribe", headers=ticket("2"), json=payload).status_code == 403


def test_reservation_notice_waits_for_permission_then_uses_real_owner_and_trial_page(wechat):
    client, calls = wechat
    configure(client); headers, _ = bind(client)
    response = create(client)
    assert response.status_code == 201
    assert jobs()[0]["state"] == "waiting_subscription"
    assert not wx.process_one(studio.database)
    allow(client, headers)
    assert wx.process_one(studio.database)
    job = jobs()[0]
    assert job["state"] == "accepted"
    request = next(c[1] for c in calls if c[0] == "cgi-bin/message/subscribe/send")
    assert request["template_id"] == TEMPLATE and request["miniprogram_state"] == "trial"
    assert request["page"] == "pages/studio/owner?reservation=" + response.json()["id"]
    assert set(request["data"]) == set(wx.TEMPLATE_KEYS)
    assert "private-contact" not in json.dumps(request) and "private-customer-note" not in json.dumps(request)
    assert not wx.process_one(studio.database)


def test_provider_subscription_rejection_is_authoritative(wechat, monkeypatch):
    client, _ = wechat
    configure(client); headers, _ = bind(client); allow(client, headers); create(client)
    monkeypatch.setattr(wx, "provider", lambda *a, **kw: {"errcode": 43101})
    assert wx.process_one(studio.database)
    assert jobs()[0]["error"] == "owner_wechat_subscription_required"
    with studio.database() as db:
        assert db.execute("SELECT grants FROM studio_owner_wechat_bindings").fetchone()[0] == 0
    assert not wx.process_one(studio.database)


def test_inflating_local_counter_cannot_override_wechat_rejection(wechat, monkeypatch):
    client, _ = wechat
    configure(client); headers, _ = bind(client); allow(client, headers)
    with studio.database() as db:
        db.execute('UPDATE studio_owner_wechat_bindings SET grants=999999')
    create(client)
    monkeypatch.setattr(wx, 'provider', lambda *a, **kw: {'errcode':43101})
    assert wx.process_one(studio.database)
    assert jobs()[0]['state'] != 'accepted'
    with studio.database() as db:
        assert db.execute('SELECT grants FROM studio_owner_wechat_bindings').fetchone()[0] == 0


def test_timeout_does_not_replay_or_invent_success(wechat, monkeypatch):
    client, _ = wechat
    configure(client); headers, _ = bind(client); allow(client, headers); create(client)
    count = []
    def fail(*a, **kw):
        count.append(1)
        raise TimeoutError()
    monkeypatch.setattr(wx, "provider", fail)
    assert wx.process_one(studio.database)
    assert jobs()[0]["state"] == "unknown"
    assert not wx.process_one(studio.database) and len(count) == 1


def test_empty_provider_response_is_not_acceptance(wechat, monkeypatch):
    client, _ = wechat
    configure(client); headers, _ = bind(client); allow(client, headers); create(client)
    monkeypatch.setattr(wx, "provider", lambda *a, **kw: {})
    assert wx.process_one(studio.database)
    assert jobs()[0]["state"] == "unknown"


def test_cancelled_booking_and_revoked_binding_never_send(wechat):
    client, calls = wechat
    configure(client); headers, _ = bind(client); allow(client, headers)
    response = create(client); ident = response.json()["id"]
    with studio.database() as db:
        db.execute("UPDATE studio_reservations SET status='cancelled' WHERE id=?", (ident,))
    assert wx.process_one(studio.database)
    assert jobs()[0]["state"] == "skipped"
    state = client.get("/studio-api/owner-wechat/status", headers=headers).json()
    assert client.delete("/studio-api/manage/owner-wechat/bindings/" + state["binding"]["id"]).status_code == 200
    assert client.get("/studio-api/owner-wechat/reservations", headers=headers).status_code == 403
    assert not any(c[0].endswith("subscribe/send") for c in calls)


def test_binding_ticket_from_another_app_is_rejected(wechat):
    client, _ = wechat
    configure(client)
    assert client.get("/studio-api/owner-wechat/status", headers=ticket("3", "wx" + "b" * 16)).status_code == 401
