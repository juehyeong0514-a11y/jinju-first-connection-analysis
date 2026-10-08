"""Calendar-specific local paths with transparent branch-assignment bounds.

strict: independently advertised variant first/last departures only.
matched: same routing remark as its advertised first trip, within its bounds.
optimistic: every family departure on every variant, intentionally overinclusive.
The optimistic mode is a robustness bound, NEVER an offered passenger route.
"""
import json
from functools import lru_cache
import analyze_strengthened as strengthened

ac = strengthened.ac
RAW = ac.RAW
_recovered = ac.ROOT/'outputs/robust/recovered_transfer_paths.json'
if _recovered.exists():
    ac.SUGGESTED = ac.SUGGESTED + json.loads(_recovered.read_text())

@lru_cache(None)
def summaries(day):
    suffix = '' if day == '1' else '_'+day
    return {str(r['brt_id']): r for r in json.loads((RAW/f'jinju_bus_times{suffix}.json').read_text())['rows']}

@lru_cache(None)
def full_table(base, day):
    p = RAW/'citybus_timetables'/f'{base}.json' if day == '1' else RAW/'strengthening/robust/citybus_calendar'/f'{day}_{base}.json'
    return json.loads(p.read_text()).get('timeTable', []) if p.exists() else []

@lru_cache(None)
def branch_audit(base, direction, day='1'):
    row = summaries(day).get(base)
    if row is None:
        return {'status': 'not_in_calendar', 'first': None, 'last': None, 'family_times': []}
    start = 'ed_firsttime' if direction == '2' else 'firsttime'
    end = 'ed_lasttime' if direction == '2' else 'lasttime'
    field = 'btt_endtime' if direction == '2' else 'btt_starttime'
    first, last = row.get(start), row.get(end)
    if not first or first == '0000':
        return {'status': 'no_direction_time', 'first': None, 'last': None, 'family_times': []}
    first = ac.minute(first); last = ac.minute(last) if last and last != '0000' else first
    table = [r for r in full_table(base, day) if str(r.get('hldyClss')) == day and r.get(field) not in [None, '', '0000']]
    family = sorted({ac.minute(r[field]) for r in table})
    matches = [r for r in table if ac.minute(r[field]) == first]
    remarks = {r.get('brt_remark', '').strip() for r in matches}
    matching = sorted({ac.minute(r[field]) for r in table if r.get('brt_remark', '').strip() in remarks and first <= ac.minute(r[field]) <= last})
    return {'base': base, 'label': row['brt_name'], 'direction': direction, 'day': day,
            'first': first, 'last': last, 'family_first': min(family) if family else None,
            'first_present': bool(matches), 'last_present': last in family,
            'first_remarks': sorted(remarks), 'family_times': family, 'matching_times': matching,
            'status': 'variant_first_found_in_family' if matches else 'summary_only'}

def departures(base, direction, day, mode):
    a = branch_audit(base, direction, day)
    if a['first'] is None: return []
    endpoints = {a['first'], a['last']}
    if mode == 'strict': return sorted(endpoints)
    if mode == 'matched': return sorted(endpoints | set(a.get('matching_times', [])))
    if mode == 'optimistic': return sorted(endpoints | set(a['family_times']))
    raise ValueError('Unknown branch mode')

@lru_cache(None)
def pathways(day='1', mode='matched', policy='baseline', factor=1, walk_cap=20, gate=5, feeder_start=285):
    paths = []; missing = 0
    for p in ac.DIRECT:
        board = ac.offset(tuple(p['origin_time_key']) if p['origin_time_key'] else None)
        end = ac.offset(tuple(p['arrival_time_key']))
        if board is None or end is None or end < board:
            missing += 1; continue
        w = ac.walk(p['origin_id'], p['boarding_stop'])
        if w > walk_cap: continue
        times = departures(p['source_route_id'], p['direction'], day, mode)
        additions = []
        if times and policy == 'full150_extra' and p['route_label'] == '150' and p['direction'] == '1': additions = [feeder_start]
        if times and policy == 'rail150_1_extra' and p['route_label'] == '150-1' and p['direction'] == '2': additions = [305]
        for d in sorted(set(times+additions)):
            if 240+w+2 > d+board*factor: continue
            paths.append({'origin_id': p['origin_id'], 'hub': p['hub'], 'arrival': d+end*factor+gate,
                          'source': 'direct', 'routes': [p['route_label']], 'board_at': [d+board*factor],
                          'walk_minutes': w, 'boarding_stop': p['boarding_stop'], 'alighting_stop': p['alighting_stop'],
                          'base': p['source_route_id'], 'direction': p['direction'], 'departure': d,
                          'branch_mode': mode, 'new_service': d in additions})
            # Later journeys of the same route cannot improve local access.
            break
    for p in ac.SUGGESTED:
        legs = p['legs']; w = ac.walk(p['origin_id'], legs[0]['boarding_stop'])
        clock = 240+w; total_w = w; boards = []; valid = True
        for i, l in enumerate(legs):
            board = ac.offset(tuple(l['boarding_time_key']) if l['boarding_time_key'] else None)
            end = ac.offset(tuple(l['arrival_time_key']))
            if board is None or end is None or end < board:
                valid = False; missing += 1; break
            if i:
                link = max(l['transfer_walk_seconds']/60, ac.walk(legs[i-1]['alighting_stop'], l['boarding_stop']))
                total_w += link; clock += link
            ds = [d for d in departures(l['base'], l['direction'], day, mode) if d+board*factor >= clock+2]
            if not ds: valid = False; break
            d = ds[0]; boards.append(d+board*factor); clock = d+end*factor
        if not valid: continue
        last = legs[-1]['alighting_stop']; final = min(ac.walk(last,h) for h in ac.HUBS[p['hub']]); total_w += final
        if total_w > walk_cap: continue
        paths.append({'origin_id':p['origin_id'], 'hub':p['hub'], 'arrival':clock+final+gate,
                      'source':'BIS_suggested', 'routes':[l['label'] for l in legs], 'board_at':boards,
                      'walk_minutes':total_w, 'new_service':False, 'branch_mode':mode})
    observations = json.loads((RAW/'map_observations.json').read_text())
    for r in observations['walking_to_innovation']:
        if r['minutes'] <= walk_cap:
            paths.append({'origin_id':r['origin_id'], 'hub':'innovation', 'arrival':240+r['minutes']+gate,
                          'source':'map_walk', 'routes':['도보'], 'board_at':[], 'walk_minutes':r['minutes'], 'new_service':False})
    for r in strengthened.MAP['additional_walks']:
        if r['minutes'] <= walk_cap:
            paths.append({'origin_id':r['origin_id'], 'hub':r['hub'], 'arrival':240+r['minutes']+gate,
                          'source':'map_walk', 'routes':['도보'], 'board_at':[], 'walk_minutes':r['minutes'], 'new_service':False})
    if policy == 'feeder':
        for oid, stop, lag in [('49036','49035',0), ('49008','49007',6)]:
            w = ac.walk(oid,stop)
            if w <= walk_cap and 240+w+2 <= feeder_start+lag*factor:
                paths.append({'origin_id':oid, 'hub':'innovation', 'arrival':feeder_start+15*factor+gate,
                              'source':'policy_feeder', 'routes':['추가 연계편'], 'board_at':[feeder_start+lag*factor],
                              'walk_minutes':w, 'boarding_stop':stop, 'new_service':True})
    return paths, missing
