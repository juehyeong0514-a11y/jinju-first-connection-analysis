"""Read public ITS statistics through the requests documented by its own UI.

Anonymous CSRF/session fields are used transiently, never printed or exported.
No credentials and no statistical write operations are involved.
"""
import http.cookiejar
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/raw/strengthening/its';DEST.mkdir(parents=True,exist_ok=True)
BASE='https://its.jinju.go.kr/its'

class Client:
    def __init__(self):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        html=self.opener.open(BASE+'/stt/view',timeout=30).read().decode()
        metas=dict(re.findall(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"',html))
        self.headers={'Content-Type':'application/json','Referer':BASE+'/stt/view','User-Agent':'Mozilla/5.0'}
        if metas.get('_csrf_header') and metas.get('_csrf'):self.headers[metas['_csrf_header']]=metas['_csrf']
    def get(self,operation,params,name):
        p=DEST/(name+'.json')
        if p.exists():return json.loads(p.read_text())
        try:
            request=urllib.request.Request(BASE+'/stt/'+operation,data=json.dumps(params).encode(),headers=self.headers)
            data=json.loads(self.opener.open(request,timeout=45).read())
            p.write_text(json.dumps(data,ensure_ascii=False,indent=2))
            (DEST/(name+'.meta.json')).write_text(json.dumps({'url':BASE+'/stt/'+operation,'parameters':params,'retrieved_local':datetime.now().isoformat(),'source_ui':BASE+'/stt/view'},ensure_ascii=False,indent=2))
            time.sleep(.3)
            return data
        except Exception as exc:
            return {'error':type(exc).__name__,'status':getattr(exc,'code',None)}

if __name__=='__main__':
    c=Client()
    for op in ['selectFilterDate','selectFilterBusLine']:
        data=c.get(op,{},op)
        print(op,str(data)[:1500],flush=True)
    periods=[('20260901','20260930'),('20261001','20261007')]
    for start,end in periods:
        for op in ['selectRidePersonPerTime','selectRidePersonPerDay','selectBusRideCntPerAdmnstrt','selectBusRidePersonPerLine']:
            p={'startDate':start,'endDate':end,'sttType':'BUS','subType':''}
            data=c.get(op,p,op+'_'+start+'_'+end)
            print(op,start,str(data)[:2500],flush=True)
