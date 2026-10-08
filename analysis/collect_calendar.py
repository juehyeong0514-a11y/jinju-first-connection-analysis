"""Cache official BIS Saturday/Sunday tables, using documented UI parameters.

No credentials. A response is accepted only when its calendar class matches.
"""
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = RAW / 'strengthening/robust/citybus_calendar'

def collect(job):
    day, row = job
    target = OUT / f"{day}_{row['brt_id']}.json"
    if target.exists():
        return {'day': day, 'base': str(row['brt_id']), 'cached': True}
    params = {'brt_id': row['brt_id'], 'brt_no': row['brt_name'], 'btt_type': day}
    req = urllib.request.Request(
        'https://bis.jinju.go.kr/bimsRoute/BusRouteTimeTable.do',
        data=urllib.parse.urlencode(params).encode(),
        headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            payload = response.read()
        data = json.loads(payload)
        classes = {str(r.get('hldyClss')) for r in data.get('timeTable', [])}
        if classes and classes != {day}:
            rejected = OUT / f"rejected_{day}_{row['brt_id']}.json"
            rejected.write_bytes(payload)
            return {'day':day,'base':str(row['brt_id']),'error_type':'CalendarClassMismatch',
                    'returned_classes':sorted(classes),'rejected_file':str(rejected.relative_to(ROOT))}
        target.write_bytes(payload)
        return {'day': day, 'base': str(row['brt_id']), 'rows': len(data.get('timeTable', []))}
    except Exception as error:
        return {'day': day, 'base': str(row['brt_id']), 'error_type': type(error).__name__}

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    # The timetable endpoint returns the route-number family; retain per-base
    # requests so each variant can be audited independently against the summary.
    used = {str(p['source_route_id']) for p in json.loads((ROOT/'outputs/strengthened/direct_paths.json').read_text())}
    used.update(l['base'] for p in json.loads((ROOT/'outputs/strengthened/suggested_paths.json').read_text()) for l in p['legs'])
    jobs = [(d, r) for d in ['3', '4'] for r in json.loads((RAW/f'jinju_bus_times_{d}.json').read_text())['rows'] if str(r['brt_id']) in used]
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(collect, jobs))
    (OUT/'manifest.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print('Calendar requests:', len(results), 'errors:', sum('error_type' in r for r in results), flush=True)
