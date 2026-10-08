"""Optional public BIS expected-time collection for recovered alias paths."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from collect_case_times import ROOT,RAW,cache_time

def collect(k):
    try:
        name=cache_time(k);p=ROOT/name;d=json.loads(p.read_text())
        return {'file':name,'url':'https://bis.jinju.go.kr/station/getTimeListAjax.do','method':'POST',
                'parameters':dict(zip(['brt_id','start_stop_id','end_stop_id'],k)),
                'expected_minutes':d.get('rows',[{}])[0].get('time') if d.get('rows') else None,
                'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'retrieved_date_kst':'2026-10-08'}
    except Exception as e:return {'key':k,'error_type':type(e).__name__}

if __name__=='__main__':
    paths=json.loads((ROOT/'outputs/robust/recovered_transfer_paths.json').read_text())
    keys=sorted({tuple(l[f]) for p in paths for l in p['legs'] for f in ['boarding_time_key','arrival_time_key'] if l[f]})
    with ThreadPoolExecutor(3) as pool:rows=list(pool.map(collect,keys))
    (RAW/'strengthening/robust/alias_time_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    print('Alias time checks:',len(rows),'errors:',sum('error_type' in r for r in rows))
