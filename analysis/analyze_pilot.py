"""Reproduce the pilot using downloaded official snapshots (stdlib only).

Run from any directory: python3 analysis/analyze_pilot.py
No stop-level bus arrival times are inferred from terminal departure times.
"""
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw", ROOT / "outputs"
OUT.mkdir(exist_ok=True)
BASE = "https://bis.jinju.go.kr"
# The official PDF pp.35-36 has empty return-departure columns on these
# one-direction services, despite the summary header showing 0:00.
EMPTY_RETURN_IDS = {381015130, 381015131, 381115131}

def read(name):
    return json.loads((RAW / name).read_text())

def minute(value):
    value = value.replace(":", "")
    if not re.fullmatch(r"\d{4}", value):
        raise ValueError(value)
    h, m = int(value[:2]), int(value[2:])
    if h > 24 or m > 59:
        raise ValueError(value)
    return h * 60 + m

def hhmm(value):
    return f"{value//60:02d}:{value%60:02d}"

def distance_km(a, b):
    lat1, lat2 = math.radians(float(a["stop_y"])), math.radians(float(b["stop_y"]))
    dlat = lat2 - lat1
    dlon = math.radians(float(b["stop_x"]) - float(a["stop_x"]))
    v = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(v))

day_summaries, cleaned, excluded = [], [], []
for name, day, dtype in [("jinju_bus_times.json", "평일", "1"), ("jinju_bus_times_3.json", "토요일", "3"), ("jinju_bus_times_4.json", "일요일·공휴일", "4")]:
    rows = read(name)["rows"]
    values = []
    for row in rows:
        for key in ("firsttime", "ed_firsttime"):
            value = row.get(key)
            if value is None or value == "":
                continue
            record = {"day_type": day, "route_id": row["brt_id"], "route_label": row["brt_name"], "field": key, "raw_time": value}
            if value == "0000":
                if row["brt_id"] not in EMPTY_RETURN_IDS or key != "ed_firsttime":
                    raise ValueError(f"Unreviewed midnight record: {record}")
                excluded.append({**record, "reason": "Official PDF pp35-36 return columns blank; not a scheduled midnight trip"})
                continue
            value = minute(value)
            values.append(value)
            cleaned.append({**record, "minutes": value, "time": hhmm(value)})
    day_summaries.append({"day_type": day, "btt_type": dtype, "variant_records": len(rows), "distinct_display_route_labels": len({r["brt_name"] for r in rows}), "earliest_departure_min": min(values), "earliest_departure": hhmm(min(values))})

intercity = read("jinju_intercity_rows.json")
seoul = next(r for r in intercity if r[0] == "서울 (남부터미널)")
early_times = re.findall(r"\b([0-9]{2}:[0-9]{2})\b", seoul[3])[:6]
assert early_times == ["04:40", "05:00", "05:30", "06:00", "06:30", "07:00"], early_times
earliest = day_summaries[0]["earliest_departure_min"]
connections = []
for t in early_times:
    departure = minute(t)
    deadline = departure - 10
    # Optimistic lower bound: assume zero in-vehicle travel and zero walking.
    # Failure of this necessary condition proves infeasibility of a same-day
    # regular city-bus connection to this terminal. Passing does not prove access.
    connections.append({"coach_departure": t, "boarding_deadline_10min": hhmm(deadline), "earliest_citybus_any_origin": hhmm(earliest), "lower_bound_shortfall_min": max(0, earliest-deadline), "status": "연결 불가(시간 하한으로 증명)" if earliest > deadline else "미판정(정류장 도착시각 필요)"})

stops = {}
manif = read("route_samples/manifest.json")
for entry in manif:
    for row in json.loads((ROOT/entry["file"]).read_text())["rows"]:
        if row.get("stop_x") and row.get("stop_y"):
            stops[str(row["stop_id"])] = row
# Two city-bus terminal-adjacent stop coordinates are proxies. These are NOT
# coach boarding-gate coordinates; straight distances cannot establish walk access.
terminals = [stops["381231001"], stops["381231002"]]
selected = [("381249018", "혁신도시 표본"), ("381249008", "혁신도시 표본"), ("381249036", "혁신도시 표본"), ("381249022", "혁신도시 표본"), ("381227001", "기존 시가지 비교 후보"), ("381241001", "기존 시가지 비교 후보")]
spatial = []
for sid, area in selected:
    s = stops[sid]
    d = min(distance_km(s, terminal) for terminal in terminals)
    spatial.append({"stop_id": sid, "stop_name": s["stop_name"], "area_label": area, "longitude": float(s["stop_x"]), "latitude": float(s["stop_y"]), "distance_to_terminal_stop_proxy_km": round(d, 3), "straight_line_walking_lower_bound_min_4_5_kmh": round(d/4.5*60, 1), "can_establish_actual_walking_access": False})

result = {"snapshot_date_kst": "2026-10-08", "city_schedule_pdf_effective_label": "2026-08-18", "scope": "Regular city bus departures and Jinju intercity terminal Seoul-Nambu early departures; purposive spatial samples", "day_summaries": day_summaries, "excluded_midnight_records": excluded, "connections": connections, "spatial_samples": spatial, "sampled_route_variant_count": len(manif), "sampled_route_label_count": len({r['route_label'] for r in manif}), "unique_sampled_stop_ids": len(stops), "unresolved": ["Trip-date-specific coach departures and intermediate-stop boarding times", "Innovation-city direct coach departures, express-terminal alternatives and rail alternatives", "Stop-level earliest bus passages, boarding-gate coordinates and walkable paths", "Representative residential origins, population and demand weights"]}
(OUT/"pilot_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
for name, records in [("citybus_first_departures.csv", cleaned), ("terminal_connection_bounds.csv", connections), ("spatial_samples.csv", spatial), ("excluded_midnight_fields.csv", excluded)]:
    with (OUT/name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0])); w.writeheader(); w.writerows(records)

source_specs = [
    ("jinju_citybus_schedule.pdf", BASE+"/file/fileDownload.do?file_seq=1", "GET", {}),
    ("jinju_bus_times.json", BASE+"/addInfo/getBusTime.do", "POST", {"btt_type":"1"}),
    ("jinju_bus_times_3.json", BASE+"/addInfo/getBusTime.do", "POST", {"btt_type":"3"}),
    ("jinju_bus_times_4.json", BASE+"/addInfo/getBusTime.do", "POST", {"btt_type":"4"}),
    ("jinju_terminal_routes.html", "http://jinjuterminal.kr/index.php?mid=sub_2_1", "GET", {}),
    ("jinju_notices.json", BASE+"/bimsInfo/noticeListAjax.do", "POST", {}),
]
sources=[]
for file, url, method, params in source_specs:
    p=RAW/file; payload=p.read_bytes()
    sources.append({"file":str(p.relative_to(ROOT)),"url":url,"method":method,"parameters":params,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest(),"retrieved_date_kst":"2026-10-08"})
(OUT/"source_manifest.json").write_text(json.dumps(sources+manif, ensure_ascii=False, indent=2))
print(json.dumps({"day_summaries":day_summaries,"connections":connections[:3],"spatial_samples":spatial}, ensure_ascii=False, indent=2))
