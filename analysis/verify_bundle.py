"""Verify every bundled hash and reproduce the latest outputs without networking."""
import hashlib,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];bundle=ROOT/'output/jinju_public_data_reproduction.zip'
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None,'ZIP integrity'
    names=z.namelist()
    assert not any(Path(n).is_absolute() or '..' in Path(n).parts or Path(n).name=='.env' or '__pycache__' in n for n in names),'Unsafe bundled path'
    manifest=json.loads(z.read('outputs/strengthened/source_manifest.json'))
    for r in manifest['files']:
        b=z.read(r['path']);assert hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'],r['path']
    expected={n:z.read(n) for n in ['outputs/robust/analysis.json','outputs/robust/validation.json','outputs/robust/alias_audit.json','outputs/robust/recovered_transfer_paths.json','outputs/robust/calendar_destination_comparison.csv','outputs/decisions/analysis.json','outputs/decisions/validation.json','outputs/decisions/arrival_opportunities.csv','outputs/decisions/departure_constraints.csv','outputs/decisions/delay_comparison.csv','outputs/decisions/conditional_taxi.csv','outputs/decisions/focal_options.csv','outputs/decisions/walking_sensitivity.csv','outputs/decisions/walking_point_options.csv']}
    with tempfile.TemporaryDirectory(prefix='jinju-offline-reproduction-') as temp:
        target=Path(temp);z.extractall(target)
        guard=target/'network_guard';guard.mkdir();(guard/'sitecustomize.py').write_text("import socket\ndef blocked(*args,**kwargs):raise RuntimeError('Networking disabled during reproduction')\nsocket.socket.connect=blocked\nsocket.create_connection=blocked\n")
        env=os.environ.copy();env['PYTHONPATH']=str(guard);env['PYTHONDONTWRITEBYTECODE']='1'
        for script in ['repair_transfer_aliases.py','analyze_robustness.py','check_robustness.py','analyze_decisions.py','check_decisions.py']:
            completed=subprocess.run([sys.executable,'analysis/'+script],cwd=target,env=env,capture_output=True,text=True,timeout=90)
            assert completed.returncode==0,'Offline reproduction failed: '+script
        for name,b in expected.items():assert (target/name).read_bytes()==b,'Reproduction differs: '+name
result={'zip_sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'zip_bytes':bundle.stat().st_size,
        'files':len(names),'verified_file_hashes':len(manifest['files']),'network_disabled':True,
        'reproduced_files':list(expected),'exact_byte_match':True,'scope':'캐시 재현·ZIP 무결성·파일 해시 검증. 실제 운행·수요·견적을 검증하지 않음.'}
(ROOT/'output/jinju_reproduction_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('Verified hashes:',len(manifest['files']),'Offline exact outputs:',len(expected))
