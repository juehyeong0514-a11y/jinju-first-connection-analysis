"""Meaningful consistency checks on cached data and scenario calculations."""
from analyze_connections import *

assert dated_minute('202610090035') == 1475
assert dated_minute('202610082400') == 1440
assert offset(('NOT_A_ROUTE','00001','00002')) is None
assert timetable_quality('381001010','1')['status']=='conflict'
assert departures('381001010','1')==[], 'Conflicting schedules must not be silently combined'
assert not any(p['source']=='policy_feeder' for p in approach(walk_cap=1,policy='feeder_0450')[0])
trips=services()
assert all(t['arr']>=t['dep'] for t in trips), 'A trip arrives before it departs'
base=run()
for policy in ['baseline','feeder_0450','full150_extra','rail150_1_extra']:
    output=run(policy=policy)
    for before,after in zip(base['results'],output['results']):
        assert after['arrival']<=before['arrival'], 'Adding a service cannot worsen the optimum'
        assert after['city_path']['arrival']+10<=after['trip']['dep']
        assert after['arrival']==after['trip']['arr']+after['trip']['last_mile']
previous=None
for cap in [10,20,30,40]:
    current=run(walk_cap=cap)['results']
    if previous:
        assert all(b['arrival']<=a['arrival'] for a,b in zip(previous,current)), 'More walking options cannot worsen the optimum'
    previous=current
for buffer in [5,10,15]:
    for factor in [1,1.2]:
        output=run(policy='feeder_0450',buffer=buffer,factor=factor)
        for origin in ['49008','49036']:
            result=next(r for r in output['results'] if r['origin_id']==origin)
            assert result['trip']['dep']==330, 'Feeder must retain 05:30 connection in tested uncertainty range'
from audit_arrival_tradeoffs import audit
for row in audit()['tradeoffs']:
    assert row['arrival_advance_minutes']==row['departure_advance_minutes']+row['journey_minutes_saved']
print('PASS: dates, missing/conflicting inputs, chronological connections, additive policies, walking limits, feeder stress, arrival-vs-duration identity')
