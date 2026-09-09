from test_reservations import client,submit,body,admin
import app as studio

def test_timetable_requires_admin_and_aggregates_beyond_page(client):
    assert client.get('/studio-api/manage/reservation-timetable').status_code==401
    # Clone a valid booking inside the isolated DB; rate-limit tests remain separate.
    assert submit(client).status_code==201
    with studio.database() as db:
        row=dict(db.execute('SELECT * FROM studio_reservations').fetchone())
        for index in range(31):
            row['id']='timetable-'+str(index);row['idempotency_key']='timetable-key-'+str(index)
            db.execute('INSERT INTO studio_reservations('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
    admin();data=client.get('/studio-api/manage/reservation-timetable?start=2026-09-07').json()
    slot=next(s for s in data['days'][1]['slots'] if s['start']=='14:00')
    assert slot['pending']==64 and slot['pending_groups']==32 and slot['confirmed']==0
    assert len(client.get('/studio-api/manage/reservations?day=2026-09-08&at=14:00').json()['items'])==30
    assert client.get('/studio-api/manage/reservations?day=2026-09-08&at=14:00').json()['total']==32
    assert client.get('/studio-api/manage/reservations?day=2026-09-08&at=16:00').json()['total']==0
    assert 'contact' not in str(data) and 'staff_note' not in str(data)

def test_timetable_statuses_boundaries_blocks_and_current_policy(client):
    refs=[submit(client).json()['id'] for _ in range(4)];admin()
    assert client.patch('/studio-api/manage/reservations/'+refs[0],json={'version':1,'status':'confirmed'}).status_code==200
    assert client.patch('/studio-api/manage/reservations/'+refs[1],json={'version':1,'status':'cancelled'}).status_code==200
    assert client.request('DELETE','/studio-api/manage/reservations/'+refs[2],json={'version':1,'reason':'test'}).status_code==200
    data=client.get('/studio-api/manage/reservation-timetable?start=2026-09-07').json()
    slot=next(s for s in data['days'][1]['slots'] if s['start']=='14:00')
    assert slot['confirmed']==2 and slot['pending']==2
    assert not any(s['confirmed'] for s in data['days'][1]['slots'] if s['start']>='16:00')
    assert next(s for s in data['days'][2]['slots'] if s['start']=='16:00')['closed']
    assert client.get('/studio-api/manage/reservations?at=14:00').status_code==422
    assert client.get('/studio-api/manage/reservations?day=2026-09-08&at=14:15').status_code==422
    assert client.post('/studio-api/manage/reservation-blocks',json={'date':'2026-09-11','start':'12:00','end':'14:00','note':'local QA'}).status_code in (200,201)
    data=client.get('/studio-api/manage/reservation-timetable?start=2026-09-07').json()
    assert next(s for s in data['days'][4]['slots'] if s['start']=='12:00')['blocked']
    import json
    with studio.database() as db:
        from reservations import read_policy
        policy=read_policy(db);policy['weekly_hours'][2]['close']='20:00'
        db.execute('UPDATE reservation_policy SET settings=? WHERE id=1',(json.dumps(policy),))
    data=client.get('/studio-api/manage/reservation-timetable?start=2026-09-07').json()
    assert not next(s for s in data['days'][2]['slots'] if s['start']=='16:00')['closed']
