"""Recover BIS endpoint aliases using exact public geometry and stop order.

Never rename a stop based only on its name. Require the raw polyline endpoint
within 3 m of a current directed stop AND the entire preceding stop list in
the same order. Retain source IDs/coordinates as an auditable crosswalk.
"""
import json
import math
from collections import Counter
from prepare_transfer_times import ROOT, routes, match_leg

def distance(x,y,a,b):
    return math.hypot((x-a)*111320*math.cos(math.radians(y)),(y-b)*111320)

def resolve(leg,direct):
    ordinary=match_leg(leg,direct)
    if ordinary:return ordinary
    field='currentDirectStopInfo' if direct else 'currentTransferStopInfo'
    vertex='currentDirectVertaxInfo' if direct else 'currentTransferVertaxInfo'
    raw=[str(s['stopId']).zfill(5) for s in leg[field]['list']]
    v=leg.get(vertex,{}).get('list',[])
    if len(raw)<2 or not v:return None
    x,y=float(v[-1]['vertaxX']),float(v[-1]['vertaxY'])
    pool=[r for g in routes.values() for r in g if r['rid']==str(leg['routeId']) or r['base']==str(leg['routeId'])]
    options=[]
    for r in pool:
        ids=[str(s['stop_service_id']).zfill(5) for s in r['stops']]
        if raw[-1] in ids:continue
        for j,s in enumerate(r['stops']):
            gap=distance(x,y,float(s['stop_x']),float(s['stop_y']))
            if gap>3 or ids.count(ids[j])!=1:continue
            preceding=raw[:-1]
            if any(ids.count(a)!=1 for a in preceding):continue
            indexes=[ids.index(a) for a in preceding]
            if indexes!=sorted(set(indexes)) or indexes[-1]>=j:continue
            # Subsequence supports skipped stops, never direction reversal.
            alias={'raw_stop':raw[-1],'network_stop':ids[j],'gap_m':round(gap,6),
                   'raw_endpoint':[x,y],'network_endpoint':[float(s['stop_x']),float(s['stop_y'])],
                   'preceding_stops_checked':len(preceding),'evidence':'geometry <=3m and ordered raw stop subsequence'}
            options.append({k:r[k] for k in ['rid','base','label','direction']}|{
                'boarding_stop':raw[0],'alighting_stop':ids[j],'origin_stop':ids[0],
                'boarding_time_key':None if ids[0]==raw[0] else [r['rid'],ids[0],raw[0]],
                'arrival_time_key':[r['rid'],ids[0],ids[j]],'transfer_walk_seconds':float(leg.get('walkingTime',0)),
                'endpoint_alias':alias})
    unique={(r['rid'],r['direction'],r['alighting_stop']):r for r in options}
    return next(iter(unique.values())) if len(unique)==1 else None

def main():
    additions=[];remaining=[];mapped=0;crosswalk=[]
    for meta in json.loads((ROOT/'outputs/strengthened/transfer_manifest.json').read_text()):
        ci=json.loads((ROOT/meta['file']).read_text()).get('TransferInfoResult',{}).get('TransferInfo',{}).get('MsgBody',{}).get('COURSEINFO',{})
        grouped=[([p],True) for p in ci.get('CurrentDirectCourseInfo',{}).get('list',[])]+[(p['currentTransferInfo']['list'],False) for p in ci.get('CurrentTransferCourseInfo',{}).get('list',[])]
        for rawlegs,direct in grouped:
            if all(match_leg(l,direct) for l in rawlegs):mapped+=1;continue
            legs=[resolve(l,direct) for l in rawlegs]
            if any(l is None for l in legs):
                remaining.append({'origin_id':meta['origin_id'],'hub':meta['hub'],'source':meta['file'],
                                  'unresolved_routes':[str(rawlegs[i]['routeId']) for i,l in enumerate(legs) if l is None]})
                continue
            additions.append({'origin_id':meta['origin_id'],'hub':meta['hub'],'source':meta['file'],'legs':legs})
            crosswalk.extend(l['endpoint_alias']|{'source':meta['file'],'route':l['rid']} for l in legs if 'endpoint_alias' in l)
    out=ROOT/'outputs/robust';out.mkdir(exist_ok=True)
    (out/'recovered_transfer_paths.json').write_text(json.dumps(additions,ensure_ascii=False,indent=2))
    result={'original_mapped':mapped,'previously_unmapped':len(additions)+len(remaining),
            'recovered_paths':len(additions),'remaining_paths':len(remaining),
            'focal_recovered':sum(r['origin_id'] in ['49008','49036'] for r in additions),
            'focal_remaining':sum(r['origin_id'] in ['49008','49036'] for r in remaining),
            'crosswalk':crosswalk,'remaining':remaining,
            'remaining_route_counts':dict(Counter(x for r in remaining for x in r['unresolved_routes'])),
            'limits':'공개 자료의 동일 좌표와 정류장 순서로 별도 코드를 대응했다. 현장의 승강장·실제 운행을 관측한 증거가 아니다.'}
    (out/'alias_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print({k:v for k,v in result.items() if k not in ['crosswalk','remaining','limits']})

if __name__=='__main__':main()
