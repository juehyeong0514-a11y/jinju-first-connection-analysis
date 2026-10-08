"""Create the six-page Korean analysis draft from computed results."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable
from analyze_connections import ROOT, hhmm

DATA=json.loads((ROOT/'outputs/connection_results.json').read_text())
AUDIT=json.loads((ROOT/'outputs/arrival_tradeoff_audit.json').read_text())
OUT=ROOT/'output/pdf/jinju_first_connection_analysis.pdf'
pdfmetrics.registerFont(TTFont('KR','/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KR',italic='KR',boldItalic='KR')
NAVY=colors.HexColor('#142E40');TEAL=colors.HexColor('#008584');GRAY=colors.HexColor('#586C7A');LIGHT=colors.HexColor('#EFF5F5');ORANGE=colors.HexColor('#BE6335')
style=ParagraphStyle('body',fontName='KR',fontSize=10.2,leading=16.5,textColor=NAVY,wordWrap='CJK',spaceAfter=9)
small=ParagraphStyle('small',parent=style,fontSize=8.5,leading=13,textColor=GRAY,spaceAfter=7)
title=ParagraphStyle('title',parent=style,fontSize=23,leading=30,spaceAfter=15)
sub=ParagraphStyle('sub',parent=style,fontSize=13,leading=19,textColor=TEAL,spaceBefore=9,spaceAfter=7)
story=[]
def p(text,s=style):return Paragraph(text,s)
def add(text,s=style):story.append(p(text,s))
def heading(n,name,kicker):
    add(f'{n:02d} / {kicker}',small);add(name,title)
def table(headers,rows,widths):
    allrows=[[p(str(x),small) for x in headers]]+[[p(str(x),small) for x in r] for r in rows]
    t=Table(allrows,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFB')])]))
    story.append(t);story.append(Spacer(1,10))
def page():story.append(PageBreak())

class ArrivalChart(Flowable):
    def __init__(self):Flowable.__init__(self);self.width=503;self.height=249
    def draw(self):
        c=self.canv;x0=130;scale=340/150
        def x(m):return x0+(m-540)*scale
        for t in [540,570,600,630,660]:
            c.setStrokeColor(colors.HexColor('#DFE8EB'));c.line(x(t),28,x(t),229)
            c.setFillColor(GRAY);c.setFont('KR',8);c.drawCentredString(x(t),10,hhmm(t))
        for i,(a,b) in enumerate(zip(DATA['baseline']['results'],DATA['scenarios'][1]['results'])):
            y=216-i*25;c.setFont('KR',9);c.setFillColor(NAVY);c.drawString(0,y-3,a['origin'])
            c.setStrokeColor(TEAL);c.setLineWidth(3);c.line(x(a['arrival']),y,x(b['arrival']),y)
            c.setFillColor(NAVY);c.circle(x(a['arrival']),y,4,fill=1,stroke=0)
            c.setFillColor(TEAL);c.circle(x(b['arrival']),y,3,fill=1,stroke=0)
            c.setFillColor(GRAY);c.setFont('KR',8);c.drawString(x(a['arrival'])+8,y-3,a['arrival_hhmm'])

heading(1,'첫차는 있어도, 연결 기회는 다르다','문제와 분석의 결론')
add('진주혁신도시·기존 주거지 대표 정류장의 새벽 버스·철도 접근성',sub)
add('분석 질문: 어느 주거지에서 서울의 같은 목적지에 더 일찍 도착할 수 있고, 첫 운행을 어떻게 보완하면 그 차이가 줄어드는가? 공통 목적지를 강남역으로 고정하고 지역 시내버스, 장거리버스, 철도, 서울 내 이동을 시간순으로 연결했다.')
table(['현재 확보한 분석 결과','의미'],[
('혁신도시 내 표본의 차이','승차장에 걸어갈 수 있는 표본과 시내버스 첫 운행을 기다려야 하는 표본의 기회가 갈린다.'),
('LH10·풀에버: 예상 10:51 → 09:21','도보 접근 한도 20분, 승차 여유 10분의 후보 경로 모형에서 04:50 연계편 추가 시 90분 앞당겨진다.'),
('철도도 함께 비교','진주 06:10 → 서울 09:52 / 광명 09:33 열차가 있지만, 일부 혁신도시 시내버스 경로는 진주역에 06:17 도착으로 추정된다.'),
('짧은 구간의 연계편이 유력','풀에버정문 → LH10 → 혁신도시 승차장 약 3.066km 구간에 추가 운행을 설정했다. 기존 운행은 유지한다.')
],[145,358])
add('이 문서에서 말하는 ‘도착’의 범위',sub)
add('2026년 10월 8일 시간표와 예상 이동시간으로 계산한 후보 경로 내 최솟값이다. 실제 승객의 도착 관측이나 진주 전체 교통망의 최적해를 의미하지 않는다. 출발점은 아파트 현관이 아닌 대표 버스정류장이다. 시외버스의 날짜 검증 공백과 일부 환승 경로의 자료 누락을 별도로 공개한다.')
add('제출용 최종본 전 단계: 계산·시각화·재현 코드가 포함된 분석 결과 초안. 팀명, 현장 관측, 운송사업자 협의 및 공개 코드 링크는 아직 확정하지 않았다.',small)
page()

heading(2,'데이터와 연결 계산','활용 데이터 / 분석과정 및 방법')
table(['자료','확보·사용 방법'],[
('진주 BIS [1]','평일 노선 변형 190개, 노선 정류장과 출발시각, 정류장 간 예상 소요시간. 직접 연결 후보 402개와 BIS 추천 경로를 결합.'),
('TAGO 고속버스 [2]','인증 성공. 진주·진주개양·진주혁신 → 서울경부의 기준일 시간표를 조회·원문 저장.'),
('TAGO 열차 [3]','인증 성공. 진주 → 서울·광명·수서·영등포·용산 조회. 출발·도착 시각 및 열차번호를 보존.'),
('TAGO 시외버스·터미널 [4,5]','인증 성공, 조사한 진주–서울 구간은 0건 응답. ‘운행 없음’으로 해석하지 않고, 공식 게시 시간표를 보조 분석에만 사용.'),
('카카오맵 [6]','혁신도시 승차장까지 도보, 서울 도착지 → 강남역 대중교통 예상시간을 화면에서 확인. 기준일 첫차 이후의 실제 환승 대기는 미검증.')
],[125,378])
add('계산 규칙',sub)
add('① 04:00 이후 출발, 지역 내 접근 보행 합계 최대 20분. ② 시내버스 승차 여유 2분, 승차장·역 내부 이동 5분, 장거리 승차 여유 10분. ③ 각 연결에서 ‘도착 + 여유 ≤ 다음 출발’인 편만 선택. ④ 후보 중 강남역 예상 도착시각의 최솟값을 구한다. 기점·종점의 출발시각 차이를 주행시간으로 사용하지 않았다.')
add('지도에서 확인한 승차장 직행 보행 외 짧은 정류장 연결은 직선거리 × 1.3, 시속 4km로 추정했다. 센텀리버파크 정류장은 지도에서 승차장과 같은 장소로 인식해 도보 수치가 없으므로, 접근·위치 확인에 5분을 가정했다. 비교한 나머지 승차장까지는 직선거리만으로도 40분을 넘는다. 도착지 대중교통은 지도 예상시간을 사용하고 실제 환승 대기는 한계로 명시한다.',small)
add('누락을 성공으로 바꾸지 않았다',sub)
add('BIS 추천 경로 1,014개 중 현재 노선의 정류장 순서에 대응되는 784개를 확보했다. 대응되지 않은 230개는 제외했다. 추가 점검에서 첫차 목록과 상세 시간표의 최초 시각이 다른 33개 노선·방향을 찾았다. 단축·분기 운행 여부를 확인하기 전에는 해당 경로를 제외한다. 시간 결측도 0분으로 채우지 않는다. 제외 후 핵심 도착시각은 유지되지만, 결과는 후보 범위에 조건부이다.',small)
page()

heading(3,'같은 혁신도시 안에서도 갈린다','분석 내용 및 결과')
story.append(ArrivalChart())
add('남색: 기존 / 청록: 04:50 연계편 추가. 가로축: 강남역 예상 도착시각. 날짜가 확인된 고속버스·철도 후보 기준. 지도 연결시간은 실제 대기시간을 보장하지 않는다.',small)
table(['대표 출발 정류장','기존','개선','도착 앞당김'],[[r['origin'],r['arrival_hhmm'],DATA['scenarios'][1]['results'][i]['arrival_hhmm'],str(round(r['arrival']-DATA['scenarios'][1]['results'][i]['arrival']))+'분'] for i,r in enumerate(DATA['baseline']['results'])],[203,90,90,120])
add('가까운 거리끼리 비교한 결과',sub)
add('풀에버정문과 퀸즈웰가는 시외터미널 인근 정류장까지 직선거리가 각각 약 4.59km, 4.60km로 비슷하다. 기준 모형에서는 강남역 예상 도착이 각각 10:51, 10:01로 50분 차이 난다. 다만 거리 하나를 맞춘 두 표본이며, 토지이용·인구·수요를 통제한 인과효과는 아니다.',small)
add('시외버스 보조 분석: 날짜가 명시되지 않은 공식 서울남부행 시간표를 포함하면 기존 시가지 네 표본의 예상 도착은 09:46으로 바뀐다. 핵심 표본인 LH10·풀에버의 기존 10:51, 연계편 추가 09:21은 이 보조 분석에서도 동일하다.',small)
page()

heading(4,'약 3.1km를 연결하는 추가 운행','정책제안 및 기대효과')
add('우선 검토안: 04:50 풀에버정문 → 04:56경 LH10 → 혁신도시 승차장',sub)
add('150번 경로의 해당 구간을 따르는 연계편을 추가한다. 정류장 소요시간 조회는 11분, BIS 경로검색은 803초(약 13.4분)를 제시해 계획 주행시간을 15분으로 두었다. 05:30 서울경부행에 연결되면 장거리 도착 09:05 + 강남역 연결 16분 = 예상 09:21이다.')
table(['대안','LH10·풀에버 예상','판단'],[
('04:50 단거리 연계편 추가',DATA['scenarios'][1]['results'][1]['arrival_hhmm']+' / 90분 앞당김','승객 운송구간 약 3.066km, 계획 15분. 출고·회송·휴게 제외.'),
('150번 04:40 조기편 추가',DATA['scenarios'][2]['results'][1]['arrival_hhmm']+' / 90분 앞당김','기존 05:30편 유지. 공식 노선표의 편도 거리 19km에 해당하는 추가 운행이 필요.'),
('150-1번 05:05 조기편 추가',DATA['scenarios'][3]['results'][1]['arrival_hhmm']+' / '+str(round(DATA['baseline']['results'][1]['arrival']-DATA['scenarios'][3]['results'][1]['arrival']))+'분 앞당김','06:10 열차 연결 대안. 광명역 이후 대기시간에 민감하므로 서울역 도착 대안도 함께 본다.')
],[153,126,224])
add('04:50 출발을 선택한 이유',sub)
add('계획 주행 15분이 20% 늘어난 18분이어도, 04:50 + 18분 + 승차장 이동 5분 + 승차 여유 15분 = 05:28이다. 05:30편에 2분의 추가 여유가 남는다. 이는 설정한 지연 범위에서의 계산이며 운행 보증은 아니다.')
add('정책 효과의 단위',sub)
add('확보한 두 대표 정류장의 연결 기회와 도착시각 개선이다. 두 단지 주민 전체가 90분씩 절약한다거나 일일 승객 수·편익·탄소 감축량을 확정하지 않는다. 차고지와 차량·기사 배치, 회송거리, 실제 새벽 승차 수요를 조사한 뒤 시범운행 여부를 결정해야 한다.')
add('90분 앞당김과 총 이동시간 절약은 다르다',sub)
table(['직통 시내버스 후보 비교','기존 출발 → 도착','연계편 출발 → 도착'],[[r['origin'],r['baseline_latest_start']+' → '+r['baseline_arrival'],r['policy_latest_start']+' → '+r['policy_arrival']] for r in AUDIT['tradeoffs']],[153,175,175])
add('기존 300번 후속편을 포함한 예시에서 두 표본은 95분 일찍 출발해 90분 일찍 도착하므로 총 이동시간은 각각 5분 늘어난다. 접근 보행·시내버스 여유를 양쪽 모두 2분씩 적용했다. 전체 교통망의 최후 출발시각이나 실측은 아니다. 편익은 시간가치 × 90분으로 환산하지 않는다.',small)
page()

heading(5,'어떤 가정에서 효과가 유지되는가','민감도 / 한계 / AI 기술 활용')
rows=[]
for cap in [10,20,30,40]:
    b=next(s for s in DATA['sensitivity'] if s['parameters']['walk_cap']==cap and s['parameters']['city_runtime_multiplier']==1 and s['parameters']['policy']=='baseline')
    rows.append([str(cap)+'분',b['results'][1]['arrival_hhmm'],b['results'][2]['arrival_hhmm'],'26분·32분 보행 허용 여부에 따라 변화'])
table(['도보 접근 한도','LH10 기존','풀에버 기존','해석'],rows,[96,85,85,237])
add('도보 한도 20분에서 지역 주행시간 20% 증가, 장거리 승차 여유 5·10·15분을 바꾼 조합에서도 04:50 연계편은 두 표본을 05:30편에 연결한다. 두 표본이 26·32분을 걸을 수 있으면 이미 같은 장거리편을 탈 수 있으므로, 추가 연계편의 도착시각 단축은 각각 사라진다. 그 경우 편익은 보행 부담·접근성 개선으로 해석해야 한다.',small)
add('목표 도착시각별 기회',sub)
table(['강남역 도착 기한','기존','연계편 추가'],[[r['deadline'],str(r['baseline_count'])+' / 8곳',str(r['policy_count'])+' / 8곳'] for r in AUDIT['deadline_access']],[233,135,135])
add('09:00 도착은 이 연계편으로 해결되지 않는다. 표본 수는 주민 비율이 아니며, 실제 환승 대기·지연에 따라 기한 판정은 바뀔 수 있다.',small)
add('분석의 한계와 제출 전 검증',sub)
add('• 8개 표본은 도시 전체를 대표하지 않는다. 기존 시가지 네 표본이 모두 251번을 이용하므로 다른 노선 생활권과 아파트 출입구까지 확대해야 한다.<br/>• 중간 승차장 탑승시각·시내버스 첫 통과·서울 내 환승 대기·시외버스 누락을 확인해야 한다. 실제 새벽 수요, 차량·기사 배치, 회송과 비용도 필요하다.<br/>• 10/13·17·18 장거리 API 추가 조회에서 고속버스는 빈 응답이었다. 10/17·18 열차 첫 편은 확인했지만 전체 주말 연결은 미검증이다.<br/>• 모든 지역·철도 환승 조합을 완전 탐색한 결과는 아니다.',small)
add('AI 활용 내역',sub)
add('ChatGPT/Codex를 공식 자료 탐색, API 수집, Python 정제·시간순 경로 계산, 민감도·한계 점검과 문서 작성에 사용했다. 주요 요청: ‘첫차로 터미널 새벽 첫차를 탈 수 있는지’, ‘같은 목적지 도착시각과 첫 운행 조정 효과 분석’, ‘기차 포함’, ‘더 구체화할 부분 점검’. 별도 예측모델 학습이나 현장 관측은 수행하지 않았다.',small)
page()

heading(6,'출처와 재현 방법','참고문헌 / 분석도구')
sources=[
('[1] 진주시 교통정보센터','진주시 · 진주 BIS','https://bis.jinju.go.kr/addInfo/addInfoTimeTable.do','시간표 PDF(2026.08.18 적용), 노선·정류장, 소요시간 및 환승검색. 원문·요청조건 로컬 보관.'),
('[2] 국토교통부(TAGO) 고속버스정보','국토교통부 · 공공데이터포털','https://www.data.go.kr/data/15098522/openapi.do','2026.10.08 출발 시간표. 진주/개양/혁신 → 서울경부.'),
('[3] 국토교통부(TAGO) 열차정보','국토교통부 · 공공데이터포털','https://www.data.go.kr/data/15098552/openapi.do','2026.10.08 진주 출발 열차. 도착역별로 별도 조회.'),
('[4] 국토교통부(TAGO) 시외버스정보','국토교통부 · 공공데이터포털','https://www.data.go.kr/data/15098541/openapi.do','서비스 인증 성공. 조사 구간 0건 응답을 결측으로 취급.'),
('[5] 진주시외버스터미널 운행정보','진주시외버스터미널 · 공식 웹사이트','http://jinjuterminal.kr/index.php?mid=sub_2_1','서울남부행 첫차 04:40 및 이후 게시 시간표. 적용일 미표시이므로 보조 분석에 한정.'),
('[6] 카카오맵','카카오 · 카카오맵','https://map.kakao.com/','2026.10.08 화면 조회. 출발·도착 지점 및 읽은 값을 map_observations.json에 기록.'),
('[7] 공모전 안내와 분석보고서 양식','숲과나눔 · 공식 웹사이트','https://koreashe.org/board/?mode=view&amp;board_id=22&amp;post_id=95427','본문 5장 내외, 분석결과 이미지 및 AI 활용·정책제안 등의 필수 항목 확인.')]
for name,provider,url,desc in sources:
    add(name,sub);add(provider+'<br/><link href="'+url+'" color="#008584">'+url+'</link><br/>'+desc,small)
add('재현: Python 3.12. API: analysis/tago_client.py, analysis/refresh_tago.py. 경로 수집: collect_case_times.py, collect_transfers.py, prepare_transfer_times.py. 계산: analyze_connections.py. 보고서: build_connection_report.py. 결과 JSON·비교 CSV와 원문 캐시 포함. API 키는 .env에만 보관하며 제출물에 포함하지 않는다. 공개 코드 링크는 아직 발행하지 않았다.',small)

def footer(c,doc):
    c.setFillColor(TEAL);c.rect(0,833,595.276,9,fill=1,stroke=0)
    c.setStrokeColor(colors.HexColor('#D6E2E6'));c.line(44,46,551,46)
    c.setFillColor(GRAY);c.setFont('KR',8);c.drawString(44,31,'2026.10.08 | 후보 경로·예상시간 기반 분석 결과 초안 | 실측·수요 검증 전')
    c.drawRightString(551,31,str(doc.page))

doc=SimpleDocTemplate(str(OUT),pagesize=(595.276,841.89),rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=61,title='첫차는 있어도, 연결 기회는 다르다',author='분석 초안 / Codex 협업')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
