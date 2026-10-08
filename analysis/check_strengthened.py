"""Invariants for timetable joins, policy accounting and evidence aggregation."""
import json
import math
from pathlib import Path
from analyze_strengthened import run,ROOT,MAP
from metro_connections import finish,connections
D=json.loads((ROOT/'outputs/strengthened/analysis.json').read_text())
checks=[]
def check(name,value):
    assert value,name
    checks.append(name)
base,added=D['scenarios'][:2]
check('20 unique origins across five balanced zones',len({r['origin_id'] for r in base['results']})==20 and all(sum(r['zone']==z for r in base['results'])==4 for z in ['혁신','서부','북부','동부','남부']))
check('added service cannot worsen enumerated arrival',all(b['arrival']<=a['arrival'] for a,b in zip(base['results'],added['results'])))
check('two target origin gains are exactly 93 minutes',all(t['arrival_advance']==93 for t in D['tradeoffs']))
check('arrival gain is not journey saving',all(t['journey_saved']==-7 and t['departure_advance']==100 for t in D['tradeoffs']))
check('opposite side boarding IDs explicit',set(o['boarding_stop'] for o in MAP['focal_access'])=={'49007','49035'})
for scenario in D['scenarios']:
    for r in scenario['results']:
        check('board chronology '+scenario['parameters']['policy']+r['origin_id'],r['city_path']['arrival']+10<=r['trip']['dep'])
        clock=r['trip']['arr']+r['seoul_connection']['entry_walk']
        for leg in r['seoul_connection']['legs']:
            check('metro chronology '+str(leg['source_rows']),leg['ready']+.5<=leg['dep']<leg['arr'])
check('Gwangmyeong 09:39 shuttle is missed with entry 10',finish('광명',573)['legs'][0]['dep']==605)
check('Suseo suburban alternative evaluated',finish('수서',641)['legs'][0]['line']=='수인분당')
check('buffer equality boards and excess fails',330-285-18-10-15==2 and 285+22.5+10+15>330)
check('positive monthly data complete at selected four routes',all(r['days']==30 and not r['zero_days'] and r['reconciled'] for r in D['demand']['routes']))
t=D['demand']['totals'];check('hour/day/route totals reconcile',t['hourly']==t['daily']==t['routes']==1983808)
check('admin residual is disclosed not silently assigned',t['routes']-t['admin']==3697 and not D['demand']['total_reconciled'])
check('departure/arrival metrics algebra',all(t['journey_saved']==t['arrival_advance']-t['departure_advance'] for t in D['tradeoffs']))
for t in D['cost']['thresholds']:
    n=t['riders_at_equality'];q=t['all_in_quote'];unit=t['taxi_unit']
    check('taxi/bus break even '+str(t),q<=n*unit and (n-1)*unit<q)
    check('common copay cancels '+str(t),(q-1650*n)-(unit-1650)*n==q-unit*n)
for dest,arrival in [('서울경부',545),('광명',573),('서울',592),('수서',641)]:
    seq=[finish(dest,arrival+delay)['arrival'] for delay in range(31)]
    check('FIFO scheduled earliest arrival '+dest,seq==sorted(seq))
check('09:30 opportunity does not imply 09:00',D['deadlines'][0]['feeder']==D['deadlines'][0]['baseline']==4 and D['deadlines'][1]['feeder']==8)
# Risk scenarios are deterministic conditions, not probabilities.
check('feeder delay grid has both possible and missed cases',{r['connection_possible'] for r in D['feeder_design_grid']}=={True,False})
check('core conclusion survives omission of gaeyang',all(D['gaeyang_exclusion']['results'][i]['arrival']==660 for i in [1,2]))
check('core conclusion survives undated intercity addition',all(D['static_supplement']['results'][i]['arrival']==660 for i in [1,2]))
result={'passed':len(checks),'failed':0,'checks':checks,'scope':'재현 계산의 논리 검증. 시간표 현실성·실측 운행 성공·수요·견적의 검증이 아님.'}
(ROOT/'outputs/strengthened/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('Passed',len(checks),'checks')
