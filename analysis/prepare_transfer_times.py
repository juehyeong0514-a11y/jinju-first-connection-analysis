"""Attach BIS timetables/estimated stop times to public suggested paths."""
import concurrent.futures
import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from collect_case_times import ROOT, RAW, STOPS, cache_time

SCHEDULES=RAW/'citybus_timetables';SCHEDULES.mkdir(exist_ok=True)
rows=json.loads((RAW/'jinju_bus_times.json').read_text())['rows']
routes=defaultdict(list)
for row in rows:
    groups=defaultdict(list)
    for s in json.loads((RAW/f"network/{row['brt_id']}.json").read_text())['rows']:
        groups[(str(s['brt_id']),str(s['brt_direction']))].append(s)
    for (rid,direction),stops in groups.items():
        routes[rid].append({'rid':rid,'base':str(row['brt_id']),'label':row['brt_name'],'direction':direction,'stops':sorted(stops,key=lambda s:s['brn_seqno'])})

def match_leg(leg, direct=False):
    field='currentDirectStopInfo' if direct else 'currentTransferStopInfo'
    stops=leg[field]['list'];board=str(stops[0]['stopId']).zfill(5);end=str(stops[-1]['stopId']).zfill(5)
    options=[]
    # The transfer endpoint may return a base ID for a reverse-direction leg.
    # Resolve its stop order against both directions instead of assuming inbound.
    pool=[r for group in routes.values() for r in group if r['rid']==str(leg['routeId']) or r['base']==str(leg['routeId'])]
    for r in pool:
        ids=[str(s['stop_service_id']).zfill(5) for s in r['stops']]
        if ids.count(board)!=1 or ids.count(end)!=1:continue
        i,j=ids.index(board),ids.index(end)
        if j<=i:continue
        options.append({k:r[k] for k in ['rid','base','label','direction']}|{'boarding_stop':board,'alighting_stop':end,'origin_stop':ids[0],'boarding_time_key':None if ids[0]==board else [r['rid'],ids[0],board],'arrival_time_key':[r['rid'],ids[0],end],'transfer_walk_seconds':float(leg.get('walkingTime',0))})
    # Same directed path may be repeated in network responses. Keep one base.
    return options[0] if options else None

def schedule(base):
    p=SCHEDULES/f'{base}.json'
    if not p.exists():
        label=next(r['brt_name'] for r in rows if str(r['brt_id'])==base)
        params={'brt_id':base,'brt_no':label,'btt_type':'1'}
        req=urllib.request.Request('https://bis.jinju.go.kr/bimsRoute/BusRouteTimeTable.do',data=urllib.parse.urlencode(params).encode(),headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=35) as r:b=r.read()
        json.loads(b);p.write_bytes(b);time.sleep(.1)
    return base

if __name__=='__main__':
    paths=[];keys=set();bases=set();unmatched=0
    for meta in json.loads((RAW/'transfer_candidates/manifest.json').read_text()):
        if 'error' in meta:continue
        ci=json.loads((ROOT/meta['file']).read_text()).get('TransferInfoResult',{}).get('TransferInfo',{}).get('MsgBody',{}).get('COURSEINFO',{})
        grouped=[([p],True) for p in ci.get('CurrentDirectCourseInfo',{}).get('list',[])]
        grouped += [(p['currentTransferInfo']['list'],False) for p in ci.get('CurrentTransferCourseInfo',{}).get('list',[])]
        for rawlegs,direct in grouped:
            legs=[match_leg(l,direct) for l in rawlegs]
            if any(l is None for l in legs):unmatched+=1;continue
            paths.append({'origin_id':meta['origin_id'],'hub':meta['hub'],'source':meta['file'],'legs':legs})
            for l in legs:
                bases.add(l['base'])
                for field in ['boarding_time_key','arrival_time_key']:
                    if l[field]:keys.add(tuple(l[field]))
    (ROOT/'outputs/suggested_transfer_paths.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2))
    print('paths',len(paths),'unmatched',unmatched,'time_queries',len(keys),'timetables',len(bases),flush=True)
    with concurrent.futures.ThreadPoolExecutor(3) as pool:list(pool.map(schedule,sorted(bases)))
    with concurrent.futures.ThreadPoolExecutor(3) as pool:list(pool.map(cache_time,sorted(keys)))
    print('complete',flush=True)
