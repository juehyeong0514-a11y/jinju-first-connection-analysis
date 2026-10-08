"""Credential-free review of the published comparison and operating costs.

This reviews the derived table, not the source timetable joins. For the full
routing reproduction use RUN_ANALYSIS.txt with the separately supplied cache.
"""
import csv,json
from pathlib import Path
from robust_cost import evaluate
ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'outputs/robust/calendar_destination_comparison.csv').open(encoding='utf-8-sig')))
assert len(rows)==300 and len({(r['date'],r['target'],r['origin_id']) for r in rows})==300
focal=[r for r in rows if r['origin_id'] in ['49008','49036']]
weekday=[r for r in focal if r['target']=='강남' and r['date'] in ['2026-10-08','2026-10-13','2026-10-15']]
assert len(weekday)==6 and all(float(r['advance'])==93 and r['baseline']==r['optimistic_baseline']==r['strict_baseline']=='11:00' and r['feeder']=='09:27' for r in weekday)
assert evaluate([1]*12)['reserved_taxis']==12 and evaluate([2]*6)['reserved_taxis']==6
assert evaluate([1]*12,seats=8)['feeder_vehicles']==2
print('Published comparisons:',len(rows),'Focal weekday Gangnam: 11:00 -> 09:27 (93 min)')
for r in focal:
 if r['target']=='강남' and r['date'] in ['2026-10-17','2026-10-18']:
  print(r['date'],r['origin'],r['baseline'],'->',r['feeder'],'branch bounds',r['optimistic_baseline'],r['strict_baseline'])
print('Cost assumptions: 12 independent parties -> 12 taxis; 6 two-person parties -> 6 taxis; 12 passengers / 8 feeder seats -> 2 feeders')
print('This review does not reproduce the original route joins or measure real service reliability.')

# Independent review of v4 aggregate scenarios; source route joins need caches.
def load_rows(name):
 return list(csv.DictReader((ROOT/'outputs/decisions'/name).open(encoding='utf-8-sig')))
ops=load_rows('arrival_opportunities.csv');dep=load_rows('departure_constraints.csv');delay=load_rows('delay_comparison.csv');taxi=load_rows('conditional_taxi.csv');options=load_rows('focal_options.csv')
assert (len(ops),len(dep),len(delay),len(taxi),len(options))==(225,540,450,360,8)
for r in ops:
 assert 0<=int(r['baseline_count'])<=int(r['feeder_count'])<=20
 assert int(r['newly_enabled_count'])==int(r['feeder_count'])-int(r['baseline_count'])
for r in delay:
 assert float(r['advance'])==float(r['baseline'])-float(r['feeder'])
 assert float(r['slack_0930'])==570-float(r['feeder'])
 assert (r['on_time_0930']=='True')==(float(r['feeder'])<=570)
example=[r for r in delay if r['date']=='2026-10-08' and r['target']=='강남' and r['branch_mode']=='matched' and r['origin_id']=='49008']
assert next(r for r in example if r['coach_delay']=='10')['feeder_hhmm']=='09:37'
assert next(r for r in example if r['coach_delay']=='60')['baseline_hub']=='rail'
for r in dep:
 if r['date']=='2026-10-08' and r['target']=='강남' and r['earliest_start']=='05:00':assert r['baseline']==r['feeder']
def minute(text):
 h,m=map(int,text.split(':'));return h*60+m
for r in taxi:
 assert minute(r['latest_pickup_for_first_coach'])+int(r['taxi_minutes'])+int(r['gate'])+int(r['buffer'])==minute(r['first_coach_departure'])
for r in options:assert float(r['journey_minutes'])==float(r['arrival'])-float(r['departure'])
print('v4: 225 deadline counts, 540 departure cases, 450 road-delay comparisons, 360 conditional taxi cases')
print('Counterexamples: 09:00 no added focal opportunity; +10 min coach delay -> 09:37; 05:00 availability misses feeder')
print('Taxi: a booked vehicle at the mapped point can use the same first coach; availability, fare and delay probabilities were not measured.')

walk=load_rows('walking_sensitivity.csv');points=load_rows('walking_point_options.csv')
assert len(walk)==360 and len(points)==30
for r in walk:
 assert float(r['advance'])==float(r['baseline'])-float(r['feeder'])
 assert float(r['baseline_local_walk'])<=float(r['walk_cap'])
 if r['walk_cap']=='40':assert float(r['advance'])==0 and r['baseline_source']=='map_walk'
for r in points:
 assert float(r['latest_departure'])+float(r['walk_minutes'])+15==minute(r['first_coach'])
 assert r['regional_fare']=='0'
print('v5 walking: 40 minute allowance removes the focal marginal arrival gain; actual walking needs were not surveyed.')
