"""Reproducible candidate-route analysis; results are estimates, not observations.

Scope: sampled bus-stop origins, dated TAGO express/rail services, published
intercity schedule as a separately flagged supplement, direct city-bus routes
and BIS-suggested one-transfer paths. Does not prove a network-wide optimum.
"""
import csv
import json
import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from collect_case_times import ROOT, RAW, ORIGINS, STOPS, HUBS, distance

OUT=ROOT/'outputs'
DIRECT=json.loads((OUT/'candidate_citybus_paths.json').read_text())
SUGGESTED=json.loads((OUT/'suggested_transfer_paths.json').read_text())
FIRST_ROWS={str(r['brt_id']):r for r in json.loads((RAW/'jinju_bus_times.json').read_text())['rows']}

def minute(s):
    s=str(s).zfill(4)
    return int(s[:2])*60+int(s[2:4])

def hhmm(m):
    if m is None:return '미확인'
    m=math.ceil(m-1e-8)
    return f'{m//60:02d}:{m%60:02d}'

def dated_minute(value):
    value=str(value)
    day=datetime.strptime(value[:8],'%Y%m%d')
    return int((day-datetime(2026,10,8)).total_seconds()/60)+minute(value[8:12])

@lru_cache(None)
def offset(key):
    if key is None:return 0.0
    p=RAW/'case_times'/('_'.join(key)+'.json')
    if not p.exists():return None
    rows=json.loads(p.read_text()).get('rows') or [{}]
    value=rows[0].get('time')
    return float(value) if value is not None else None

@lru_cache(None)
def timetable_quality(base,direction):
    """Do not silently choose between contradictory official first departures."""
    p=RAW/'citybus_timetables'/(base+'.json')
    if not p.exists():return {'status':'not_cross_checked'}
    field='btt_endtime' if direction=='2' else 'btt_starttime'
    first_field='ed_firsttime' if direction=='2' else 'firsttime'
    advertised=FIRST_ROWS.get(base,{}).get(first_field)
    times=[minute(r[field]) for r in json.loads(p.read_text()).get('timeTable',[]) if str(r.get('hldyClss','1'))=='1' and r.get(field) and r[field]!='0000']
    if not advertised or advertised=='0000' or not times:return {'status':'not_cross_checked'}
    actual=min(times);expected=minute(advertised)
    return {'status':'agree' if actual==expected else 'conflict','summary_first':expected,'detailed_first':actual}

@lru_cache(None)
def departures(base,direction):
    p=RAW/'citybus_timetables'/(base+'.json')
    if not p.exists() or timetable_quality(base,direction)['status']=='conflict':return []
    field='btt_endtime' if direction=='2' else 'btt_starttime'
    return sorted({minute(r[field]) for r in json.loads(p.read_text()).get('timeTable',[]) if str(r.get('hldyClss','1'))=='1' and r.get(field) and r[field]!='0000'})

def walk(a,b):
    # Explicit approximation used ONLY for short local stop connectors.
    return distance(STOPS[a],STOPS[b])*1.3/4*60

def approach(walk_cap=20,factor=1,policy='baseline'):
    paths=[]; missing=0
    for p in DIRECT:
        if timetable_quality(p['source_route_id'],p['direction'])['status']=='conflict':missing+=1;continue
        board=offset(tuple(p['origin_time_key']) if p['origin_time_key'] else None)
        end=offset(tuple(p['arrival_time_key']))
        if board is None or end is None or end<board:missing+=1;continue
        initial_walk=walk(p['origin_id'],p['boarding_stop'])
        dep=minute(p['first_departure'])
        deps=[dep]
        if policy=='full150_extra' and p['route_label']=='150' and p['direction']=='1':deps.append(dep-50)
        if policy=='rail150_1_extra' and p['route_label']=='150-1' and p['direction']=='2':deps.append(dep-35)
        for d in deps:
            if initial_walk>walk_cap or 240+initial_walk+2>d+board*factor:continue
            paths.append({'origin_id':p['origin_id'],'hub':p['hub'],'arrival':d+end*factor+5,'source':'direct','routes':[p['route_label']],'board_at':[d+board*factor],'walk_minutes':initial_walk,'alighting_stop':p['alighting_stop'],'new_service':d!=dep})
    for p in SUGGESTED:
        legs=p['legs'];initial_walk=walk(p['origin_id'],legs[0]['boarding_stop'])
        clock=240+initial_walk; walking=initial_walk; board_times=[]; valid=True
        for i,l in enumerate(legs):
            board=offset(tuple(l['boarding_time_key']) if l['boarding_time_key'] else None)
            end=offset(tuple(l['arrival_time_key']))
            if board is None or end is None or end<board:valid=False;missing+=1;break
            if i:
                walking_link=max(l['transfer_walk_seconds']/60,walk(legs[i-1]['alighting_stop'],l['boarding_stop']))
                clock+=walking_link;walking+=walking_link
            eligible=[d for d in departures(l['base'],l['direction']) if d+board*factor>=clock+2]
            if not eligible:valid=False;break
            d=eligible[0];board_times.append(d+board*factor);clock=d+end*factor
        if not valid:continue
        last=legs[-1]['alighting_stop']
        final_walk=min(walk(last,h) for h in HUBS[p['hub']])
        walking+=final_walk
        if walking>walk_cap:continue
        paths.append({'origin_id':p['origin_id'],'hub':p['hub'],'arrival':clock+final_walk+5,'source':'BIS_suggested','routes':[l['label'] for l in legs],'board_at':board_times,'walk_minutes':walking,'alighting_stop':last,'new_service':False})
    obs=json.loads((RAW/'map_observations.json').read_text())
    for w in obs['walking_to_innovation']:
        if w['minutes']<=walk_cap:
            paths.append({'origin_id':w['origin_id'],'hub':'innovation','arrival':240+w['minutes'],'source':'map_walk','routes':['도보'],'board_at':[],'walk_minutes':w['minutes'],'new_service':False})
    if policy=='feeder_0450' and walk_cap>=2:
        # Added service along the observed 150 segment, existing services retained.
        # Local gate walk: 5 minutes; coach boarding buffer applied downstream.
        # BIS stopTime gives 11 min while transfer search gives 803 sec (13.38).
        # Plan 15 min, not the more optimistic estimator. Segment length 3.066 km.
        for oid,board_offset in [('49036',0),('49008',6)]:
            paths.append({'origin_id':oid,'hub':'innovation','arrival':290+15*factor+5,'source':'policy_feeder','routes':['추가 연계편'],'board_at':[290+board_offset*factor],'walk_minutes':2,'new_service':True})
    return paths,missing

def services():
    trips=[]
    last={r['origin']:r['minutes'] for r in json.loads((RAW/'map_observations.json').read_text())['last_mile']}
    express_hubs={'NAEK722':'express','NAEK723':'gaeyang','NAEK724':'innovation'}
    for f in (RAW/'tago').glob('*_20261008.json'):
        data=json.loads(f.read_text())['response']['body'];rawitems=data.get('items')
        items=rawitems.get('item',[]) if isinstance(rawitems,dict) else []
        if isinstance(items,dict):items=[items]
        if f.name.startswith('express_') and f.name.split('_')[1] in express_hubs and '_NAEK010_' in f.name:
            for t in items:
                trips.append({'hub':express_hubs[f.name.split('_')[1]],'mode':'express','dep':dated_minute(t['depPlandTime']),'arr':dated_minute(t['arrPlandTime']),'last_mile':last.get('서울고속버스터미널(경부)',16),'destination':'서울경부','label':t['gradeNm'],'dated':True,'source':str(f.relative_to(ROOT))})
        if f.name.startswith('train_'):
            for t in items:
                dest=t['arrplacename'];last_key={'서울':'서울역','수서':'수서역','광명':'광명역','영등포':'영등포역'}.get(dest)
                if last_key not in last:continue
                if str(t['depplandtime'])[:8]!=str(t['arrplandtime'])[:8]:continue
                trips.append({'hub':'rail','mode':'train','dep':minute(str(t['depplandtime'])[8:12]),'arr':minute(str(t['arrplandtime'])[8:12]),'last_mile':last[last_key],'destination':dest,'label':t['traingradename']+' '+t['trainno'],'dated':True,'source':str(f.relative_to(ROOT))})
    # Static official terminal schedule, effective date not stated; report separately.
    for s in ['0440','0500','0530','0600','0630','0700','0730','0800','0830','0900']:
        dep=minute(s)
        trips.append({'hub':'intercity','mode':'intercity','dep':dep,'arr':dep+215,'last_mile':last.get('서울남부터미널',20),'destination':'서울남부','label':'공식 게시 시간표','dated':False,'source':'data/raw/jinju_terminal_routes.html'})
    return trips

def run(walk_cap=20,factor=1,policy='baseline',buffer=10,lastmile_extra=0,include_static=False):
    paths,missing=approach(walk_cap,factor,policy);trips=services();results=[];hub_rows=[]
    for oid,name,area in ORIGINS:
        available=[p for p in paths if p['origin_id']==oid]
        for hub in HUBS:
            ps=[p for p in available if p['hub']==hub]
            if ps:
                p=min(ps,key=lambda p:p['arrival']);hub_rows.append({'origin':name,'origin_id':oid,'hub':hub,**p,'arrival_hhmm':hhmm(p['arrival'])})
        candidates=[]
        for p in available:
            for t in trips:
                if t['hub']!=p['hub'] or (not include_static and not t['dated']):continue
                if p['arrival']+buffer<=t['dep']:
                    candidates.append({'origin_id':oid,'origin':name,'area':area,'arrival':t['arr']+t['last_mile']+lastmile_extra,'arrival_hhmm':hhmm(t['arr']+t['last_mile']+lastmile_extra),'city_path':p,'trip':t})
        if candidates:results.append(min(candidates,key=lambda r:(r['arrival'],not r['trip']['dated'],r['city_path']['arrival'])))
        else:results.append({'origin_id':oid,'origin':name,'area':area,'arrival':None,'arrival_hhmm':'미확인'})
    return {'parameters':{'walk_cap':walk_cap,'city_runtime_multiplier':factor,'policy':policy,'boarding_buffer':buffer,'local_gate_walk':5,'earliest_start':'04:00','last_mile_extra':lastmile_extra,'include_undated_intercity':include_static},'results':results,'hub_access':hub_rows,'unusable_path_count':missing,'evaluated_path_count':len(paths)}

if __name__=='__main__':
    base=run();scenarios=[]
    for policy in ['baseline','feeder_0450','full150_extra','rail150_1_extra']:
        scenarios.append(run(policy=policy))
    sensitivity=[run(walk_cap=w,factor=f,policy=p) for w in [10,20,30,40] for f in [1,1.2] for p in ['baseline','feeder_0450']]
    static_supplement=run(include_static=True)
    buffer_sensitivity=[run(policy=p,buffer=b,factor=f) for p in ['baseline','feeder_0450'] for b in [5,10,15] for f in [1,1.2]]
    output={'scope':'Earliest among enumerated candidates, not a proof of global optimum. Expected BIS stop times and map durations, not observed actual arrivals.','date':'2026-10-08','baseline':base,'scenarios':scenarios,'sensitivity':sensitivity,'buffer_sensitivity':buffer_sensitivity,'undated_intercity_supplement':static_supplement}
    (OUT/'connection_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    with (OUT/'arrival_comparison.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(['지역','표본 정류장','기존','연계편 04:50 추가','150 조기편 추가','150-1 철도 연계편 추가'])
        for i,(_,name,area) in enumerate(ORIGINS):writer.writerow([area,name]+[s['results'][i]['arrival_hhmm'] for s in scenarios])
    for s in scenarios:
        print(s['parameters']['policy'],[(r['origin'],r['arrival_hhmm'],r.get('trip',{}).get('destination'),r.get('city_path',{}).get('routes')) for r in s['results']])
    print('paths',base['evaluated_path_count'],'unusable',base['unusable_path_count'])
