"""Corrections 1–4: housing scale, branch bounds, calendars/destinations, cost.

Everything runs offline from cached official public inputs. No probability,
observed travel-time, actual incremental demand or operator quote is inferred.
"""
import csv
import io
import json
from collections import Counter
from datetime import date
from functools import lru_cache
from itertools import product
from pathlib import Path
import robust_paths as rp
from robust_metro import finish_target
from robust_cost import scenarios as cost_scenarios
from metro_connections import mins

ac=rp.ac;ROOT=ac.ROOT;RAW=ROOT/'data/raw/strengthening/robust';OUT=ROOT/'outputs/robust'
DATES=['2026-10-08','2026-10-13','2026-10-15','2026-10-17','2026-10-18']
TARGETS=['강남','서울역','사당']

def day_classes(value):
    w=date.fromisoformat(value).weekday()
    return ('3','SAT') if w==5 else ('4','END') if w==6 else ('1','DAY')

@lru_cache(None)
def services(value):
    if value=='2026-10-08': return ac.services()
    trips=[]
    observed=json.loads((RAW/'kobus_calendar.json').read_text())
    for r in observed['records']:
        if r['date']!=value: continue
        for i,s in enumerate(r['departures']):
            dep=mins(s+':00')
            trips.append({'hub':r['hub'],'mode':'express','dep':dep,'arr':dep+r['duration'],
                          'destination':'서울경부','label':'KOBUS 공시','dated':True,
                          'remaining_seats':r['remaining_seats'][i],'total_seats':r['total_seats'][i],
                          'arrival_basis':'공시 소요예상시간, 실제 도착 아님',
                          'source':'data/raw/strengthening/robust/kobus_calendar.json'})
    # Daily official KTX worksheet completes TAGO's known future-date gaps.
    # Intermediate station values are published station times (conservatively
    # later than arrival when a departure is printed); terminal Seoul/Suseo
    # values are destination times. Do not call this an actual arrival record.
    for r in json.loads((RAW/'ktx_morning_rows.json').read_text()):
        if r['비고']!='매일': raise ValueError('Unhandled train calendar')
        for dest in ['서울','광명','수서']:
            if r[dest]=='00:00:00': continue
            trips.append({'hub':'rail','mode':'train','dep':mins(r['진주']),'arr':mins(r[dest]),
                          'destination':dest,'label':r['편성']+' '+r['열차번호'],'dated':True,
                          'arrival_basis':'2026-10-01 공식 열차 시각표(매일); 중간역 공시 시각',
                          'source':'data/raw/strengthening/korail_ktx_20261001.xlsx'})
    return trips

def first_coach(value):
    return min(t['dep'] for t in services(value) if t['hub']=='innovation' and t['mode']=='express')

@lru_cache(None)
def run(value='2026-10-08',target='강남',mode='matched',policy='baseline',
        factor=1,buffer=10,gate=5,seat_filter=False,fixed_start=None,include_static=False):
    city_day,metro_day=day_classes(value)
    start=first_coach(value)-50 if fixed_start is None else fixed_start
    paths,missing=rp.pathways(city_day,mode,policy,factor,20,gate,start)
    trips=services(value)
    results=[]
    for oid,name,zone in ac.ORIGINS:
        # The earliest ready time at a hub dominates later paths to that hub.
        best={}
        for p in paths:
            if p['origin_id']!=oid: continue
            if p['hub'] not in best or p['arrival']<best[p['hub']]['arrival']:best[p['hub']]=p
        candidates=[]
        for t in trips:
            if not t['dated'] and not include_static: continue
            if seat_filter and t.get('remaining_seats',1)<1: continue
            p=best.get(t['hub'])
            if not p or p['arrival']+buffer>t['dep']:continue
            last=finish_target(t['destination'],t['arr'],metro_day,target)
            if last:
                candidates.append({'origin_id':oid,'origin':name,'zone':zone,
                                   'arrival':last['arrival'],'arrival_hhmm':ac.hhmm(last['arrival']),
                                   'city_path':p,'trip':t,'seoul_connection':last,
                                   'boarding_slack':t['dep']-p['arrival']-buffer})
        results.append(min(candidates,key=lambda r:(r['arrival'],r['city_path']['arrival'])) if candidates else
                       {'origin_id':oid,'origin':name,'zone':zone,'arrival':None,'arrival_hhmm':'미확인'})
    return {'parameters':{'date':value,'target':target,'branch_mode':mode,'policy':policy,
                          'city_day':city_day,'metro_day':metro_day,'runtime_multiplier':factor,
                          'boarding_buffer':buffer,'gate':gate,'feeder_start':start,
                          'seat_snapshot_filter':seat_filter,'include_static':include_static},
            'evaluated_paths':len(paths),'missing_offsets':missing,'results':results}

def housing():
    b=(RAW/'jinju_housing_20260701.csv').read_bytes()
    rows=[{k.strip():v for k,v in r.items()} for r in csv.DictReader(io.StringIO(b.decode('cp949')))]
    selected=[r for r in rows if r['아파트명'] in ['혁신도시NHF10단지','한림풀에버']]
    pop=json.loads((RAW/'population_source.json').read_text())
    return {'housing_reference_date':'2026-07-01','housing_source':'https://www.data.go.kr/data/15046124/fileData.do',
            'housing_rows':[{k:r[k] for k in ['연번','아파트명','새주소','세대수','동수']} for r in selected],
            'related_housing_units':sum(int(r['세대수']) for r in selected),
            'admin_reference_date':pop['reference_date'],'admin_name':'충무공동','admin_population':pop['population'],
            'admin_registered_households':pop['households'],'admin_men':pop['men'],'admin_women':pop['women'],
            'admin_source':pop['source'],
            'limits':['1,825호는 관련 두 단지의 주택 규모이며 실제 수혜 가구·거주 인구·새벽 서울행 승객 수가 아니다.',
                      '단지 내 모든 동·출입구에서 동일한 보행 조건이나 연결 공백을 확인한 것은 아니다.',
                      '행정동 전체 인구를 두 단지에 배분하지 않고, 평균 가구원수로 단지 인구를 만들어내지 않는다.',
                      '차량 미보유·근로시간·서울행 목적을 개인이나 가구 수준에서 관측하지 않았다.']}

def branch_audits():
    old=json.loads((ROOT/'outputs/strengthened/analysis.json').read_text())['timetable_conflicts']
    restored=[rp.branch_audit(r['base'],r['direction']) for r in old]
    all_checks=[]
    bases={str(p['source_route_id']) for p in ac.DIRECT}
    bases.update(l['base'] for p in ac.SUGGESTED for l in p['legs'])
    for day in ['1','3','4']:
        for base in sorted(bases):
            for direction in ['1','2','3']:
                a=rp.branch_audit(base,direction,day)
                if a['first'] is not None:all_checks.append(a)
    return {'previous_excluded_route_directions':len(old),'restored_first_departures':sum(r['first_present'] for r in restored),
            'previous_exclusions':restored,'all_calendar_checks':all_checks,
            'interpretation':'상세표가 노선번호 묶음이므로 그 최솟값과 지선 첫차의 차이를 모순으로 단정한 기존 제외 규칙을 폐기했다. 동일 비고 매칭은 후보이며 확정 지선 배정이 아니다. 첫·막차만 사용하는 보수적 결과와 모든 묶음 운행을 허용하는 낙관적 경계를 함께 보고한다.'}

def focal_tradeoffs():
    base=run();policy=run(policy='feeder');out=[]
    for obs in rp.strengthened.MAP['focal_access']:
        oid=obs['origin_id'];old=next(r for r in base['results'] if r['origin_id']==oid)
        new=next(r for r in policy['results'] if r['origin_id']==oid)
        starts=[]
        for p in ac.DIRECT:
            if p['origin_id']!=oid or p['boarding_stop']!=obs['boarding_stop'] or p['hub']!=old['trip']['hub']:continue
            board=ac.offset(tuple(p['origin_time_key']) if p['origin_time_key'] else None);end=ac.offset(tuple(p['arrival_time_key']))
            if board is None or end is None or end<board:continue
            for dep in rp.departures(p['source_route_id'],p['direction'],'1','matched'):
                if dep+end+5+10<=old['trip']['dep']:
                    starts.append({'start':dep+board-obs['walk_minutes']-2,'base':p['source_route_id'],
                                   'direction':p['direction'],'route':p['route_label'],'departure':dep})
        latest=max(starts,key=lambda r:r['start'])
        new_start=new['city_path']['board_at'][0]-obs['walk_minutes']-2
        advance=old['arrival']-new['arrival'];departure_advance=latest['start']-new_start
        out.append({'origin_id':oid,'origin':old['origin'],'source_point':obs['start'],
                    'baseline_start':latest['start'],'policy_start':new_start,
                    'baseline_arrival':old['arrival'],'policy_arrival':new['arrival'],
                    'baseline_journey':old['arrival']-latest['start'],'policy_journey':new['arrival']-new_start,
                    'arrival_advance':advance,'departure_advance':departure_advance,
                    'journey_saved':advance-departure_advance,'baseline_route':latest,
                    'passing_allowance':7,'journey_saved_with_allowance':advance-departure_advance+7,
                    'scope':'同一 지도 지점→검증된 승차 정류장 직통 후보의 가장 늦은 출발을 비교'.replace('同一','동일')})
    return out

def main():
    OUT.mkdir(exist_ok=True)
    experiments=[run(d,t,m,p) for d,t,m,p in product(DATES,TARGETS,['strict','matched','optimistic'],['baseline','feeder','full150_extra','rail150_1_extra'])]
    matrix=[];bound_differences=[]
    for d,t in product(DATES,TARGETS):
        b=run(d,t);f=run(d,t,policy='feeder');lo=run(d,t,'optimistic');hi=run(d,t,'strict')
        for i,r in enumerate(b['results']):
            if r['arrival']!=lo['results'][i]['arrival'] or r['arrival']!=hi['results'][i]['arrival']:
                bound_differences.append({'date':d,'target':t,'origin_id':r['origin_id'],'origin':r['origin'],
                                          'optimistic':lo['results'][i]['arrival_hhmm'],'matched':r['arrival_hhmm'],'strict':hi['results'][i]['arrival_hhmm']})
            matrix.append({'date':d,'target':t,'origin_id':r['origin_id'],'origin':r['origin'],'zone':r['zone'],
                           'baseline':r['arrival_hhmm'],'feeder':f['results'][i]['arrival_hhmm'],
                           'advance':r['arrival']-f['results'][i]['arrival'] if r['arrival'] is not None and f['results'][i]['arrival'] is not None else None,
                           'optimistic_baseline':lo['results'][i]['arrival_hhmm'],'strict_baseline':hi['results'][i]['arrival_hhmm']})
    focal=[r for r in matrix if r['origin_id'] in ['49008','49036']]
    result={'version':3,'dates':DATES,'targets':TARGETS,'sample_size':20,
            'scope':'열거한 직통·BIS 추천 환승 및 서울 명시 회랑의 공개 시간표 계산. 전체 망 최적해·실측·수요예측 아님.',
            'housing':housing(),'branches':branch_audits(),
            'alias_audit':json.loads((OUT/'alias_audit.json').read_text()),'experiments':experiments,
            'comparison':matrix,'focal_comparison':focal,'branch_bound_differences':bound_differences,
            'calendar_dispatch':[{'date':d,'first_coach':first_coach(d),'feeder_start':first_coach(d)-50,
                                  'stress_ready':first_coach(d)-50+22.5+10,'stress_buffer':15,
                                  'stress_slack':2.5} for d in DATES],
            'old_fixed_0445_weekend':[run(d,policy='feeder',fixed_start=285) for d in DATES],
            'seat_snapshots':[run(d,policy=p,seat_filter=True) for d,p in product(DATES[1:],['baseline','feeder'])],
            'stress_tests':[run(d,policy=p,factor=1.2,buffer=15,gate=10) for d,p in product(DATES,['baseline','feeder'])],
            'cost':cost_scenarios(),'demand':rp.strengthened.demand(),'tradeoffs':focal_tradeoffs(),
            'undated_supplement':run(include_static=True),
            'limits':['TAGO 미래 고속버스 빈 응답은 미운행으로 해석하지 않는다. 네 추가 날짜의 KOBUS 공개 배차를 수동 대조했다.',
                      '미래 열차는 공식 10/1 적용 KTX 경전선 시각표의 매일 운행 204·382·206으로 보완했다. 미래 일반열차 전체를 완전 수집한 것은 아니다.',
                      '주말 시내버스 및 서울 전철은 각각 해당 요일 분류를 적용한다. 특별 공휴일·임시 변경은 별도 갱신이 필요하다.',
                      '좌석 스냅샷은 현재 예약 가능 여부의 일시적 정보다. 계획을 확정하려면 당일 승차권 확보가 필요하다.']}
    (OUT/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    with (OUT/'calendar_destination_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(matrix[0]));w.writeheader();w.writerows(matrix)
    print('Experiments',len(experiments),'comparisons',len(matrix),'branch-sensitive',len(bound_differences))
    for r in focal[::2]:print(r['date'],r['target'],r['baseline'],'→',r['feeder'],'advance',r['advance'],'bounds',r['optimistic_baseline'],r['strict_baseline'])

if __name__=='__main__':main()
