"""Attendance is required on completion, never on an ordinary status update."""
import pytest

import app as studio
import wallet
from test_reservations import client, admin, submit


@pytest.mark.parametrize('status', ['pending', 'confirmed', 'cancelled'])
@pytest.mark.parametrize('legacy_zero', [False, True])
def test_other_statuses_do_not_require_or_overwrite_attendance(client, status, legacy_zero):
    ident = submit(client).json()['id']
    admin()
    if legacy_zero:
        with studio.database() as db:
            db.execute('UPDATE studio_reservations SET actual_minutes=0 WHERE id=?', (ident,))
    response = client.patch('/studio-api/manage/reservations/'+ident,
                            json={'status':status,'version':1,'public_note':'See you soon'})
    assert response.status_code == 200, response.text
    with studio.database() as db:
        row = db.execute('SELECT * FROM studio_reservations WHERE id=?', (ident,)).fetchone()
        assert row['status'] == status
        assert row['actual_minutes'] == (0 if legacy_zero else None)
        assert row['actual_guests'] is None
        assert row['public_note'] == 'See you soon'
        assert db.execute("SELECT count(*) FROM studio_wallet_ledger WHERE idempotency_key=?", ('visit-reward:'+ident,)).fetchone()[0] == 0


@pytest.mark.parametrize('details', [{}, {'actual_minutes':30}, {'actual_guests':1}, {'actual_minutes':0,'actual_guests':1}])
def test_completion_needs_both_positive_details_atomically(client, details):
    ident = submit(client).json()['id']
    admin()
    path = '/studio-api/manage/reservations/'+ident
    assert client.patch(path,json={'status':'confirmed','version':1}).status_code == 200
    response = client.patch(path,json={'status':'completed','version':2,**details})
    assert response.status_code == 422
    with studio.database() as db:
        row = db.execute('SELECT * FROM studio_reservations WHERE id=?', (ident,)).fetchone()
        assert row['status'] == 'confirmed' and row['version'] == 2
        assert row['actual_minutes'] is None and row['actual_guests'] is None
        assert db.execute('SELECT count(*) FROM studio_finance_entries WHERE reservation_id=?', (ident,)).fetchone()[0] == 0


def test_half_hour_completion_and_note_resave_reward_once(client, monkeypatch):
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-08T18:00:00-04:00')
    ident = submit(client).json()['id']
    admin()
    path = '/studio-api/manage/reservations/'+ident
    assert client.patch(path,json={'status':'confirmed','version':1}).status_code == 200
    assert client.patch(path,json={'status':'completed','version':2,'actual_minutes':30,'actual_guests':1}).status_code == 200
    assert client.patch(path,json={'status':'completed','version':3,'staff_note':'Checked'}).status_code == 200
    with studio.database() as db:
        row = db.execute('SELECT * FROM studio_reservations WHERE id=?', (ident,)).fetchone()
        assert row['actual_minutes'] == 30 and row['actual_guests'] == 1
        assert db.execute('SELECT count(*) FROM studio_wallet_ledger WHERE idempotency_key=?', ('visit-reward:'+ident,)).fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM studio_finance_entries WHERE reservation_id=?', (ident,)).fetchone()[0] == 1
