"""Build the Korean evidence-and-design brief. Requires reportlab."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT/'outputs/pilot_results.json').read_text())
OUT = ROOT/'output/pdf'; OUT.mkdir(parents=True, exist_ok=True)
PATH = OUT/'newtown_first_bus_pilot.pdf'
FONT = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
pdfmetrics.registerFont(TTFont('KR', FONT))
W,H=595.276,841.89
NAVY=HexColor('#122B3C'); TEAL=HexColor('#087E83'); RED=HexColor('#BC4F38')
GRAY=HexColor('#5B6873'); LIGHT=HexColor('#EAF2F4'); BORDER=HexColor('#CFDCE0')
c=canvas.Canvas(str(PATH), pagesize=(W,H))
c.setTitle('같은 도시, 다른 첫차 | 신도시 교통 주제 검증 및 예비분석')
c.setAuthor('분석 초안 · Codex와 공동 작업')

def text(x,y,s,size=11,color=NAVY):
    c.setFillColor(color);c.setFont('KR',size);c.drawString(x,y,s)

def para(y,s,size=11,leading=17,x=44,width=W-88,color=NAVY):
    st=ParagraphStyle('p',fontName='KR',fontSize=size,leading=leading,textColor=color,wordWrap='CJK')
    p=Paragraph(s,st);_,h=p.wrap(width,900);p.drawOn(c,x,y-h)
    return y-h

def rule(y):
    c.setStrokeColor(BORDER);c.setLineWidth(.6);c.line(44,y,W-44,y)

def header(n,eyebrow,title,subtitle=None):
    c.setFillColor(TEAL);c.rect(0,H-9,W,9,fill=1,stroke=0)
    text(44,H-43,eyebrow,10,TEAL)
    text(44,H-82,title,24)
    if subtitle:para(H-98,subtitle,10,15,color=GRAY)
    rule(48)
    text(44,30,'2026.10.08 자료 확인 · 주제 검증 및 예비분석 · 제출용 최종본 아님',8,GRAY)
    c.drawRightString(W-44,30,f'{n} / 6')

def sub(y,title):
    text(44,y,title,14,TEAL);return y-15

def note(y,title,body,color=TEAL,height=82):
    c.setFillColor(LIGHT);c.roundRect(44,y-height,W-88,height,7,fill=1,stroke=0)
    c.setFillColor(color);c.rect(44,y-height,3,height,fill=1,stroke=0)
    text(58,y-22,title,12,color)
    para(y-32,body,10,15,58,W-116)
    return y-height-20

def table(y,headers,rows,widths,row_h=39,size=10):
    x0=44
    c.setFillColor(NAVY);c.rect(x0,y-29,sum(widths),29,fill=1,stroke=0)
    x=x0
    for h,w in zip(headers,widths):
        para(y-7,h,9,12,x+8,w-16,white);x+=w
    y-=29
    for i,row in enumerate(rows):
        if i%2==0:
            c.setFillColor(LIGHT);c.rect(x0,y-row_h,sum(widths),row_h,fill=1,stroke=0)
        x=x0
        for value,w in zip(row,widths):
            para(y-9,str(value),size,14,x+8,w-16);x+=w
        y-=row_h
    return y

header(1,'RESEARCH DECISION  /  01','같은 도시, 다른 첫차','지방 신도시와 기존 주거지의 새벽 장거리버스 접근성 · 진주 예비분석')
y=note(703,'권고: 신도시를 중심으로 하되, 같은 도시의 기존 주거지와 비교','신도시끼리의 넓은 비교보다 진주혁신도시 한 곳에서 연결 문제와 개선 효과를 끝까지 검증하는 구성이 적합하다. 지역 선정 이유는 자료 확보 가능성이며, 진주의 문제가 가장 심하다는 뜻은 아니다.',height=99)
y=sub(y-5,'주제의 중심은 ‘터미널까지의 거리’보다 ‘실제로 탈 수 있는 첫차’')
y=para(y,'집에서 출발해 시내버스·도보로 장거리버스에 연결하고 목적지까지 도착하는 전 과정을 비교한다. 터미널 첫차를 놓쳐도 혁신도시 내 중간 정류장에서 다른 편을 탈 수 있다면 그 대안을 포함한다. 신도시가 불리하다는 결론은 미리 정하지 않는다.')
y-=28
cards=[('04:40','서울남부행 첫 출발','진주시외터미널 공식 안내 [2]'),('05:00','시내버스 첫 운행','평일·토요일·휴일 목록 [1]'),('미확정','신도시의 상대적 불리함','직접 승차 대안·실제 경로 필요')]
for i,(big,label,foot) in enumerate(cards):
    x=44+i*174
    c.setFillColor(LIGHT);c.roundRect(x,y-103,160,103,6,fill=1,stroke=0)
    text(x+12,y-33,big,25,TEAL if i<2 else GRAY)
    text(x+12,y-58,label,11)
    para(y-71,foot,8.7,12,x+12,136,GRAY)
y-=133
y=sub(y,'현재 판단')
y=table(y,['항목','판단과 이유'],[
('문제 존재','04:40편은 같은 날 시작하는 정기 시내버스로 터미널에 와서 탈 수 없다.'),
('신도시 차별성','혁신도시 직접 승차편이 존재한다. 터미널 연결 실패를 장거리 이동 불가로 일반화하면 안 된다.'),
('공모전 적합성','이동 기회의 격차를 발견하고 구체적 정책을 제안한다는 공모 취지와 맞는다. [4]'),
('완성 가능성','공식 자료는 확보했다. 정류장별 통과시각과 날짜별 장거리편을 검증해야 분석을 완결할 수 있다.')
],[101,406],row_h=52)
para(y-14,'추천 가제: 「같은 도시, 다른 첫차 — 진주혁신도시와 기존 주거지의 새벽 장거리버스 접근성」',10,15,color=GRAY)
c.showPage()

header(2,'VERIFIED FINDINGS  /  02','시간표만으로 증명되는 연결 공백','확인 대상: 진주시 정기 시내버스 → 진주시외버스터미널 → 서울남부터미널')
y=table(703,['공식 시간표 구분','노선 변형 레코드','표시 노선명 수','가장 이른 출발'],[
    (d['day_type'],d['variant_records'],d['distinct_display_route_labels'],d['earliest_departure']) for d in DATA['day_summaries']
],[139,118,104,146],row_h=30)
y=para(y-12,'레코드는 분기·단축 운행을 포함한 목록 행이다. 운행 횟수나 실제 차량 수가 아니다. 표시 노선명 수는 고유 brt_name 수이며, 첫차는 각 기점·종점의 출발시각이다. [1]',9,14,color=GRAY)
y-=22
text(44,y,'04:40편의 연결 조건: 터미널에 04:30까지 도착',13,TEAL)
axis_y=y-89;x1=73;x2=527
def tx(m):return x1+(m-240)/120*(x2-x1)
c.setFillColor(HexColor('#F9E9E3'));c.rect(tx(270),axis_y-17,tx(300)-tx(270),36,fill=1,stroke=0)
c.setStrokeColor(BORDER);c.line(x1,axis_y,x2,axis_y)
for m in [240,270,280,300,330,360]:
    c.line(tx(m),axis_y-4,tx(m),axis_y+4)
    text(tx(m)-14,axis_y-20,f'{m//60:02}:{m%60:02}',8,GRAY)
for m,label,dy,col in [(270,'04:30 도착 필요',53,RED),(280,'04:40 시외버스 출발',30,RED),(300,'05:00 시내버스 운행 시작',78,TEAL)]:
    c.setStrokeColor(col);c.line(tx(m),axis_y+4,tx(m),axis_y+dy-14)
    c.setFillColor(col);c.circle(tx(m),axis_y,3,fill=1,stroke=0)
    text(tx(m)-48,axis_y+dy-8,label,9,col)
y=axis_y-47
y=table(y,['장거리 출발','10분 전 도착 기준','판정'],[
    ('04:40','04:30','연결 불가 · 이동시간을 0분으로 가정해도 30분 부족'),
    ('05:00','04:50','연결 불가 · 같은 가정에서도 10분 부족'),
    ('05:30 이후','05:20 이후','미판정 · 버스가 운행한다고 터미널 접근이 보장되지는 않음')
],[96,115,296],row_h=40)
y=para(y-15,'10분은 분석자가 설정한 승차 여유시간이며 운영기관의 의무 규정이 아니다. 04:40편은 여유시간을 0분으로 줄여도 시내버스 출발이 20분 늦다. 30분은 필요한 운행 조정량의 하한일 뿐, 첫차를 30분 앞당기면 해결된다는 뜻이 아니다.',10,15)
y=note(y-19,'00:00 데이터를 실제 심야 첫차로 처리하지 않았다','151·151-1번의 역방향 0000 표기 3개는 PDF 35~36쪽에서 해당 방향 상세 출발칸이 비어 있음을 확인했다. 이 특정 항목만 제외했다. 전날 이동 후 대기, 택시, 자가용, 비정기 운송은 위 판정 범위 밖이다.',height=82)
c.showPage()

header(3,'SPATIAL PILOT  /  03','거리 차이와 첫차 차이는 구분해야 한다','공식 정류장 좌표로 계산한 예비 비교 · 임의 선정한 6개 표본이며 주민 전체를 대표하지 않음')
text(44,692,'시외터미널 인근 시내버스 정류장까지의 직선거리',13,TEAL)
labels=['센텀리버파크 인근','LH10단지','풀에버정문 인근','LH3/LH5단지','중앙시장(주차장)','퀸즈웰가아파트']
x0=222;scale=42
for i,(row,label) in enumerate(zip(DATA['spatial_samples'],labels)):
    y=645-i*40;d=row['distance_to_terminal_stop_proxy_km']
    text(44,y-3,label,10)
    c.setFillColor(TEAL if i<4 else GRAY);c.roundRect(x0,y-7,d*scale,16,3,fill=1,stroke=0)
    text(x0+d*scale+8,y-3,f'{d:.2f} km',10)
text(44,387,'청록: 혁신도시 표본   /   회색: 기존 시가지 비교 후보',9,GRAY)
para(368,'정류장명은 축약 표기했다. 거리는 각 출발 정류장과 터미널 인근 두 시내버스 정류장 중 가까운 쪽의 좌표로 계산했다. 터미널 승차홈까지의 보행거리·시간이 아니며 도로, 하천 횡단 및 출입구를 반영하지 않는다. [1]',9,14,color=GRAY)
y=note(302,'확인된 시사점: 비슷한 거리의 기존 주거지도 비교해야 한다','풀에버정문 표본 4.59km와 퀸즈웰가 표본 4.60km는 터미널에서의 직선거리가 비슷하다. 이 두 지점의 실제 이용 가능 첫 편이 다르다면, 거리 외에 운행시각·환승·중간 정차가 차이를 만드는지 검토할 수 있다.',height=101)
y=sub(y-3,'신도시 직접 승차편을 빼면 분석이 왜곡된다')
y=para(y,'주택관리공단 공식 안내는 진주혁신도시 사옥 앞 장거리버스 승차 위치와 서울 등 행선지를 안내한다. 다만 이 페이지는 날짜별 첫차시각을 제공하지 않는다. 따라서 현재 확보한 자료로 혁신도시 주민의 서울 이동 자체가 불가능하다고 판단할 수 없다. [3]',10.5,16)
para(y-14,'다음 계산은 터미널 접근 경로와 혁신도시 직접 승차 경로를 함께 비교해야 한다. 05:00 이후에는 정류장별 통과시각을 확보하기 전까지 접근 가능·불가를 확정하지 않는다.',10,15,color=GRAY)
c.showPage()

header(4,'ANALYSIS DESIGN  /  04','완성도는 ‘도착 기회’와 ‘개선 효과’에서 나온다','권장 범위: 진주혁신도시 + 진주 기존 주거지 · 서울 방면 장거리버스 · 비교 날짜별 분석')
y=sub(698,'1. 비교 단위와 목적지를 고정한다')
y=para(y,'신도시·기존 시가지에서 주거지 출입구를 각각 6~10곳 선정한다. 터미널과의 거리, 주거 밀도, 정류장까지의 거리 구간을 맞춰 비교한다. 중앙시장 같은 터미널 인접 지점은 참고 사례로 분리한다. 표본 결과를 도시 전체 인구 비율로 표현하지 않는다.',10.5,16)
y=para(y-10,'서울남부·서울경부처럼 도착 터미널이 다르면 같은 기회로 볼 수 없다. 본 분석은 공통 최종 목적지(예: 강남역)를 정한 뒤 서울 내 이동까지 합산하거나, 목적지별 결과를 별도 제시한다. 철도를 제외할 때는 ‘버스 이용 기회’로 해석 범위를 제한한다.',10.5,16)
y=sub(y-29,'2. 경로를 시간순으로 연결한다')
flow_y=y-13
boxes=[('집 출입구',78),('시내버스·도보',125),('모든 승차 지점',127),('장거리편 + 도착지 이동',147)]
x=44
for label,width in boxes:
    c.setFillColor(LIGHT);c.roundRect(x,flow_y-34,width-12,34,4,fill=1,stroke=0)
    para(flow_y-9,label,9,13,x+6,width-24)
    x+=width
    if x<540:text(x-11,flow_y-21,'>',11,TEAL)
y=para(flow_y-52,'각 연결은 ‘도착시각 + 필요한 승차 여유시간 ≤ 다음 편 출발시각’일 때만 인정한다. 기점·종점의 출발시각 차이를 주행시간으로 쓰지 않는다. 회차·대기시간과 서로 다른 운행편이 섞일 수 있기 때문이다.',10.5,16)
y=table(y-22,['핵심 지표','계산·해석'],[
('실제 이용 가능 첫 편','주거지에서 출발해 연결 가능한 편 중 가장 이른 장거리 출발편'),
('가장 이른 도착','접근·환승·장거리 이동·도착지 이동을 합친 가장 이른 도착시각'),
('아침 도착 기회','08:30 / 09:00 / 10:00 도착 가능 여부를 나란히 제시'),
('추가 대기·지연','연결 단절 때문에 놓친 편과 다음 이용 가능 편의 도착시각 차이')
],[140,367],row_h=40)
y=sub(y-29,'3. 정책 대안을 같은 조건에서 비교한다')
y=para(y,'기존 시내버스 첫 운행 조정, 주거지→승차 지점 단거리 연계편, 장거리버스의 혁신도시 조기 정차를 후보로 둔다. 대안마다 새로 연결되는 표본·인구, 절감되는 도착 지연, 추가 차량시간·운행거리를 비교한다. 감축 운행이나 인력 재배치가 있으면 기존 이용자의 손실도 계산한다.',10.5,16)
para(y-12,'정책을 선택할 때에는 실제 수요와 운행 여건이 필요하다. 시간표만으로 이용자 수·예산·탄소 감축량을 확정하지 않는다. 탄소효과는 추가 버스 운행과 대체된 자가용 이동을 함께 두고 민감도 분석한다.',9.5,15,color=GRAY)
c.showPage()

header(5,'DELIVERY & QUALITY  /  05','지금 확인한 것과 제출 전 채워야 할 것','현재는 주제 검증과 시간·공간 하한 분석을 완료한 단계다. 접근성 순위와 정책 효과는 아직 계산하지 않았다.')
y=table(696,['상태','작업·필요 근거'],[
('완료','공식 시내버스 PDF와 요일별 첫차 목록 확보, 예외값 점검, 서울남부행 초기 출발편 확인'),
('완료','23개 노선 변형의 정류장 표본 수집, 6개 지점 거리 계산, 04:40·05:00편 연결의 시간 하한 검증'),
('필수 보완','기준 날짜별 시외·고속버스 및 혁신도시 중간 정류장 출발편을 공식 예매 정보로 대조'),
('필수 보완','비교 주거지의 실제 보행 경로·승차홈 위치와 시내버스 정류장별 첫 통과시각 확보'),
('필수 보완','기존·개선 시나리오 재계산, 표본 경로 수동 검증, 변화 폭과 불확실성 제시')
],[85,422],row_h=43)
y=sub(y-28,'데이터가 부족할 때의 정직한 분석 범위')
y=para(y,'정류장별 도착시각을 확보하지 못하면 05:00 이후 경로를 임의 평균속도로 확정하지 않는다. 교통정보센터 자료나 실제 첫 운행 관측으로 검증하거나, 가정별 소요시간 구간을 두고 ‘확실히 연결 / 조건부 연결 / 확실히 불가’로 제시한다. 세부 자료 부족이 계속되면 검증 가능한 표본 경로 중심으로 범위를 줄인다.',10.5,16)
y=sub(y-29,'AI 활용은 실제 수행한 작업을 기록한다')
y=para(y,'사용 도구: ChatGPT/Codex. 현재 활용 범위: 공식 자료 탐색, 시간표 구조 점검, Python 정제·계산 코드 작성, PDF 초안 작성. 주요 입력: 첫차 연결 가능성 검토 요청, 신도시 비교 제안, 최상의 결과물을 목표로 한 분석 요청. 수요 예측 모델을 학습했거나 현장 관측을 수행한 것으로 기재하지 않는다.',10.5,16)
y=sub(y-29,'권장 제출 구성')
y=para(y,'문제와 비교 설계 → 데이터·연결 계산 → 지역별 결과 지도 및 도착시각 분포 → 2~3개 개선 대안의 효과 → 한계·AI 활용 내역. 공모전 양식의 분석 내용·결과, 정책제안, 분석결과 이미지 항목에 맞춘다. 접수 마감은 2026년 10월 22일이다. [4, 5]',10.5,16)
y=note(y-20,'최종 판단','신도시 방향을 유지할 가치가 있다. 다만 경쟁력은 ‘신도시’라는 이름보다, 중간 승차 대안까지 포함한 실제 연결 계산과 최소한의 운행 조정으로 얻는 개선 효과를 증명하는 데 있다.',height=80)
c.showPage()

header(6,'SOURCES & REPRODUCTION','출처와 재현 방법','이 페이지는 참고자료다. 수치는 2026년 10월 8일에 확보한 공개자료 스냅숏을 기준으로 계산했다.')
y=700
sources=[
('[1] 진주시 버스정보시스템 — 시간표 및 노선정보','https://bis.jinju.go.kr/addInfo/addInfoTimeTable.do','전체 PDF 파일명에 2026.08.18 표기. getBusTime.do의 평일·토요일·일요일/공휴일 목록을 저장. 노선 좌표는 공개 노선 화면의 MainBusRouteListAjax.do 응답. 0000 처리 근거는 PDF 35~36쪽.'),
('[2] 진주시외버스터미널 — 운행정보','http://jinjuterminal.kr/index.php?mid=sub_2_1','서울(남부터미널) 행선지 행에서 04:40, 05:00, 05:30 등의 출발시각 확인. 사이트 게시 시간표의 특정 운행일 적용 여부는 공식 예매 조회로 추가 대조해야 한다.'),
('[3] 주택관리공단 — 공단위치','https://kohom.or.kr/mobile/intro/mobileLocation.do?mobileType=56','혁신도시 사옥 앞 장거리버스 승차 위치 및 서울 등 행선지 안내 확인. 검색에 수록된 공식 페이지 본문을 사용했으며 직접 재접속은 시간 초과 또는 HTTP 417 응답. 출발시각 출처로 사용하지 않음.'),
('[4] 숲과나눔 — 공모전 공지','https://koreashe.org/notice/?mod=document&uid=95427','AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전. 접수 8월 18일~10월 22일. 이동 격차와 탄소중립에 기여하는 정책 아이디어 취지.'),
('[5] 공모전 공지의 붙임2 분석보고서 양식','https://koreashe.org/notice/?mod=document&uid=95427','활용 데이터, 분석 방법, AI 활용 서비스·범위·주요 프롬프트, 분석 결과, 정책제안, 참고문헌 및 결과 이미지 항목 확인. 원본 HWP와 추출 텍스트를 data/raw에 보관.')]
for title,url,body in sources:
    y=para(y,title,11,16)
    y=para(y-4,f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#087E83">공식 자료 열기</link>',9,13)
    y=para(y-4,body,9.5,14,color=GRAY)-18
y=sub(y-1,'계산 파일')
y=para(y,'analysis/analyze_pilot.py — 저장된 원본을 읽어 전체 수치 재계산 (Python 표준 라이브러리).<br/>outputs/pilot_results.json — 지표와 범위, 미해결 항목.<br/>outputs/source_manifest.json — 출처 URL, 요청 방식, SHA-256.<br/>outputs/*.csv — 정제 첫차시각, 제외 항목, 연결 판정, 공간 표본.',9.5,15)
y=para(y-12,'재현: python3 analysis/analyze_pilot.py<br/>보고서 생성: python3 analysis/build_pilot_report.py (reportlab 및 AppleGothic 글꼴 필요)<br/>노선 표본 재수집: python3 analysis/collect_route_samples.py',9.5,15,color=GRAY)
para(y-12,'표본은 모집단을 대표하도록 추출하지 않았다. 접근성 수치는 관측 수요가 아니다. 공식 시간표의 변경과 행사·휴일 예외를 제출 직전에 다시 확인해야 한다.',9.5,15,color=GRAY)
c.save()
print(PATH)
