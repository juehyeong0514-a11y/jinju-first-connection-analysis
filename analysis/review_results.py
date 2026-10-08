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
