"""Account for every raw BIS suggestion that could not be mapped to stop order."""
import json
from collections import Counter
from prepare_transfer_times import match_leg, routes, ROOT

def reason(leg, direct):
    field='currentDirectStopInfo' if direct else 'currentTransferStopInfo'
    stops=leg.get(field,{}).get('list',[])
    if len(stops)<2: return 'missing_leg_stop_list'
    board=str(stops[0]['stopId']).zfill(5);end=str(stops[-1]['stopId']).zfill(5)
    pool=[r for g in routes.values() for r in g if r['rid']==str(leg['routeId']) or r['base']==str(leg['routeId'])]
    if not pool:return 'route_id_not_in_network'
    order=[]
    for r in pool:
        ids=[str(s['stop_service_id']).zfill(5) for s in r['stops']]
        if board in ids and end in ids:
            if ids.count(board)!=1 or ids.count(end)!=1:order.append('repeated_stop_ambiguous')
            else:order.append('end_not_after_board')
    return order[0] if order else 'endpoints_not_on_same_directed_variant'

def audit():
    unmatched=[];mapped=0
    for meta in json.loads((ROOT/'outputs/strengthened/transfer_manifest.json').read_text()):
        ci=json.loads((ROOT/meta['file']).read_text()).get('TransferInfoResult',{}).get('TransferInfo',{}).get('MsgBody',{}).get('COURSEINFO',{})
        grouped=[([p],True) for p in ci.get('CurrentDirectCourseInfo',{}).get('list',[])]
        grouped += [(p['currentTransferInfo']['list'],False) for p in ci.get('CurrentTransferCourseInfo',{}).get('list',[])]
        for rawlegs,direct in grouped:
            bad=[{'route_id':str(l['routeId']),'reason':reason(l,direct)} for l in rawlegs if match_leg(l,direct) is None]
            if bad:unmatched.append({'origin_id':meta['origin_id'],'hub':meta['hub'],'source':meta['file'],'legs':bad})
            else:mapped+=1
    return {'mapped':mapped,'unmatched':len(unmatched),'reason_counts':dict(Counter(l['reason'] for r in unmatched for l in r['legs'])),
            'focal_unmatched':sum(r['origin_id'] in ['49008','49036'] for r in unmatched),'rows':unmatched,
            'limits':'미대응 추천은 현재 노선 순서를 확정할 수 없어 경로로 사용하지 않는다. 50개 시간표 제외의 복원·지선 경계 검토와 별개다. 완전한 네트워크 탐색을 입증하지 않는다.'}

if __name__=='__main__':
    d=audit();out=ROOT/'outputs/robust';out.mkdir(exist_ok=True);(out/'unmatched_audit.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
    print({k:v for k,v in d.items() if k not in ['rows','limits']})
