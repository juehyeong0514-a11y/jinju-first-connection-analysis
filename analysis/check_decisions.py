"""Meaningful invariants and fixed counterexamples for the v4 scenarios."""
import json
from collections import defaultdict
from itertools import product
import analyze_decisions as ad
D=json.loads((ad.OUT/'analysis.json').read_text());passed=0;groups=defaultdict(int)
def check(value,group):
    global passed
    assert value,group
    passed+=1;groups[group]+=1

def order(x):return float('inf') if x is None else x
# Default starting time is compatible with every core baseline/feeder result.
for d,t,m,p in product(ad.ar.DATES,ad.ar.TARGETS,ad.MODES,['baseline','feeder']):
    old=ad.ar.run(d,t,m,p);new=ad.run(d,t,m,p)
    for a,b in zip(old['results'],new['results']):
        check(a['origin_id']==b['origin_id'] and a['arrival']==b['arrival'],'v3 default compatibility')
        if b['arrival'] is not None:
            check(b['city_path']['arrival']+10<=b['trip']['dep'],'regional boarding chronology')
            check(b['gateway_arrival_with_shock']==b['trip']['arr'],'zero shock identity')
            check(b['arrival']>=b['trip']['arr'],'final arrival chronology')
for r in D['opportunities']:
    deadline=int(r['deadline'][:2])*60+int(r['deadline'][3:])
    b=ad.run(r['date'],r['target'],r['branch_mode']);f=ad.run(r['date'],r['target'],r['branch_mode'],'feeder')
    for key,res in [('baseline_count',b),('feeder_count',f)]:
        check(r[key]==sum(x['arrival'] is not None and x['arrival']<=deadline for x in res['results']),'deadline membership')
    check(0<=r['baseline_count']<=r['feeder_count']<=20,'opportunity bounds and service preservation')
    check(r['newly_enabled_count']==r['feeder_count']-r['baseline_count'],'opportunity increment')
    check(len(list(filter(None,r['newly_enabled_ids'].split('|'))))==r['newly_enabled_count'],'newly enabled identifiers')
for d,t,m,p in product(ad.ar.DATES,ad.ar.TARGETS,ad.MODES,['baseline','feeder']):
    for grid,parameter in [(ad.STARTS,'earliest_start'),(ad.DELAYS,'coach_delay')]:
        previous=None
        for value in grid:
            result=ad.run(d,t,m,p,**{parameter:value})
            if previous:
                check(all(order(a['arrival'])<=order(b['arrival']) for a,b in zip(previous['results'],result['results'])),parameter+' monotonicity')
            previous=result
for r in D['delay_comparison']:
    check(r['advance']==r['baseline']-r['feeder'],'delay comparison same assumptions')
    check(r['on_time_0930']==(r['feeder']<=570),'09:30 deadline with exact seconds')
    check(r['slack_0930']==570-r['feeder'],'deadline slack')
    check(r['advance']>=0,'added feeder preserves alternatives')
for r in D['conditional_taxi']:
    h,m=map(int,r['latest_pickup_for_first_coach'].split(':'));dep=h*60+m
    h,m=map(int,r['first_coach_departure'].split(':'));coach=h*60+m
    check(dep+r['taxi_minutes']+r['gate']+r['buffer']==coach,'conditional taxi latest pickup')
for r in D['focal_options']:
    check(r['journey_minutes']==r['arrival']-r['departure'],'journey arithmetic')
    check(r['regional_user_cost_won'] is None or r['regional_user_cost_won']>=0,'cost scope')
# Fixed counterexamples prevent optimistic prose from masking missed deadlines.
rows=[r for r in D['delay_comparison'] if r['date']=='2026-10-08' and r['target']=='강남' and r['branch_mode']=='matched' and r['origin_id']=='49008']
check(next(r for r in rows if r['coach_delay']==0)['feeder']==567,'weekday core arrival')
check(next(r for r in rows if r['coach_delay']==10)['feeder']==576.5,'10 minute shock misses 09:30')
check(next(r for r in rows if r['coach_delay']==60)['baseline_hub']=='rail','reoptimization preserves rail fallback')
for oid in ad.FOCAL:
    b=next(r for r in ad.run(earliest_start=300)['results'] if r['origin_id']==oid)
    f=next(r for r in ad.run(policy='feeder',earliest_start=300)['results'] if r['origin_id']==oid)
    check(b['arrival']==f['arrival'],'05:00 availability misses added first feeder')
    taxi=next(r for r in ad.run(policy='taxi')['results'] if r['origin_id']==oid)
    feeder=next(r for r in ad.run(policy='feeder')['results'] if r['origin_id']==oid)
    check(taxi['arrival']==feeder['arrival'] and taxi['trip']==feeder['trip'],'conditional taxi can use same coach')
    check(taxi['city_path']['source']=='conditional_reserved_taxi','taxi path actually selected')
# Additional station entry walking must not improve an otherwise identical result.
for target,road,rail,policy in product(ad.ar.TARGETS,[0,10,30],[0,10],['baseline','feeder']):
    a=ad.run(target=target,coach_delay=road,rail_delay=rail,policy=policy)
    b=ad.run(target=target,coach_delay=road,rail_delay=rail,entry_extra=10,policy=policy)
    check(all(order(x['arrival'])<=order(y['arrival']) for x,y in zip(a['results'],b['results'])),'station entry walking monotonicity')
result={'passed':passed,'groups':dict(groups),'scope':'계산'+' 일관성·반례 검증. 실측 신뢰도·새벽 배차·정시확률·우승 가능성을 검증하지 않음.'}
(ad.OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('v4 invariant checks:',passed,'groups:',len(groups))
