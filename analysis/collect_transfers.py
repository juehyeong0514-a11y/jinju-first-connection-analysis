"""Cache public BIS suggested direct/one-transfer paths, not an exhaustive graph."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
from collect_case_times import ORIGINS, STOPS, ROOT

DEST=ROOT/'data/raw/transfer_candidates'; DEST.mkdir(exist_ok=True)
HUBS={'intercity':'31002','express':'20008','innovation':'49017','gaeyang':'47010','rail':'47026'}

def collect(job):
    oid,hub,sid=job
    p=DEST/f'{oid}_{hub}.json'
    params={'startstopid':str(STOPS[oid]['stop_id']),'endstopid':str(STOPS[sid]['stop_id'])}
    if not p.exists():
        req=urllib.request.Request('https://bis.jinju.go.kr/transfer/getTransfer.do',data=urllib.parse.urlencode(params).encode(),headers={'Referer':'https://bis.jinju.go.kr/transfer/transfer.do','User-Agent':'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req,timeout=40) as r:body=r.read()
            json.loads(body);p.write_bytes(body)
        except Exception as exc:
            return {'origin_id':oid,'hub':hub,'error':type(exc).__name__}
        time.sleep(.12)
    d=json.loads(p.read_text())
    ci=d.get('TransferInfoResult',{}).get('TransferInfo',{}).get('MsgBody',{}).get('COURSEINFO',{})
    return {'origin_id':oid,'hub':hub,'parameters':params,'file':str(p.relative_to(ROOT)),'direct_count':ci.get('DIRECTCNT'),'transfer_count':ci.get('TRANSCNT'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'retrieved_date_kst':'2026-10-08'}

if __name__=='__main__':
    jobs=[(oid,hub,sid) for oid,_,_ in ORIGINS for hub,sid in HUBS.items() if oid!=sid]
    with concurrent.futures.ThreadPoolExecutor(3) as pool:rows=list(pool.map(collect,jobs))
    (DEST/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    print('collected',len(rows),'errors',sum('error' in r for r in rows),flush=True)
