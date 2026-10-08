"""Check long-distance schedules on a weekday and a normal weekend.

This does not validate city-bus connections on those days. Raw API responses
and key-free request metadata are cached by tago_client.query.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from tago_client import ROOT, query

DATES=['20261013','20261017','20261018']

def request(job):
    service,date,origin,dest=job
    if service=='express':
        operation='GetStrtpntAlocFndExpbusInfo'
        params={'depTerminalId':origin,'arrTerminalId':dest,'depPlandTime':date,'numOfRows':500,'pageNo':1}
        dep_key,arr_key='depPlandTime','arrPlandTime'
    else:
        operation='GetStrtpntAlocFndTrainInfo'
        params={'depPlaceId':origin,'arrPlaceId':dest,'depPlandTime':date,'numOfRows':500,'pageNo':1}
        dep_key,arr_key='depplandtime','arrplandtime'
    label=f'{service}_{origin}_{dest}_{date}'
    result=query(service,operation,params,label)
    items=result.pop('items',[])
    result.update({'date':date,'origin_id':origin,'destination_id':dest})
    result['morning_trips']=[{'departure':str(x[dep_key]),'arrival':str(x[arr_key])} for x in items if str(x[dep_key])[:8]==date and str(x[dep_key])[8:12]<'0900']
    return result

if __name__=='__main__':
    jobs=[('express',d,o,'NAEK010') for d in DATES for o in ['NAEK722','NAEK723','NAEK724']]
    jobs += [('train',d,'NAT881014',a) for d in DATES for a in ['NAT010000','NATH10219','NATH30000']]
    with ThreadPoolExecutor(3) as pool:results=list(pool.map(request,jobs))
    (ROOT/'outputs/service_date_audit.json').write_text(json.dumps({'scope':'Long-distance schedules only; city connections must be checked for each day type.','results':results},ensure_ascii=False,indent=2))
    for r in results:print(r['service'],r['date'],r['origin_id'],r['destination_id'],r['ok'],r.get('count'),r['morning_trips'][:2])
