"""Download current route geometries and direction-specific first-departure data.
Read-only public Jinju BIS requests, cached; at most three concurrent requests.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
DEST=RAW/'network';DEST.mkdir(exist_ok=True)
BASE='https://bis.jinju.go.kr'

def get(route):
    rid=route['brt_id'];name=str(rid)+'.json';out=DEST/name
    if not out.exists():
        sample=RAW/'route_samples'/name
        if sample.exists():
            out.write_bytes(sample.read_bytes())
        else:
            params=urllib.parse.urlencode({'brt_id':rid}).encode()
            req=urllib.request.Request(BASE+'/MainBusRouteListAjax.do',data=params,headers={'Referer':BASE+'/bimsRoute/bimsRoute.do','User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=30) as r:payload=r.read()
            if json.loads(payload).get('resultCode')!=200:raise ValueError(rid)
            out.write_bytes(payload)
            time.sleep(.15)
    return {'route_label':route['brt_name'],'route_id':rid,'file':str(out.relative_to(ROOT)),'url':BASE+'/MainBusRouteListAjax.do','method':'POST','parameters':{'brt_id':str(rid)},'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'retrieved_date_kst':'2026-10-08'}

if __name__=='__main__':
    rows=json.loads((RAW/'jinju_bus_times.json').read_text())['rows']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:manifest=list(pool.map(get,rows))
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('route variants cached',len(manifest))
