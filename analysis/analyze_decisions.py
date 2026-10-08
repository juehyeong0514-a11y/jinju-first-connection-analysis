"""v5: conditional arrival opportunities, departure burden and access alternatives.

Offline cached public timetables. Road shocks are scenarios, not probabilities
or measured delays. Each scenario reselects the best known coach/train and
rejoins the actual scheduled metro; existing trains are preserved.
"""
import csv
import json
from functools import lru_cache
from itertools import product
import analyze_robustness as ar

ROOT=ar.ROOT; OUT=ROOT/'outputs/decisions'; ac=ar.ac
MODES=['strict','matched','optimistic']
STARTS=[240,270,300,330,360,390]
DELAYS=[0,10,20,30,60]
DEADLINES=[540,570,600,630,660]
WALK_CAPS=[10,20,30,40]
FOCAL=['49008','49036']

@lru_cache(None)
def run(value='2026-10-08',target='강남',mode='matched',policy='baseline',
        earliest_start=240,coach_delay=0,entry_extra=0,rail_delay=0,taxi_minutes=5,gate=5,buffer=10,walk_cap=20):
    if min(coach_delay,entry_extra,rail_delay,taxi_minutes,gate,buffer,walk_cap)<0:raise ValueError('Negative duration')
    city_day,metro_day=ar.day_classes(value)
    start=ar.first_coach(value)-50
    paths,_=ar.rp.pathways(city_day,mode,'baseline' if policy=='taxi' else policy,
                          1,walk_cap,gate,start,earliest_start)
    if policy=='taxi':
        # Conditional on a pre-booked vehicle being ready at the mapped point.
        # This is NOT evidence of available dawn vehicles or a quoted fare.
        paths=paths+[{'origin_id':oid,'hub':'innovation','arrival':earliest_start+taxi_minutes+gate,
                     'source':'conditional_reserved_taxi','board_at':[earliest_start],
                     'walk_minutes':0,'routes':['예약택시 가정'],'new_service':True} for oid in FOCAL]
    results=[]
    for oid,name,zone in ac.ORIGINS:
        best={}
        for p in paths:
            if p['origin_id']==oid and (p['hub'] not in best or p['arrival']<best[p['hub']]['arrival']):best[p['hub']]=p
        candidates=[]
        for t in ar.services(value):
            if not t['dated']:continue
            p=best.get(t['hub'])
            if p is None or p['arrival']+buffer>t['dep']:continue
            delay=rail_delay if t['mode']=='train' else coach_delay
            last=ar.finish_target(t['destination'],t['arr']+delay,metro_day,target,extra=entry_extra)
            if last:
                candidates.append({'origin_id':oid,'origin':name,'zone':zone,'arrival':last['arrival'],
                    'arrival_hhmm':ac.hhmm(last['arrival']),'city_path':p,'trip':t,'seoul_connection':last,
                    'gateway_arrival_with_shock':t['arr']+delay,'boarding_slack':t['dep']-p['arrival']-buffer})
        results.append(min(candidates,key=lambda r:(r['arrival'],r['city_path']['arrival'])) if candidates else
                       {'origin_id':oid,'origin':name,'zone':zone,'arrival':None,'arrival_hhmm':'미확인'})
    return {'parameters':{'date':value,'target':target,'branch_mode':mode,'policy':policy,
            'earliest_start':earliest_start,'coach_delay':coach_delay,'entry_extra':entry_extra,
            'rail_delay':rail_delay,'taxi_minutes':taxi_minutes,'gate':gate,'buffer':buffer,'walk_cap':walk_cap},'results':results}

def focal(r):return [x for x in r['results'] if x['origin_id'] in FOCAL]

def compare(b,f):
    rows=[]
    for a,z in zip(b['results'],f['results']):
        rows.append({'origin_id':a['origin_id'],'origin':a['origin'],'baseline':a['arrival'],
                     'feeder':z['arrival'],'baseline_hhmm':a['arrival_hhmm'],'feeder_hhmm':z['arrival_hhmm'],
                     'advance':a['arrival']-z['arrival'] if a['arrival'] is not None and z['arrival'] is not None else None,
                     'baseline_hub':a.get('trip',{}).get('hub'),'feeder_hub':z.get('trip',{}).get('hub'),
                     'baseline_service':a.get('trip',{}).get('label'),'feeder_service':z.get('trip',{}).get('label')})
    return rows

def write_csv(name,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    OUT.mkdir(exist_ok=True)
    opportunities=[];departure=[];delays=[];entry=[];taxi=[]
    for d,t,m in product(ar.DATES,ar.TARGETS,MODES):
        b=run(d,t,m);f=run(d,t,m,'feeder')
        for deadline in DEADLINES:
            enabled=[a['origin_id'] for a,z in zip(b['results'],f['results']) if z['arrival'] is not None and z['arrival']<=deadline and (a['arrival'] is None or a['arrival']>deadline)]
            opportunities.append({'date':d,'target':t,'branch_mode':m,'deadline':ac.hhmm(deadline),
                'baseline_count':sum(x['arrival'] is not None and x['arrival']<=deadline for x in b['results']),
                'feeder_count':sum(x['arrival'] is not None and x['arrival']<=deadline for x in f['results']),
                'newly_enabled_count':len(enabled),'newly_enabled_ids':'|'.join(enabled),'sample_size':20})
        for start in STARTS:
            for row in compare(run(d,t,m,earliest_start=start),run(d,t,m,'feeder',earliest_start=start)):
                if row['origin_id'] in FOCAL:departure.append(dict(date=d,target=t,branch_mode=m,earliest_start=ac.hhmm(start),**row))
        for shock in DELAYS:
            for row in compare(run(d,t,m,coach_delay=shock),run(d,t,m,'feeder',coach_delay=shock)):
                if row['origin_id'] in FOCAL:
                    delays.append(dict(date=d,target=t,branch_mode=m,coach_delay=shock,entry_extra=0,
                        on_time_0930=row['feeder'] is not None and row['feeder']<=570,
                        slack_0930=570-row['feeder'] if row['feeder'] is not None else None,**row))
    # Separate extra station-entry walking and both-mode delay corner tests.
    for t,road,walk,rail in product(ar.TARGETS,[0,10,30],[0,5,10],[0,10]):
        for row in compare(run(target=t,coach_delay=road,entry_extra=walk,rail_delay=rail),
                           run(target=t,policy='feeder',coach_delay=road,entry_extra=walk,rail_delay=rail)):
            if row['origin_id'] in FOCAL:entry.append(dict(target=t,coach_delay=road,entry_extra=walk,rail_delay=rail,**row))
    for d,t,duration,gate,buffer in product(ar.DATES,ar.TARGETS,[5,10,15],[5,10],[10,15]):
        res=run(d,t,policy='taxi',taxi_minutes=duration,gate=gate,buffer=buffer)
        # Same first coach independently checked; departure is from mapped point.
        coach=next(s for s in ar.services(d) if s['hub']=='innovation' and s['mode']=='express' and s['dep']==ar.first_coach(d))
        for r in focal(res):
            taxi.append({'date':d,'target':t,'origin_id':r['origin_id'],'origin':r['origin'],
                'taxi_minutes':duration,'gate':gate,'buffer':buffer,
                'latest_pickup_for_first_coach':ac.hhmm(coach['dep']-duration-gate-buffer),
                'first_coach_departure':ac.hhmm(coach['dep']),'arrival':r['arrival'],
                'arrival_hhmm':r['arrival_hhmm'],'selected_local_source':r.get('city_path',{}).get('source'),
                'scope':'지도 지점 예약 차량 즉시 출발 가정; 실제 배차·요금·예약 가능 여부 미검증'})
    base=json.loads((ROOT/'outputs/robust/analysis.json').read_text())
    frontier=[]
    for r in base['tradeoffs']:
        oid=r['origin_id'];obs=next(o for o in ar.rp.strengthened.MAP['focal_access'] if o['origin_id']==oid)
        for label,start,arrival,cost in [
            ('기존 확인 직통 후보',r['baseline_start'],r['baseline_arrival'],1650),
            ('예약 연계편 계획',r['policy_start'],r['policy_arrival'],1650),
            ('예약택시 5분 가정',ar.first_coach('2026-10-08')-5-5-10,r['policy_arrival'],obs['taxi_won']),
            ('예약택시 15분·이동10·여유15',ar.first_coach('2026-10-08')-15-10-15,r['policy_arrival'],None)]:
            frontier.append({'origin_id':oid,'origin':r['origin'],'source_point':obs['start'],'option':label,
                'departure':start,'departure_hhmm':ac.hhmm(start),'arrival':arrival,'arrival_hhmm':ac.hhmm(arrival),
                'journey_minutes':arrival-start,'regional_user_cost_won':cost,
                'cost_scope':'지역 접근만; 장거리·서울 운임은 별도. 1650은 제안 본인부담, 택시금액은 지도 참고값.'})
    walking=[];walking_points=[]
    for d,t,m,cap in product(ar.DATES,ar.TARGETS,MODES,WALK_CAPS):
        b=run(d,t,m,walk_cap=cap);f=run(d,t,m,'feeder',walk_cap=cap)
        for row in compare(b,f):
            if row['origin_id'] in FOCAL:
                a=next(r for r in b['results'] if r['origin_id']==row['origin_id'])
                walking.append(dict(date=d,target=t,branch_mode=m,walk_cap=cap,
                    baseline_source=a.get('city_path',{}).get('source'),
                    baseline_local_walk=a.get('city_path',{}).get('walk_minutes'),
                    baseline_count_0930=sum(r['arrival'] is not None and r['arrival']<=570 for r in b['results']),
                    feeder_count_0930=sum(r['arrival'] is not None and r['arrival']<=570 for r in f['results']),**row))
    for d,t,obs in product(ar.DATES,ar.TARGETS,ar.rp.strengthened.MAP['focal_access']):
        coach=next(s for s in ar.services(d) if s['hub']=='innovation' and s['mode']=='express' and s['dep']==ar.first_coach(d))
        result=ar.finish_target(coach['destination'],coach['arr'],ar.day_classes(d)[1],t)
        walk=obs['coach_walk_minutes'];point_start=coach['dep']-walk-5-10
        walking_points.append({'date':d,'target':t,'origin_id':obs['origin_id'],'source_point':obs['start'],
            'walk_minutes':walk,'distance_meters':obs['coach_walk_meters'],
            'latest_departure':point_start,'latest_departure_hhmm':ac.hhmm(point_start),
            'first_coach':ac.hhmm(coach['dep']),'arrival':result['arrival'],'arrival_hhmm':ac.hhmm(result['arrival']),
            'regional_fare':0,'scope':'지도 지점 직보행; 이동5분·승차여유10분. 야간 보행환경·개인 보행 능력·장거리 승차권 미확인.'})
    result={'version':5,'dates':ar.DATES,'targets':ar.TARGETS,'sample_size':20,
        'opportunities':opportunities,'departure_constraints':departure,'delay_comparison':delays,
        'entry_and_rail_sensitivity':entry,'conditional_taxi':taxi,'focal_options':frontier,'walking_sensitivity':walking,'walking_point_options':walking_points,
        'primary_context':json.loads((ROOT/'data/raw/strengthening/decisions/primary_context.json').read_text()),
        'operating_rule':{'walking_need_first':'개별 출발점의 보행 대안·가능시간·허용 보행을 먼저 확인. 실제 보행 부담을 확인하기 전 모든 주민의 첫차 불가나 지원 필요를 주장하지 않음','ticket_first':True,'no_unrelated_taxi_pooling':True,'choose':'확정'+' 일행·좌석·동일 범위 견적에서 더 낮은 총비용 수단 선택; 동률이면 배차·취소 조건 비교',
            'pilot_duration':'4주 제안, 실증 수행 아님','observe':['예약 일행 수·확정 장거리 좌석','실제 차량 준비·승차장 도착·승차 성공','서울 최종 도착과 목표시각 충족','실제 회송 포함 원가·취소·불참','비참여 사유와 예약 불가 건수'],
            'stop':'차량/승차권/허용 좌석/현실적 출발시각 중 하나라도 확보되지 않으면 연결 보장 문구 없이 대안 제시'},
        'limits':['93분은 지역보행20분 이내라는 가정에서의 값이다. 더 긴 보행을 허용하면 두 지점에서도 첫차에 연결돼 연계편의 추가 도착 개선이 사라질 수 있다.',
            '20분은 조사된 주민 선호나 공인 지원 기준이 아니다. 10/20/30/40분은 가정의 민감도 격자다.',
            '대표 정류장 보행26/32분과 상세 지도 지점28/31분은 출발점이 다른 관측이므로 대체하거나 섞지 않는다. 야간 보행 안전·실제 가능 여부는 관측하지 않았다.',
            '20개 대표 지점의 시간표 기회 수이며 주민·직장·진료 수요의 수나 비율이 아니다.',
            '09:00/09:30 등 목표시각은 비교 격자이며 실제 약속이나 수요로 조사한 값이 아니다.',
            '코치 도착 지연0/10/20/30/60분은 가상 입력이다. 발생 빈도·정시율·확률·인과효과를 추정하지 않는다.',
            '각 지연 조건에서 두 정책 모두 알려진 장거리편과 전철을 재선택한다. 철도 지연0/10분은 별도 조건이다.',
            '늦은 출발 격자는 출발 부담을 보여준다. 전체 경로별 가장 늦은 출발의 완전한 Pareto 최적해는 아니다.',
            '지도 지점 예약택시는 실제 새벽 차량이 확보되었다는 조건이며 호출 대기시간0·주행5/10/15분 가정이다.',
            '택시비 지도 참고액은 예약·새벽·회송 포함 견적이 아니다. 지원 시 동일 도착에 지역 본인부담을 바꾸는 정책이다.',
            '기존 DRT 공식 게시 안내와의 비교이며 조회 후 변경 가능. 새벽 연계 사업 승인·차량 전용을 확인한 것이 아니다.']}
    (OUT/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    for name,rows in [('arrival_opportunities.csv',opportunities),('departure_constraints.csv',departure),('delay_comparison.csv',delays),('conditional_taxi.csv',taxi),('focal_options.csv',frontier),('walking_sensitivity.csv',walking),('walking_point_options.csv',walking_points)]:write_csv(name,rows)
    print('v5 opportunities',len(opportunities),'departure cases',len(departure),'delay comparisons',len(delays),'taxi cases',len(taxi))
    print('walking sensitivity',len(walking),'mapped walking options',len(walking_points))
    for r in walking:
        if r['date']=='2026-10-08' and r['target']=='강남' and r['branch_mode']=='matched':print('walk cap',r['walk_cap'],r['origin'],r['baseline_hhmm'],'->',r['feeder_hhmm'],'advance',r['advance'])
    for r in delays:
        if r['date']=='2026-10-08' and r['target']=='강남' and r['branch_mode']=='matched' and r['origin_id']=='49008':print(r['coach_delay'],r['baseline_hhmm'],'->',r['feeder_hhmm'],'advance',r['advance'],'09:30 slack',r['slack_0930'])

if __name__=='__main__':main()
