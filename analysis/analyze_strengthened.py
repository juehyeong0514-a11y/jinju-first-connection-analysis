"""Public-data strengthening: 20 origins, scheduled Seoul transfers, demand/cost.
No ridership forecast, causal estimate, measured reliability, or global optimum.
"""
import csv
import json
import math
from collections import Counter
from functools import lru_cache
from itertools import product
from pathlib import Path
import analyze_connections as ac
from metro_connections import finish
from audit_arrival_tradeoffs import latest_direct_start
ROOT=ac.ROOT; OUT=ROOT/'outputs/strengthened'; RAW=ROOT/'data/raw/strengthening'
SAMPLE=json.loads((OUT/'sample_selection.json').read_text())
MAP=json.loads((RAW/'map_checks.json').read_text())
def configure():
    origins=SAMPLE['origins'] if isinstance(SAMPLE,dict) else SAMPLE
    ac.ORIGINS=[(r['id'],r['name'],r['zone']) for r in origins]
    ac.DIRECT=json.loads((OUT/'direct_paths.json').read_text())
    ac.SUGGESTED=json.loads((OUT/'suggested_paths.json').read_text())
configure()

def pathways(policy='baseline',factor=1,walk_cap=20,gate=5,feeder_start=285,feeder_minutes=15):
    paths,missing=ac.approach(walk_cap,factor,policy if policy!='feeder_0445' else 'baseline')
    # Explicitly account for terminal/platform access on all walking candidates.
    for p in paths:
        p['arrival'] += gate if p['source']=='map_walk' else gate-5
    for r in MAP['additional_walks']:
        if r['minutes']<=walk_cap:
            paths.append(dict(origin_id=r['origin_id'],hub=r['hub'],arrival=240+r['minutes']+gate,source='map_walk',routes=['도보'],board_at=[],walk_minutes=r['minutes'],new_service=False))
    if policy=='feeder_0445':
        for oid,stop,b in [('49036','49035',0),('49008','49007',6)]:
            w=ac.walk(oid,stop)
            if w<=walk_cap and 240+w+2<=feeder_start+b*factor:
                paths.append(dict(origin_id=oid,hub='innovation',arrival=feeder_start+feeder_minutes*factor+gate,source='policy_feeder',routes=['추가 연계편'],board_at=[feeder_start+b*factor],walk_minutes=w,boarding_stop=stop,new_service=True))
    return paths,missing

@lru_cache(None)
def run(policy='baseline',factor=1,walk_cap=20,buffer=10,gate=5,coach_delay=0,entry_extra=0,feeder_start=285,feeder_minutes=15,include_static=False,exclude_gaeyang=False):
    paths,missing=pathways(policy,factor,walk_cap,gate,feeder_start,feeder_minutes)
    results=[];trips=ac.services()
    for oid,name,zone in ac.ORIGINS:
        candidates=[]
        for p in paths:
            if p['origin_id']!=oid:continue
            for t in trips:
                if p['hub']!=t['hub'] or (not include_static and not t['dated']):continue
                if exclude_gaeyang and t['hub']=='gaeyang':continue
                if p['arrival']+buffer>t['dep']:continue
                delayed=t['arr']+(coach_delay if t['mode']!='train' else 0)
                last=finish(t['destination'],delayed,'DAY',entry_extra)
                if last:candidates.append(dict(origin_id=oid,origin=name,zone=zone,arrival=last['arrival'],arrival_hhmm=ac.hhmm(last['arrival']),city_path=p,trip=t,seoul_connection=last,boarding_slack=t['dep']-p['arrival']-buffer))
        results.append(min(candidates,key=lambda r:(r['arrival'],r['city_path']['arrival'])) if candidates else dict(origin_id=oid,origin=name,zone=zone,arrival=None,arrival_hhmm='미확인'))
    return dict(parameters=dict(policy=policy,city_runtime_multiplier=factor,walk_cap=walk_cap,boarding_buffer=buffer,gate_walk=gate,coach_delay=coach_delay,seoul_entry_extra=entry_extra,feeder_start=feeder_start,feeder_minutes=feeder_minutes,include_static=include_static,exclude_gaeyang=exclude_gaeyang),results=results,evaluated_paths=len(paths),unusable_paths=missing)

def demand():
    p=RAW/'its';period='20260901_20260930'
    def read(name,suffix=''):return json.loads((p/f'{name}_{period}{suffix}.json').read_text())
    routes={r['routeNo']:r['rideCnt'] for r in read('selectBusRidePersonPerLine')};result=[]
    for route in ['150','150-1','300','251']:
        hourly=read('selectRidePersonPerTime',f'_route{route}');daily=read('selectRidePersonPerDay',f'_route{route}')
        hs=sum(int(r['rideCnt']) for r in hourly);ds=sum(r['rideCnt'] for r in daily)
        result.append(dict(route=route,monthly_boardings=routes[route],hourly_total=hs,daily_total=ds,days=len(daily),zero_days=[r['rungDt'] for r in daily if r['rideCnt']==0],reconciled=hs==ds==routes[route],hour05=int(next(r['rideCnt'] for r in hourly if r['category']=='05시')),hour06=int(next(r['rideCnt'] for r in hourly if r['category']=='06시'))))
    admin=read('selectBusRideCntPerAdmnstrt')['data'];allhours=read('selectRidePersonPerTime');alldays=read('selectRidePersonPerDay')
    totals=dict(hourly=sum(int(r['rideCnt']) for r in allhours),daily=sum(r['rideCnt'] for r in alldays),routes=sum(routes.values()),admin=sum(r['rideCnt'] for r in admin))
    return dict(period='2026-09-01 ~ 2026-09-30',unit='승차 건수(연인원); 고유 이용자 수 아님',routes=result,admin=admin,totals=totals,total_reconciled=len(set(totals.values()))==1,limits=['노선·시간대 집계는 신규 연계편 수요나 서울행 수요가 아님','승차·하차 기록을 완전한 OD로 해석하지 않음','운행 전 04시 승차 0은 잠재수요 0을 뜻하지 않음','10/7 전 노선 일별 0은 미집계 가능성이 있어 10월 자료는 주 추정에 사용하지 않음'])

def cost():
    # Q is an all-in quote, not a cost estimate; same co-pay cancels at crossover.
    taxi=[4600,5000,6000,8000];quotes=[30000,60000,90000,120000]
    return dict(unit='원/운행일 1회',copay=1650,taxi_reference={r['origin_id']:r['taxi_won'] for r in MAP['focal_access']},taxi_assumption='1인 1대, 합승 없음. 6000/8000은 호출·예약 할증을 포함해 보는 가정 시나리오.',quote_assumption='30000~120000은 실제 견적이 아닌 의사결정 격자. 운전자 유급시간·회송·차량·배차·보험 등 포함 견적 필요.',thresholds=[dict(all_in_quote=q,taxi_unit=t,riders_at_equality=math.ceil(q/t)) for q,t in product(quotes,taxi)],max_acceptable_quotes=[dict(riders=n,at_4600=n*4600,at_5000=n*5000,at_8000=n*8000) for n in [2,4,6,8,12,16,20]],formula='고정편 순지원액=max(0,Q-1650N); 개별지원=N max(0,T-1650). Q>=1650N, T>=1650이면 Q<=NT일 때 고정편이 개별지원보다 저렴. 좌석·배차 보장 조건 별도.',limits=['확정수요·운송원가를 관측하지 않았으므로 B/C, 실현 절감액, 적정 대수를 추정하지 않음','예약 인원은 장거리 승차권 보유자 중 이용 확정 인원; 단순 클릭·설문 의향과 구분','운행 거리만으로 추가비용을 산정하지 않음'])

def main():
    scenarios=[run(policy=p) for p in ['baseline','feeder_0445','full150_extra','rail150_1_extra']]
    baseline,feeder=scenarios[:2];trade=[]
    # Update imported audit module globals to use expanded direct candidates.
    import audit_arrival_tradeoffs as audit
    audit.DIRECT=ac.DIRECT
    for obs in MAP['focal_access']:
        oid=obs['origin_id'];old=next(r for r in baseline['results'] if r['origin_id']==oid);new=next(r for r in feeder['results'] if r['origin_id']==oid)
        p,missing=audit.latest_direct_start(oid,old['trip'])
        assert p['boarding_stop']==obs['boarding_stop'],(oid,p['boarding_stop'])
        # Nominal 2-min boarding buffer in both; separate ±7 passing-time case.
        start_old=p['board_at']-obs['walk_minutes']-2
        start_new=(285 if oid=='49036' else 291)-obs['walk_minutes']-2
        trade.append(dict(origin_id=oid,origin=old['origin'],start_definition=obs['start'],access_walk=obs['walk_minutes'],baseline_start=start_old,policy_start=start_new,baseline_arrival=old['arrival'],policy_arrival=new['arrival'],arrival_advance=old['arrival']-new['arrival'],departure_advance=start_old-start_new,baseline_journey=old['arrival']-start_old,policy_journey=new['arrival']-start_new,journey_saved=(old['arrival']-start_old)-(new['arrival']-start_new),baseline_local=p,early_passing_allowance=7,baseline_start_with_7min_allowance=start_old-7,journey_saved_with_7min_allowance=(old['arrival']-(start_old-7))-(new['arrival']-start_new),missing_full_timetables=missing))
    deadlines=[dict(deadline=ac.hhmm(t),baseline=sum(r['arrival'] is not None and r['arrival']<=t for r in baseline['results']),feeder=sum(r['arrival'] is not None and r['arrival']<=t for r in feeder['results']),sample_size=20) for t in [540,570,600,630,660]]
    # Focal design feasibility grid, not empirical success probability.
    grid=[]
    for start,runtime,gate,buffer in product([280,285,290],[15,18,22.5],[5,10],[10,15]):
        ready=start+runtime+gate;grid.append(dict(start=start,runtime=runtime,gate=gate,buffer=buffer,ready=ready,slack=330-ready-buffer,connection_possible=ready+buffer<=330))
    arrival_grid=[]
    for delay,extra in product([0,5,10,20,30],[0,5,10]):
        f=finish('서울경부',545+delay,'DAY',extra);arrival_grid.append(dict(coach_delay=delay,entry_extra=extra,arrival=f['arrival'],by0930=f['arrival']<=570,by1000=f['arrival']<=600))
    conflicts=[dict(base=b,direction=d,**ac.timetable_quality(b,d)) for b in ac.FIRST_ROWS for d in ['1','2'] if ac.timetable_quality(b,d)['status']=='conflict']
    result=dict(date='2026-10-08',scope='2026-10-08 평일 공개 시간표 기반, 열거한 직접/1회환승 후보 중 가장 이른 결과. 실제 관측·전체망 최적해·인구대표 추정 아님.',assumptions=dict(origin_start=240,external_walk_cap=20,local_gate_walk=5,local_boarding_buffer=2,longdistance_buffer=10,seoul_exit_walk=3),scenarios=scenarios,tradeoffs=trade,deadlines=deadlines,feeder_design_grid=grid,arrival_delay_grid=arrival_grid,walking_focus_sensitivity=[dict(cap=c,eligible_POIs=[o['origin_id'] for o in MAP['focal_access'] if o['coach_walk_minutes']<=c]) for c in [10,20,30,40]],static_supplement=run(include_static=True),gaeyang_exclusion=run(exclude_gaeyang=True),runtime_sensitivity=[run(policy=p,factor=1.2,buffer=15) for p in ['baseline','feeder_0445']],timetable_conflicts=conflicts,demand=demand(),cost=cost())
    (OUT/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    with (OUT/'arrival_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['권역','표본 정류장','기존','연계편04:45','150추가','150-1추가','기존 경유지','기존 시내 접근'])
        for i,r in enumerate(baseline['results']):writer.writerow([r['zone'],r['origin']]+[s['results'][i]['arrival_hhmm'] for s in scenarios]+[r.get('trip',{}).get('hub'),'+'.join(r.get('city_path',{}).get('routes',[]))])
    print('RESULTS',[(r['origin'],r['arrival_hhmm']) for r in baseline['results']]);print('DEADLINES',deadlines);print('DEMAND',result['demand']['totals']);print('TRADEOFFS',[{k:v for k,v in r.items() if k!='baseline_local'} for r in trade])
if __name__=='__main__':main()
