"""Build a local allowlisted reproducibility bundle; never include credentials."""
import hashlib
import json
import urllib.parse
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=set()
def include(pattern):files.update(p for p in ROOT.glob(pattern) if p.is_file())
for pattern in ['analysis/*.py','RUN_ANALYSIS.txt','submission/*.json','output/pdf/jinju_first_connection*.pdf',
 'output/submission/*_분석보고서.pdf','output/submission/*_분석보고서.docx','output/submission/*.txt','output/submission/*.hwp',
 'data/raw/contest_report.hwp','data/raw/contest_report.txt','data/raw/contest_report_template.docx','data/raw/contest_report_assets/*.png',
 'outputs/all_stops.json','outputs/candidate_citybus_paths.json','outputs/suggested_transfer_paths.json',
 'outputs/strengthened/*.json','outputs/strengthened/*.csv','outputs/robust/*.json','outputs/robust/*.csv','outputs/decisions/*.json','outputs/decisions/*.csv','data/raw/strengthening/decisions/*.json',
 'data/raw/case_times/*.json','data/raw/citybus_timetables/*.json','data/raw/network/*.json','data/raw/transfer_candidates/*.json','data/raw/route_samples/*.json',
 'data/raw/tago/*.json','data/raw/jinju_bus_times*.json','data/raw/jinju_citybus_schedule.pdf','data/raw/map_observations.json',
 'data/raw/strengthening/*.json','data/raw/strengthening/*.xlsx','data/raw/strengthening/*.csv','data/raw/strengthening/citybus_schedule.txt','data/raw/strengthening/its/*.json',
 'data/raw/strengthening/robust/citybus_calendar/*.json','data/raw/strengthening/robust/jinju_housing_20260701.csv',
 'data/raw/strengthening/robust/kobus_calendar.json','data/raw/strengthening/robust/ktx_morning_rows.json',
 'data/raw/strengthening/robust/population_source.json','data/raw/strengthening/robust/public_sources.json',
 'data/raw/strengthening/robust/alias_time_manifest.json','data/raw/strengthening/robust/unlisted_network_*.json']:
    include(pattern)
manifest=ROOT/'outputs/strengthened/source_manifest.json'
files.discard(manifest)
files.discard(ROOT/'outputs/strengthened/preliminary_expansion.json')
# Compare to actual local secrets without logging any values.
secrets=[]
env=ROOT/'.env'
if env.exists():
    for line in env.read_text().splitlines():
        if '=' not in line or line.lstrip().startswith('#'):continue
        value=line.split('=',1)[1].strip().strip('\"\'')
        if len(value)>=12:secrets.extend([value.encode(),urllib.parse.unquote(value).encode(),urllib.parse.quote(value,safe='').encode()])
for p in files:
    b=p.read_bytes()
    if any(s in b for s in secrets):raise RuntimeError('Credential match in selected file; bundle not written')
rows=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)]
manifest.write_text(json.dumps(dict(scope='Local allowlisted analysis bundle; input/output hashes; no credentials',files=rows),ensure_ascii=False,indent=2))
files.add(manifest)
output=ROOT/'output/jinju_public_data_reproduction.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(files):z.write(p,p.relative_to(ROOT))
print('Bundle:',len(files),'files;',output.stat().st_size,'bytes. Actual local credential strings absent.')
