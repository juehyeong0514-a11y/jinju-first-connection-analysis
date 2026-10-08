"""Cache official Jinju route samples; public read-only website requests.

No API key is required for these endpoints used by the public bus website.
This is a purposive route sample, not a complete city network.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = RAW / "route_samples"
OUT.mkdir(exist_ok=True)
SELECTED = {"10", "124", "150", "150-1", "151", "151-1", "200", "251", "280", "281", "282", "290", "300", "300-1", "301", "301-1"}
BASE = "https://bis.jinju.go.kr"

def fetch(row):
    route_id = row["brt_id"]
    path = OUT / f"{route_id}.json"
    params = {"brt_id": str(route_id)}
    url = BASE + "/MainBusRouteListAjax.do"
    if not path.exists():
        req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), headers={"User-Agent": "Mozilla/5.0", "Referer": BASE + "/bimsRoute/bimsRoute.do"})
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read()
        parsed = json.loads(payload)
        if parsed.get("resultCode") != 200 or not parsed.get("rows"):
            raise RuntimeError(f"No route data: {route_id}")
        path.write_bytes(payload)
    payload = path.read_bytes()
    return {"file": str(path.relative_to(ROOT)), "url": url, "method": "POST", "parameters": params, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "retrieved_date_kst": "2026-10-08", "route_label": row["brt_name"]}

if __name__ == "__main__":
    rows = json.loads((RAW / "jinju_bus_times.json").read_text())["rows"]
    selected = [r for r in rows if r["brt_name"] in SELECTED]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, selected))
    (OUT / "manifest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Cached {len(results)} route variants / {len(set(r['route_label'] for r in results))} route labels.")
