"""The owner confirmed that exactly two hours remains available."""
import json
import pytest
import app as studio
from test_reservations import client, body, submit, confirm, admin
from test_capacity_buffer import configure, grid


def block(client, start, end, day='2026-09-08'):
    admin()
    result = client.post('/studio-api/manage/reservation-blocks', json={'date':day,'start':start,'end':end,'note':'gap fixture'})
    assert result.status_code in (200,201), result.text


@pytest.mark.parametrize('end,closed', [('12:30',True),('13:00',True),('13:30',True),('14:00',False),('14:30',False)])
def test_internal_runs_and_exact_two_hour_boundary(client, end, closed):
    block(client,'10:00','12:00')
    block(client,end,'18:00')
    public,host=grid(client),grid(client,admin_view=True)
    assert public['12:00']['gap_blocked'] is closed
    assert public['12:00']['available'] is not closed
    assert host['12:00']['gap_blocked'] is closed
    assert public['12:00']['reason']==('short_gap' if closed else None)
    assert not any(s['buffered'] for s in public.values()), 'A gap must not generate recursive padding'
    assert public['18:00']['available']


def test_short_opening_and_closing_fragments(client):
    block(client,'11:00','20:30')
    public,host=grid(client),grid(client,admin_view=True)
    for at in ('10:00','10:30','20:30','21:00','21:30'):
        assert public[at]['gap_blocked'] and not public[at]['available']
        assert host[at]['gap_blocked'] and not host[at]['available']


def test_exact_two_hours_at_both_opening_boundaries_is_bookable(client):
    block(client,'12:00','20:00')
    slots=grid(client)
    assert slots['10:00']['available'] and slots['20:00']['available']
    assert submit(client,body(start='10:00',end='12:00')).status_code==201
    assert submit(client,body(start='20:00',end='22:00')).status_code==201


def test_uses_actual_wednesday_closing_time(client):
    block(client,'12:30','14:30',day='2026-09-09')
    public=grid(client,day='2026-09-09')
    assert public['10:00']['available']
    assert public['14:30']['gap_blocked'] and public['15:30']['gap_blocked']
    assert public['16:00']['closed'] and not public['16:00']['gap_blocked']


def test_capacity_buffers_are_applied_before_gap_closure_and_cancel_reopens(client):
    configure(client,max_concurrent_groups=1,max_concurrent_guests=None)
    first=submit(client,body(start='10:00',end='12:00')).json()['id']
    second=submit(client,body(start='14:30',end='16:30')).json()['id']
    assert confirm(client,first).status_code==200
    assert confirm(client,second).status_code==200
    slots=grid(client)
    assert slots['12:00']['buffered'] and slots['14:00']['buffered']
    assert all(slots[at]['gap_blocked'] for at in ('12:30','13:00','13:30'))
    assert slots['17:00']['available'] and not slots['17:00']['buffered']
    assert client.patch('/studio-api/manage/reservations/'+second,json={'version':2,'status':'cancelled'}).status_code==200
    assert grid(client)['12:30']['available']


def test_gap_uses_selected_party_size_not_just_occupied_intervals(client):
    configure(client,max_concurrent_guests=4,max_concurrent_groups=None)
    for start,end in [('10:00','12:00'),('13:30','15:30')]:
        payload=body(start=start,end=end)
        payload['booking']['guests']=2
        ref=submit(client,payload).json()['id']
        assert confirm(client,ref).status_code==200
    one,three=grid(client,1),grid(client,3)
    assert one['12:00']['available'] and not one['12:00']['gap_blocked']
    assert not three['12:00']['available'] and three['12:00']['gap_blocked']
    assert not any(s['buffered'] for s in three.values())


def test_pending_does_not_create_gap_and_reads_preserve_bookings(client):
    configure(client,max_concurrent_groups=1,max_concurrent_guests=None)
    ref=submit(client,body(start='11:00',end='21:00')).json()['id']
    with studio.database() as db:
        before=[tuple(r) for r in db.execute('SELECT * FROM studio_reservations ORDER BY id')]
    slots=grid(client)
    assert slots['10:00']['available'] and not any(s['gap_blocked'] for s in slots.values())
    grid(client,admin_view=True)
    with studio.database() as db:
        assert before==[tuple(r) for r in db.execute('SELECT * FROM studio_reservations ORDER BY id')]


def test_unbookable_fragment_cannot_be_used_to_cross_a_closed_interval(client):
    block(client,'10:00','12:00')
    block(client,'13:30','18:00')
    result=submit(client,body(start='12:00',end='14:00'))
    assert result.status_code==409
