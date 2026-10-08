"""Read approved TAGO APIs. Never log keys or authenticated request URLs."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, unquote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CATALOG = {'intercity': '15098541', 'express': '15098522', 'train': '15098552'}

def credentials():
    values = {}
    for line in (ROOT / '.env').read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            name, value = line.split('=', 1)
            values[name.strip()] = value.strip().strip('\"\'')
    return values

def query(service, operation, params=None, label=None):
    params = dict(params or {})
    key = credentials().get(f'TAGO_{service.upper()}_API_KEY', '')
    if not key:
        return {'ok': False, 'service': service, 'error': 'MISSING_KEY'}
    spec = json.loads((ROOT / 'data/raw/tago_docs' / (CATALOG[service] + '.json')).read_text())
    path = '/' + operation.lstrip('/')
    if path not in spec['paths']:
        raise ValueError('Operation not present in saved official specification')
    endpoint = 'https://' + spec['host'] + spec.get('basePath', '') + path
    public_params = {'_type': 'json', **params}
    # Decode an accidentally supplied Encoding key once, then urlencode once.
    raw_key = unquote(key)
    request = Request(endpoint + '?' + urlencode({'serviceKey': raw_key, **public_params}))
    try:
        with urlopen(request, timeout=35) as response:
            body = response.read()
    except HTTPError as exc:
        return {'ok': False, 'service': service, 'error': 'HTTP_ERROR', 'http_status': exc.code}
    except (URLError, TimeoutError, OSError) as exc:
        return {'ok': False, 'service': service, 'error': type(exc).__name__}
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        # XML gateway errors: return the short result code only, not a URL/body.
        import xml.etree.ElementTree as ET
        try:
            tree = ET.fromstring(body)
            code = tree.findtext('.//returnReasonCode') or tree.findtext('.//resultCode')
        except ET.ParseError:
            code = None
        return {'ok': False, 'service': service, 'error': 'NON_JSON_RESPONSE', 'result_code': code}
    payload = data.get('response', data)
    header = payload.get('header', {})
    if str(header.get('resultCode')) not in ('00', '0', '0000'):
        code = str(header.get('resultCode', 'MISSING_HEADER'))
        return {'ok': False, 'service': service, 'error': 'API_ERROR', 'result_code': code[:32]}
    # A defensive check prevents accidental key echo from entering the cache.
    text = body.decode('utf-8')
    if key in text or raw_key in text:
        return {'ok': False, 'service': service, 'error': 'CREDENTIAL_ECHO_NOT_SAVED'}
    content = payload.get('body') or {}
    items = (content.get('items') or {}).get('item', []) if isinstance(content.get('items'), dict) else []
    if isinstance(items, dict):
        items = [items]
    now = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    result = {'ok': True, 'service': service, 'count': len(items), 'total_count': content.get('totalCount', len(items)), 'items': items}
    if label:
        if not label.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Invalid cache label')
        out = ROOT / 'data/raw/tago'
        out.mkdir(exist_ok=True)
        file = out / (label + '.json')
        file.write_bytes(body)
        manifest = {'endpoint': endpoint, 'parameters': public_params, 'retrieved_at_kst': now, 'sha256': hashlib.sha256(body).hexdigest(), 'source': f'https://www.data.go.kr/data/{CATALOG[service]}/openapi.do', 'file': str(file.relative_to(ROOT))}
        file.with_suffix('.meta.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        result['file'] = str(file.relative_to(ROOT))
    return result

if __name__ == '__main__':
    from concurrent.futures import ThreadPoolExecutor
    def check(service):
        result = query(service, 'GetCtyCodeList', label=service + '_cities')
        result.pop('items', None)
        return result
    with ThreadPoolExecutor(3) as pool:
        for result in pool.map(check, CATALOG):
            print(json.dumps(result, ensure_ascii=False), flush=True)
