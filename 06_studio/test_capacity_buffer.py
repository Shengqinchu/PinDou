"""Shared public/native/host availability and non-recursive full-capacity padding."""
import json
from test_reservations import client, submit, body, admin, confirm
import app as studio
import reservations as visits


def configure(client, **limits):
    admin()
    policy=client.get('/studio-api/manage/reservation-policy').json()
    result=client.put('/studio-api/manage/reservation-policy',json={'version':policy['version'],**limits})
    assert result.status_code==200, result.text


def grid(client, guests=1, admin_view=False, day='2026-09-08'):
    path='/studio-api/manage/reservation-timetable?start=2026-09-07' if admin_view else '/studio-api/reservation-calendar?guests='+str(guests)
    result=client.get(path)
    assert result.status_code==200, result.text
    return {s['start']:s for d in result.json()['days'] if d['date']==day for s in d['slots']}


def overlap_full(client):
    configure(client,max_concurrent_guests=4,max_concurrent_groups=None)
    first=submit(client,body(start='17:00',end='20:00')).json()['id']
    second=submit(client,body(start='17:30',end='19:30')).json()['id']
    assert confirm(client,first).status_code==200
    assert confirm(client,second).status_code==200
    return first,second


def test_low_seats_agree_across_clients_and_ignore_requested_group_size(client):
    configure(client,max_concurrent_guests=4,max_concurrent_groups=None)
    ref=submit(client,body(start='17:30',end='19:30')).json()['id']
    assert grid(client)['17:30']['remaining_seats']==4  # pending does not hold seats
    assert confirm(client,ref).status_code==200
    one,three,host=grid(client),grid(client,3),grid(client,admin_view=True)
    for time in ('17:30','18:00','18:30','19:00'):
        assert one[time]['available'] and one[time]['remaining_seats']==2 and one[time]['low_capacity']
        assert not three[time]['available'] and three[time]['reason']=='capacity' and three[time]['low_capacity']
        for key in ('remaining_seats','low_capacity','capacity_full','buffered'):
            assert one[time][key]==three[time][key]==host[time][key]
    assert not any(s['buffered'] for s in one.values())
    assert not one['17:00']['low_capacity']


def test_exact_owner_example_has_only_thirty_minutes_padding(client):
    overlap_full(client)
    public,host=grid(client),grid(client,admin_view=True)
    for time in ('17:30','18:00','18:30','19:00'):
        assert public[time]['capacity_full'] and public[time]['remaining_seats']==0
        assert not public[time]['available'] and not public[time]['buffered']
    for time in ('17:00','19:30'):
        assert public[time]['buffered'] and not public[time]['available']
        assert public[time]['reason']=='buffer' and not public[time]['low_capacity']
        assert host[time]['buffered'] and not host[time]['low_capacity']
    assert public['16:30']['available'] and public['20:00']['available']
    assert not public['16:30']['buffered'] and not public['20:00']['buffered']


def test_submission_cannot_cross_buffer_and_exact_boundaries_remain_available(client):
    overlap_full(client)
    assert submit(client,body(start='15:00',end='17:00')).status_code==201
    assert submit(client,body(start='15:30',end='17:30')).status_code==409
    assert submit(client,body(start='19:30',end='21:30')).status_code==409
    assert submit(client,body(start='20:00',end='22:00')).status_code==201
    assert submit(client,body(start='10:00',end='22:00',plan='day')).status_code==409


def test_confirmation_rechecks_new_buffer_in_same_transaction(client):
    configure(client,max_concurrent_guests=4,max_concurrent_groups=None)
    pending=submit(client,body(start='15:30',end='17:30')).json()['id']
    first=submit(client,body(start='17:00',end='20:00')).json()['id']
    second=submit(client,body(start='17:30',end='19:30')).json()['id']
    assert confirm(client,first).status_code==200
    assert confirm(client,second).status_code==200
    response=confirm(client,pending)
    assert response.status_code==409 and response.json()['detail']=='reservation_confirmation_conflict'


def test_cancellation_releases_full_interval_and_its_buffer(client):
    _,second=overlap_full(client)
    assert client.patch('/studio-api/manage/reservations/'+second,json={'version':2,'status':'cancelled'}).status_code==200
    slots=grid(client)
    assert not any(s['buffered'] or s['capacity_full'] for s in slots.values())
    assert slots['17:00']['available'] and slots['17:00']['low_capacity']
    assert slots['19:30']['available'] and slots['19:30']['low_capacity']


def test_group_limit_creates_padding_even_without_total_seat_limit(client):
    configure(client,max_concurrent_groups=1,max_concurrent_guests=None)
    ref=submit(client).json()['id']
    assert confirm(client,ref).status_code==200
    slots=grid(client)
    assert slots['14:00']['capacity_full'] and slots['14:00']['remaining_seats']==0
    assert slots['13:30']['buffered'] and slots['16:00']['buffered']
    assert slots['13:00']['available'] and slots['16:30']['available']
    assert slots['13:00']['remaining_seats'] is None and not slots['13:00']['low_capacity']


def test_unlimited_capacity_and_manual_closure_do_not_create_padding(client):
    admin()
    ref=submit(client).json()['id']
    assert confirm(client,ref).status_code==200
    assert client.post('/studio-api/manage/reservation-blocks',json={'date':'2026-09-08','start':'18:00','end':'19:00','note':'local fixture'}).status_code in (200,201)
    slots=grid(client)
    assert all(s['remaining_seats'] is None and not s['low_capacity'] and not s['buffered'] for s in slots.values())
    assert slots['17:30']['available'] and slots['19:00']['available'] and not slots['18:00']['available']


def test_new_buffers_do_not_reject_saving_policy_for_accepted_legacy_visits(client):
    configure(client,max_concurrent_groups=1,max_concurrent_guests=None)
    refs=[submit(client,body(start=start,end=end)).json()['id'] for start,end in [('10:00','12:00'),('12:00','14:00')]]
    # Existing accepted adjacent bookings predate the padding rule.
    with studio.database() as db:
        db.executemany("UPDATE studio_reservations SET status='confirmed' WHERE id=?",[(r,) for r in refs])
    configure(client,max_guests_per_group=5)
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_reservations WHERE status='confirmed'").fetchone()[0]==2
    configure(client,max_concurrent_guests=4)
    response=client.put('/studio-api/manage/reservation-policy',json={'version':4,'max_concurrent_guests':1})
    assert response.status_code==409


def test_closed_and_past_slots_do_not_show_low_seats_and_days_are_independent(client,monkeypatch):
    configure(client,max_concurrent_guests=2,max_concurrent_groups=None)
    assert not any(s['low_capacity'] for s in grid(client,day='2026-09-09').values() if s['start']>='16:00')
    from datetime import datetime
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,9,8,15,0,tzinfo=visits.ZONE))
    slots=grid(client)
    assert not slots['15:00']['low_capacity'] and slots['15:30']['low_capacity']
    day_grid=visits.capacity_grid([{'date':'2026-09-08','start':'20:00','end':'22:00','guests':2}], '2026-09-09', {'exclusive_groups':False,'max_concurrent_groups':None,'max_concurrent_guests':2})
    assert not any(s['buffered'] or s['capacity_full'] for s in day_grid.values())
