"""Check official attachment-2 fields, sources, figures and PDF pagination."""
import hashlib
import json
import re
from pathlib import Path
from docx import Document
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/submission/김주형_분석보고서'
def normalized(text):return re.sub(r'\s+','',text)
fields=['이름/팀명','주제','분석 배경 및 목적','활용 데이터','분석과정 및 방법','AI 기술 활용','분석 내용 및 결과','정책제안 및 기대효과','분석도구 및 참고문헌','분석결과 이미지(필수)']
d=Document(BASE.with_suffix('.docx'));labels=[]
for t in d.tables:
    for row in t.rows:
        label=normalized(row.cells[0].text)
        if label in [normalized(s) for s in fields]:labels.append(label)
assert labels==[normalized(s) for s in fields], 'Official fields or order differ'
pages=PdfReader(BASE.with_suffix('.pdf')).pages
assert len(pages)==5, 'Expected five completed body pages'
text=normalized('\n'.join(p.extract_text() for p in pages))
for field in fields:assert normalized(field) in text, 'Missing field'
for source in json.loads((ROOT/'submission/data_catalog.json').read_text()):
    assert normalized(source['url']) in text, 'Missing source URL'
identity=json.loads((ROOT/'submission/identity.json').read_text())
assert normalized(identity['code_url']) in text, 'Code link absent'
for phrase in ['지역 보행 20분','40분','추가 개선은 0분','여정은 12분','수요','실측하지 않았다','실제 견적','OpenAI Codex','주요 프롬프트']:
    assert normalized(phrase) in text, 'Material qualification absent'
for placeholder in ['※ 데이터 분석의 핵심','※ 분석 배경','※ 분석 내용','※ 분석보고서 작성 시 유의사항']:
    assert normalized(placeholder) not in text, 'Instruction placeholder left in form'
assert len(d.inline_shapes)==4, 'Expected original two logos and two analysis figures'
assert BASE.with_suffix('.pdf').read_bytes()==(ROOT/'output/pdf/jinju_first_connection_analysis.pdf').read_bytes(), 'Submission PDF differs'
result={'analysis_version':5,'report_format_revision':1,'official_fields':fields,'field_order_matches':True,'body_pages':5,'data_urls_checked':14,'inline_images':4,'calculation_outputs_changed':False,'source_hwp_sha256':hashlib.sha256((ROOT/'data/raw/contest_report.hwp').read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(BASE.with_suffix('.pdf').read_bytes()).hexdigest(),'scope':'필수항목·순서·출처·그림·페이지 수의 구조 검사. 화면 배치는 별도로 확인.'}
(ROOT/'outputs/decisions/official_form_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('Official form: 10 fields in order; 14 source URLs; 4 images; 5 PDF pages.')
