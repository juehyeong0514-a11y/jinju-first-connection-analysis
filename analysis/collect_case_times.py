"""Collect official expected running times for all direct city-bus candidates.

Origins are named residential-area bus stops, NOT apartment door locations.
The BIS expects five-character public stop_service_id, not internal stop_id.
"""
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw';DEST=RAW/'case_times';DEST.mkdir(exist_ok=True)
BASE='https://bis.jinju.go.kr'
ORIGINS=[('49018','센텀리버파크','혁신도시'),('49008','LH10단지','혁신도시'),('49036','풀에버정문','혁신도시'),('49022','LH3/LH5단지','혁신도시'),('41001','퀸즈웰가','기존 시가지'),('46007','판문현대','기존 시가지'),('41005','휴먼시아4단지','기존 시가지'),('42001','신안주공','기존 시가지')]
HUBS={'intercity':['31001','31002'],'express':['20007','20008'],'innovation':['49017','49018'],'gaeyang':['47009','47010'],'rail':['47026','00020','00085']}
STOPS=json.loads((ROOT/'outputs/all_stops.json').read_text())

def distance(a,b):
    a1,a2=map(math.radians,[float(a['stop_y']),float(b['stop_y'])]);dl=math.radians(float(b['stop_x'])-float(a['stop_x']))
    v=math.sin((a2-a1)/2)**2+math.cos(a1)*math.cos(a2)*math.sin(dl/2)**2
    return 6371.0088*2*math.asin(math.sqrt(v))

def cache_time(key):
    rid,start,end=key
    p=DEST/f'{rid}_{start}_{end}.json'
    if not p.exists():
        params={'brt_id':rid,'start_stop_id':start,'end_stop_id':end}
        req=urllib.request.Request(BASE+'/station/getTimeListAjax.do',data=urllib.parse.urlencode(params).encode(),headers={'Referer':BASE+'/station/stopTime.do','User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=30) as r:b=r.read()
        json.loads(b);p.write_bytes(b);time.sleep(.12)
    return str(p.relative_to(ROOT))

def candidates(origins=None):
    origins = ORIGINS if origins is None else origins
    rows=json.loads((RAW/'jinju_bus_times.json').read_text())['rows']
    paths=[];keys=set()
    for row in rows:
        routes=json.loads((RAW/f"network/{row['brt_id']}.json").read_text())['rows']
        groups={}
        for s in routes:groups.setdefault((str(s['brt_id']),str(s['brt_direction'])),[]).append(s)
        for (rid,direction),seq in groups.items():
            field='ed_firsttime' if direction=='2' else 'firsttime'
            first=row.get(field)
            if not first or first=='0000' or int(first)>800:continue
            seq=sorted(seq,key=lambda x:x['brn_seqno'])
            for oid,name,area in origins:
                # nearby stops may cover the opposite carriageway or an adjacent route
                for i,boarding in enumerate(seq):
                    walk=distance(STOPS[oid],boarding)
                    if walk>.25:continue
                    for hub,ids in HUBS.items():
                        for j in range(i+1,len(seq)):
                            if str(seq[j]['stop_service_id']) not in ids:continue
                            sid=str(seq[0]['stop_service_id']);bid=str(boarding['stop_service_id']);eid=str(seq[j]['stop_service_id'])
                            # Repeated stop IDs in a loop cannot identify a unique
                            # occurrence to this endpoint. Exclude ambiguous timing.
                            if sum(str(s['stop_service_id'])==bid for s in seq[:i+1])>1 or sum(str(s['stop_service_id'])==eid for s in seq[:j+1])>1:continue
                            start_key=(rid,sid,bid);end_key=(rid,sid,eid);ride_key=(rid,bid,eid)
                            if sid!=bid:keys.add(start_key)
                            keys.add(end_key);keys.add(ride_key)
                            paths.append({'origin_id':oid,'origin_name':name,'area':area,'route_label':row['brt_name'],'source_route_id':str(row['brt_id']),'route_id':rid,'direction':direction,'first_departure':first,'origin_stop':sid,'boarding_stop':bid,'hub':hub,'alighting_stop':eid,'walk_to_boarding_straight_km':round(walk,4),'boarding_seq':i+1,'alighting_seq':j+1,'origin_time_key':list(start_key) if sid!=bid else None,'arrival_time_key':list(end_key),'ride_time_key':list(ride_key)})
    return paths,sorted(keys)

if __name__=='__main__':
    paths,keys=candidates()
    (ROOT/'outputs/candidate_citybus_paths.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2))
    print('candidate paths',len(paths),'requests',len(keys),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:files=list(pool.map(cache_time,keys))
    manifest=[]
    for key,file in zip(keys,files):
        p=ROOT/file;d=json.loads(p.read_text());v=d.get('rows',[{}])[0].get('time')
        manifest.append({'file':file,'url':BASE+'/station/getTimeListAjax.do','method':'POST','parameters':dict(zip(['brt_id','start_stop_id','end_stop_id'],key)),'expected_minutes':v,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'retrieved_date_kst':'2026-10-08'})
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('cached',len(files),'missing',sum(r['expected_minutes'] is None for r in manifest))
