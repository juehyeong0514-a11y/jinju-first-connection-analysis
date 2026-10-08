"""Refresh previously collected official requests; keep credentials out of logs.

Usage: python analysis/refresh_tago.py [YYYYMMDD]
Without a date, replay the saved collection requests. Intercity data is limited
to the current day according to the provider, so historical replay may be empty.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from tago_client import ROOT, query

def refresh(meta_file):
    meta=json.loads(meta_file.read_text());service=meta_file.name.split('_')[0]
    params=meta['parameters'].copy();label=meta_file.name.removesuffix('.meta.json')
    if len(sys.argv)>1 and 'depPlandTime' in params:
        old=str(params['depPlandTime']);params['depPlandTime']=sys.argv[1]
        label=label.replace(old,sys.argv[1])
    result=query(service,meta['endpoint'].rsplit('/',1)[-1],params,label)
    result.pop('items',None)
    print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:
        from datetime import datetime
        datetime.strptime(sys.argv[1],'%Y%m%d')
    with ThreadPoolExecutor(3) as pool:list(pool.map(refresh,sorted((ROOT/'data/raw/tago').glob('*.meta.json'))))
