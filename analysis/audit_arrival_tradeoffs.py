"""Audit arrival-time gains versus journey durations and sample dependence.

The later-departure audit considers direct local routes with cached timetables,
falling back to the first published departure when a full timetable is absent.
It is not a proof of the latest feasible start across all walking/transfer paths.
"""
import json
from collections import Counter
from analyze_connections import ROOT, RAW, OUT, DIRECT, ORIGINS, FIRST_ROWS, offset, departures, minute, hhmm, run, timetable_quality

def clock_floor(value):
    n=int(value+1e-8)
    return f'{n//60:02d}:{n%60:02d}'

def latest_direct_start(oid, trip):
    eligible=[]; missing_timetables=set()
    for p in DIRECT:
        if p['origin_id']!=oid or p['hub']!=trip['hub']:continue
        if timetable_quality(p['source_route_id'],p['direction'])['status']=='conflict':continue
        board=offset(tuple(p['origin_time_key']) if p['origin_time_key'] else None)
        end=offset(tuple(p['arrival_time_key']))
        if board is None or end is None or end<board:continue
        # Use the same explicit 2-minute access walk for baseline and feeder.
        # This is a controlled stop-proxy example, not an apartment-door measure.
        walk_minutes=2
        deps=departures(p['source_route_id'],p['direction'])
        if not deps:
            deps=[minute(p['first_departure'])]
            missing_timetables.add(p['source_route_id'])
        for d in deps:
            ready_at_gate=d+end+5
            latest_start=d+board-walk_minutes-2
            if latest_start>=240 and ready_at_gate+10<=trip['dep']:
                eligible.append({'route':p['route_label'],'base':p['source_route_id'],'direction':p['direction'],'origin_departure':d,'board_at':d+board,'at_local_hub':d+end,'ready_at_gate':ready_at_gate,'latest_start':latest_start,'boarding_stop':p['boarding_stop'],'alighting_stop':p['alighting_stop'],'offset_to_board':board,'offset_to_hub':end})
    return max(eligible,key=lambda p:p['latest_start']),sorted(missing_timetables)

def audit():
    baseline=run();policy=run(policy='feeder_0450');rows=[]
    for oid,planned_board in [('49036',290),('49008',296)]:
        old=next(r for r in baseline['results'] if r['origin_id']==oid)
        new=next(r for r in policy['results'] if r['origin_id']==oid)
        path,missing=latest_direct_start(oid,old['trip'])
        old_start=path['latest_start'];new_start=planned_board-2-2
        rows.append({'origin_id':oid,'origin':old['origin'],'baseline_latest_start':clock_floor(old_start),'policy_latest_start':clock_floor(new_start),'baseline_arrival':old['arrival_hhmm'],'policy_arrival':new['arrival_hhmm'],'arrival_advance_minutes':old['arrival']-new['arrival'],'departure_advance_minutes':old_start-new_start,'baseline_journey_minutes':old['arrival']-old_start,'policy_journey_minutes':new['arrival']-new_start,'journey_minutes_saved':(old['arrival']-old_start)-(new['arrival']-new_start),'baseline_path':path,'baseline_trip':old['trip'],'missing_full_timetables':missing})
    deadlines=[]
    for deadline in ['0900','0930','1000','1030']:
        t=minute(deadline)
        deadlines.append({'deadline':hhmm(t),'baseline_count':sum(r['arrival'] is not None and r['arrival']<=t for r in baseline['results']),'policy_count':sum(r['arrival'] is not None and r['arrival']<=t for r in policy['results']),'denominator':8,'unit':'sampled stop origins, not residents'})
    old_routes=Counter(tuple(r['city_path']['routes']) for r in baseline['results'] if r['area']=='기존 시가지')
    conflicts=[]
    for base,row in FIRST_ROWS.items():
        for direction in ['1','2']:
            quality=timetable_quality(base,direction)
            if quality['status']=='conflict':conflicts.append({'base':base,'route':row['brt_name'],'direction':direction,**quality})
    result={'analysis_date':'2026-10-08','scope':'Conditional illustrative direct-route comparisons using available cached full timetables. Not a globally latest departure, not actual observation.','assumptions':{'access_walk_minutes_for_both':2,'local_boarding_buffer':2,'gate_walk_minutes':5,'long_distance_boarding_buffer':10,'maximum_local_walk_minutes':20},'tradeoffs':rows,'deadline_access':deadlines,'old_city_route_dependence':[{'routes':list(k),'origin_count':v} for k,v in old_routes.items()],'timetable_conflicts':conflicts,'interpretation':'Arrival advances and in-journey time savings are different outcomes. Added early service changes morning arrival opportunities; it must not be monetized as 90 minutes of travel-time savings.'}
    (OUT/'arrival_tradeoff_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    result=audit()
    for row in result['tradeoffs']:
        print({k:v for k,v in row.items() if k not in ['baseline_path','baseline_trip','missing_full_timetables']})
        print('baseline local bus',row['baseline_path']['route'],'board',hhmm(row['baseline_path']['board_at']),'uncached full timetable count',len(row['missing_full_timetables']))
    print('deadline access',result['deadline_access'])
    print('old-city paths',result['old_city_route_dependence'])
    print('conflicting timetable directions',len(result['timetable_conflicts']),result['timetable_conflicts'])
