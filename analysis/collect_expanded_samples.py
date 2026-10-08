"""Outcome-blind geographical expansion; preserves the original eight-stop run.

Four named residential stop proxies per geographic zone, no population weights.
The additional stops are selected by geography and names BEFORE routing them.
They are not a random sample, apartment doors, or an official boundary layer.
"""
import concurrent.futures
import json
from collect_case_times import ROOT, RAW, ORIGINS, STOPS, candidates, cache_time
from collect_transfers import collect, HUBS
from prepare_transfer_times import match_leg, schedule

DEST=ROOT/'outputs/strengthened';DEST.mkdir(exist_ok=True)
ORIGINS20=[(o,n,'혁신' if i<4 else '서부') for i,(o,n,_) in enumerate(ORIGINS)]+[
 ('34019','상봉주공2차아파트','북부'),('44006','이현주공아파트','북부'),
 ('39036','초전푸르지오','북부'),('39033','힐스테이트초전','북부'),
 ('35010','상대한보아파트','동부'),('36008','상대주공아파트','동부'),
 ('36017','삼전아파트','동부'),('37004','동일스위트아파트','동부'),
 ('47013','가좌주공아파트','남부'),('47039','가좌주공3단지','남부'),
 ('19012','금호석류/은빛한보아파트','남부'),('48011','호탄대경아파트','남부')]

def safe(fn,arg):
    try:return fn(arg)
    except Exception as exc:return {'error':type(exc).__name__,'job':arg}

def main():
    selection={'rule':'Four residential stop proxies per geographic zone, chosen before route outcome computation; purposive, not population representative.',
      'origins':[{'id':o,'name':n,'zone':z,'longitude':float(STOPS[o]['stop_x']),'latitude':float(STOPS[o]['stop_y'])} for o,n,z in ORIGINS20]}
    (DEST/'sample_selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2))
    direct,keys=candidates(ORIGINS20)
    (DEST/'direct_paths.json').write_text(json.dumps(direct,ensure_ascii=False,indent=2))
    jobs=[(oid,hub,sid) for oid,_,_ in ORIGINS20 for hub,sid in HUBS.items() if oid!=sid]
    with concurrent.futures.ThreadPoolExecutor(3) as pool:meta=list(pool.map(collect,jobs))
    (DEST/'transfer_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    paths=[];keys=set(map(tuple,keys));bases={p['source_route_id'] for p in direct};unmatched=0
    for m in meta:
        if 'error' in m:continue
        ci=json.loads((ROOT/m['file']).read_text()).get('TransferInfoResult',{}).get('TransferInfo',{}).get('MsgBody',{}).get('COURSEINFO',{})
        grouped=[([p],True) for p in ci.get('CurrentDirectCourseInfo',{}).get('list',[])]
        grouped += [(p['currentTransferInfo']['list'],False) for p in ci.get('CurrentTransferCourseInfo',{}).get('list',[])]
        for rawlegs,is_direct in grouped:
            legs=[match_leg(l,is_direct) for l in rawlegs]
            if any(l is None for l in legs):unmatched+=1;continue
            paths.append({'origin_id':m['origin_id'],'hub':m['hub'],'source':m['file'],'legs':legs})
            for l in legs:
                bases.add(l['base'])
                for f in ['boarding_time_key','arrival_time_key']:
                    if l[f]:keys.add(tuple(l[f]))
    (DEST/'suggested_paths.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2))
    print('origins',len(ORIGINS20),'direct',len(direct),'suggested',len(paths),'unmatched',unmatched,'keys',len(keys),flush=True)
    with concurrent.futures.ThreadPoolExecutor(3) as pool:sr=list(pool.map(lambda b:safe(schedule,b),sorted(bases)))
    with concurrent.futures.ThreadPoolExecutor(3) as pool:tr=list(pool.map(lambda k:safe(cache_time,k),sorted(keys)))
    errors=[r for r in sr+tr if isinstance(r,dict) and 'error' in r]
    (DEST/'collection_quality.json').write_text(json.dumps({'origins':len(ORIGINS20),'direct':len(direct),'suggested':len(paths),'unmatched':unmatched,'time_queries':len(keys),'errors':errors},ensure_ascii=False,indent=2))
    print('complete; errors',len(errors),flush=True)

if __name__=='__main__':main()
