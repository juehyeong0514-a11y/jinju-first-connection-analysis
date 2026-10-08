"""Data, chronology, recovery, bounds and operating-cost invariants for v3."""
import json,math
from collections import Counter
from pathlib import Path
import analyze_robustness as ar
import robust_paths as rp
from robust_cost import evaluate
from metro_connections import connections
ROOT=ar.ROOT;D=json.loads((ROOT/'outputs/robust/analysis.json').read_text());checks=[]
def check(label,value):
    assert value,label
    checks.append(label)
def clock(v):return float('inf') if v is None else v
check('date destination origin coverage',len(D['experiments'])==180 and len(D['comparison'])==300 and len(D['focal_comparison'])==30)
check('housing units not inferred people',D['housing']['related_housing_units']==1825 and sum(int(r['세대수']) for r in D['housing']['housing_rows'])==1825)
check('administrative population arithmetic',D['housing']['admin_men']+D['housing']['admin_women']==D['housing']['admin_population']==33698)
A=D['alias_audit'];check('recovery conservation',A['original_mapped']==1799 and A['recovered_paths']+A['remaining_paths']==471)
check('recovery focal conservation',A['focal_recovered']+A['focal_remaining']==34)
for i,r in enumerate(A['crosswalk']):
    check('alias coordinate evidence '+str(i),r['gap_m']<=3 and r['preceding_stops_checked']>=1 and r['raw_stop']!=r['network_stop'])
check('all earlier 50 exclusions first departures restored',D['branches']['previous_excluded_route_directions']==D['branches']['restored_first_departures']==50)
for i,a in enumerate(D['branches']['all_calendar_checks']):
    strict=set(rp.departures(a['base'],a['direction'],a['day'],'strict'));matched=set(rp.departures(a['base'],a['direction'],a['day'],'matched'));optimistic=set(rp.departures(a['base'],a['direction'],a['day'],'optimistic'))
    check('departure bound subsets '+str(i),strict<=matched<=optimistic)
    check('summary first survives every mode '+str(i),a['first'] in strict)
lookup={tuple(e['parameters'][k] for k in ['date','target','branch_mode','policy']):e for e in D['experiments']}
for ei,e in enumerate(D['experiments']):
    check('20 unique origins '+str(ei),len({r['origin_id'] for r in e['results']})==20)
    check('calendar class '+str(ei),(e['parameters']['city_day'],e['parameters']['metro_day'])==ar.day_classes(e['parameters']['date']))
    for r in e['results']:
        if r['arrival'] is None:continue
        key=str(ei)+' '+r['origin_id'];p=r['city_path'];t=r['trip']
        check('long-distance boards '+key,p['arrival']+e['parameters']['boarding_buffer']<=t['dep']<t['arr']<=r['arrival'])
        check('walk budget '+key,p['walk_minutes']<=20)
        check('no before 04:00 boarding '+key,not p['board_at'] or p['board_at'][0]>=240+p['walk_minutes']+2)
        for j,l in enumerate(r['seoul_connection']['legs']):
            check('metro chronology '+key+' '+str(j),l['ready']+.5<=l['dep']<l['arr']<=r['arrival'])
            choices=connections(l['line'],l['start'],l['end'],e['parameters']['metro_day'])
            check('published metro train pairing '+key+' '+str(j),any(x['train']==l['train'] and x['dep']==l['dep'] and x['arr']==l['arr'] for x in choices))
for date in D['dates']:
    for target in D['targets']:
        for policy in ['baseline','feeder','full150_extra','rail150_1_extra']:
            runs=[lookup[(date,target,m,policy)] for m in ['optimistic','matched','strict']]
            for i in range(20):check('arrival bounds '+date+target+policy+str(i),clock(runs[0]['results'][i]['arrival'])<=clock(runs[1]['results'][i]['arrival'])<=clock(runs[2]['results'][i]['arrival']))
        for mode in ['strict','matched','optimistic']:
            b=lookup[(date,target,mode,'baseline')]
            for policy in ['feeder','full150_extra','rail150_1_extra']:
                f=lookup[(date,target,mode,policy)]
                check('addition preserves existing service '+date+target+mode+policy,all(clock(y['arrival'])<=clock(x['arrival']) for x,y in zip(b['results'],f['results'])))
for t in D['tradeoffs']:
    check('journey and arrival algebra '+t['origin_id'],t['journey_saved']==t['arrival_advance']-t['departure_advance']==-12 and t['policy_journey']-t['baseline_journey']==12)
check('weekday Gangnam focal robust 93',all(r['advance']==93 and r['baseline']==r['optimistic_baseline']==r['strict_baseline']=='11:00' for r in D['focal_comparison'] if r['date'] in D['dates'][:3] and r['target']=='강남'))
check('Saturday focal differences retained',len({r['baseline'] for r in D['focal_comparison'] if r['date']=='2026-10-17' and r['target']=='강남'})==2)
check('Sunday adaptive dispatch works',lookup[('2026-10-18','강남','matched','feeder')]['results'][1]['arrival_hhmm']=='09:05')
check('Sunday fixed 04:45 misses first coach',D['old_fixed_0445_weekend'][-1]['results'][1]['arrival_hhmm']=='10:59')
check('Sunday full150 adaptive addition works',lookup[('2026-10-18','강남','matched','full150_extra')]['results'][1]['arrival_hhmm']=='09:05')
for r in D['calendar_dispatch']:check('stress planning slack '+r['date'],r['first_coach']-r['stress_ready']-r['stress_buffer']==r['stress_slack']==2.5)
for r in D['seat_snapshots']:
    for p in r['results']:
        if p.get('trip',{}).get('mode')=='express':check('zero seat coach excluded '+r['parameters']['date']+p['origin_id'],p['trip']['remaining_seats']>0)
for i,r in enumerate(D['cost']['grid']):
    check('cost capacity and accounting '+str(i),r['feeder_vehicles']==math.ceil(r['confirmed']/r['seats_per_feeder']) and r['served_within_reserved_capacity'] and r['reserved_taxis']>=r['active_taxis'] and r['feeder_gross']==r['feeder_vehicles']*r['quote_per_feeder'] and r['feeder_public']==max(0,r['feeder_gross']-1650*r['actual']) and r['taxi_public']==max(0,r['taxi_gross']-1650*r['actual']))
check('independent parties never combined',evaluate([1]*12)['reserved_taxis']==12 and evaluate([2]*6)['reserved_taxis']==6 and evaluate([3]*4)['reserved_taxis']==4)
check('seat overflow adds vehicle',evaluate([1]*12,seats=8)['feeder_vehicles']==2)
check('cancel before contract reduces taxi reservations',evaluate([1]*12,cancellations=4)['reserved_taxis']==8)
check('late absence retains fixed contract',evaluate([1]*12,no_shows=4)['feeder_gross']==60000)
check('unused taxi fee monotonic', [evaluate([1]*12,no_shows=4,no_show_fee=a)['taxi_gross'] for a in [0,.5,1]]==[40000,50000,60000])
check('empty dispatch costs zero',evaluate([])['feeder_gross']==evaluate([])['taxi_gross']==0)
for kwargs in [dict(seats=0),dict(seats=1.5),dict(taxi=-1),dict(quote=-1),dict(copay=-1),dict(no_shows=13),dict(cancellations=.5),dict(no_show_fee=1.1)]:
    try:evaluate([1]*12,**kwargs)
    except ValueError:check('reject invalid input '+str(kwargs),True)
    else:check('reject invalid input '+str(kwargs),False)
check('published demand sum reconciliation',D['demand']['totals']['routes']==D['demand']['totals']['daily']==D['demand']['totals']['hourly']==1983808)
check('admin aggregate residual visible',D['demand']['totals']['routes']-D['demand']['totals']['admin']==3697)
check('undated supplement does not improve focal baseline',all(r['arrival']==660 for r in D['undated_supplement']['results'] if r['origin_id'] in ['49008','49036']))
result={'passed':len(checks),'failed':0,'checks':checks,'scope':'공개 캐시의 순서·자료 대응·경계·비용 논리 검사. 실제 운행 성공률·신규 수요·계약 견적 검증이 아니다.'}
(ROOT/'outputs/robust/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('Passed',len(checks),'checks')
