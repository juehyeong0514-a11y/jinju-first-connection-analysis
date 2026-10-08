"""Six-page submission narrative and an evidence appendix from computed outputs."""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,Flowable
from analyze_connections import ROOT,hhmm
D=json.loads((ROOT/'outputs/strengthened/analysis.json').read_text())
S=json.loads((ROOT/'outputs/strengthened/sample_selection.json').read_text())['origins']
M=json.loads((ROOT/'data/raw/strengthening/map_checks.json').read_text())
Q=json.loads((ROOT/'outputs/strengthened/collection_quality.json').read_text())
B,F=D['scenarios'][:2]
pdfmetrics.registerFont(TTFont('KR','/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KR',italic='KR',boldItalic='KR')
NAVY=colors.HexColor('#163547');TEAL=colors.HexColor('#008C88');GRAY=colors.HexColor('#526B79');LIGHT=colors.HexColor('#EDF5F5');AMBER=colors.HexColor('#B56036');PALE=colors.HexColor('#F7F9FB')
body=ParagraphStyle('body',fontName='KR',fontSize=10.1,leading=16.2,textColor=NAVY,wordWrap='CJK',spaceAfter=9)
small=ParagraphStyle('small',parent=body,fontSize=8.2,leading=12.8,textColor=GRAY,spaceAfter=6)
mini=ParagraphStyle('mini',parent=small,fontSize=7.4,leading=11,spaceAfter=2)
large=ParagraphStyle('large',parent=body,fontSize=24,leading=31,spaceAfter=12)
sub=ParagraphStyle('sub',parent=body,fontSize=12.6,leading=18.5,textColor=TEAL,spaceBefore=7,spaceAfter=7)
WIDTH=507
story=[]
def p(t,s=body):return Paragraph(str(t).replace('\n','<br/>'),s)
def add(t,s=body):story.append(p(t,s))
def head(k,title,kicker):add(f'{k} / {kicker}',small);add(title,large)
def page():story.append(PageBreak())
def table(headers,rows,widths=None,compact=False):
    widths=widths or [WIDTH/len(headers)]*len(headers)
    st=mini if compact else small
    t=Table([[p(x,st) for x in headers]]+[[p(x,st) for x in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('TEXTCOLOR',(0,0),(-1,0),TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5 if compact else 7),('BOTTOMPADDING',(0,0),(-1,-1),4),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE])]))
    story.append(t);story.append(Spacer(1,8))
def callout(text):
    t=Table([[p(text,ParagraphStyle('callout',parent=body,autoLeading='max'))]],colWidths=[WIDTH]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.5,TEAL),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,10))

class ArrivalPlot(Flowable):
    def __init__(self):super().__init__();self.width=WIDTH;self.height=385
    def draw(self):
        c=self.canv;left=174;scale=315/165
        def x(t):return left+(t-510)*scale
        for t in [510,540,570,600,630,660]:
            c.setStrokeColor(colors.HexColor('#DDE6EB'));c.setLineWidth(.5);c.line(x(t),24,x(t),372);c.setFillColor(GRAY);c.setFont('KR',8);c.drawCentredString(x(t),8,hhmm(t))
        c.setStrokeColor(AMBER);c.setDash(2,3);c.line(x(570),24,x(570),372);c.setDash()
        for i,(a,b) in enumerate(zip(B['results'],F['results'])):
            y=362-i*17.2
            if i%4==0:
                c.setStrokeColor(colors.HexColor('#BACDD4'));c.line(0,y+9,WIDTH,y+9)
            c.setFont('KR',8.5);c.setFillColor(NAVY);c.drawString(0,y-3,a['zone']+'  '+a['origin'])
            c.setStrokeColor(TEAL);c.setLineWidth(2);c.line(x(a['arrival']),y,x(b['arrival']),y)
            c.setFillColor(NAVY);c.circle(x(a['arrival']),y,3.2,fill=1,stroke=0)
            if a['arrival']!=b['arrival']:
                c.setFillColor(TEAL);c.circle(x(b['arrival']),y,3.2,fill=1,stroke=0);c.setFont('KR',8);c.drawString(x(b['arrival'])+7,y+4,'93분 앞당김')

class SpatialPlot(Flowable):
    def __init__(self):super().__init__();self.width=WIDTH;self.height=265
    def draw(self):
        c=self.canv;xs=[r['longitude'] for r in S];ys=[r['latitude'] for r in S];xlo,xhi=min(xs)-.01,max(xs)+.01;ylo,yhi=min(ys)-.005,max(ys)+.005
        def coord(r):return (35+(r['longitude']-xlo)/(xhi-xlo)*420,20+(r['latitude']-ylo)/(yhi-ylo)*225)
        palette={'혁신':TEAL,'서부':colors.HexColor('#6685B0'),'북부':AMBER,'동부':colors.HexColor('#A873A8'),'남부':NAVY}
        for i,r in enumerate(S):
            x,y=coord(r);c.setFillColor(palette[r['zone']]);c.circle(x,y,4,stroke=0,fill=1);c.setFont('KR',8);c.drawString(x+5,y+4,str(i+1))
        c.setFillColor(GRAY);c.setFont('KR',8);c.drawString(12,248,'북 ↑');c.drawString(20,0,'축척 없는 경·위도 배치도 / 행정경계 생략 / 숫자는 표본 번호')

class CostPlot(Flowable):
    def __init__(self):super().__init__();self.width=WIDTH;self.height=180
    def draw(self):
        c=self.canv;lx=45;by=25;w=425;h=130
        for v in [0,40000,80000,120000,160000]:
            y=by+v/160000*h;c.setStrokeColor(colors.HexColor('#DFE7EB'));c.line(lx,y,lx+w,y);c.setFont('KR',7.5);c.setFillColor(GRAY);c.drawRightString(lx-6,y-3,str(v//10000)+'만')
        for n in [0,4,8,12,16,20]:
            x=lx+n/20*w;c.drawCentredString(x,9,str(n)+'명')
        for rate,color,label in [(5000,TEAL,'1대당 5,000원'),(8000,AMBER,'1대당 8,000원 가정')]:
            c.setStrokeColor(color);c.setLineWidth(2);c.line(lx,by,lx+w,by+20*rate/160000*h);c.setFillColor(color);c.drawRightString(lx+w,by+20*rate/160000*h+5,label)
        c.setFont('KR',8);c.setFillColor(GRAY);c.drawString(lx,166,'개별 택시 지원보다 비싸지 않은 고정편 총 견적 상한 (동일 본인부담 기준)')

def footer(c,doc):
    c.setFillColor(TEAL);c.rect(0,834,595.276,8,fill=1,stroke=0);c.setStrokeColor(colors.HexColor('#D2E0E6'));c.line(44,45,551,45)
    c.setFont('KR',7.6);c.setFillColor(GRAY);c.drawString(44,30,'2026.10.08 | 공개자료 기반 조건부 분석 | 현장 실측·신규 수요예측 아님');c.drawRightString(551,30,str(doc.page))
def build(name,title):
    path=ROOT/'output/pdf'/name
    doc=SimpleDocTemplate(str(path),pagesize=(595.276,841.89),leftMargin=44,rightMargin=44,topMargin=41,bottomMargin=59,title=title,author='교통 데이터 분석 / Codex 협업')
    doc.build(story,onFirstPage=footer,onLaterPages=footer);print(path)

head('01','첫차의 연결이\n서울 도착 기회를 바꾼다'.replace('\n','<br/>'),'문제 정의와 핵심 결과')
add('진주 5개 생활권 20개 주거지 표본의 버스·철도 연계 분석',sub)
add('같은 목적지인 강남역까지, 어느 주거지에서 더 일찍 도착할 수 있는가? 새로운 장거리 노선보다 먼저, 집 근처 정류장과 이미 운행 중인 첫 장거리편 사이의 연결을 점검했다. 핵심 대상은 혁신도시 LH10단지와 풀에버정문이다.')
callout('LH10·풀에버의 후보 경로 도착시각<br/><font size="21" color="#008C88">11:00 → 09:27</font>  /  93분 앞당김<br/>04:45 풀에버 출발 연계편을 추가하면 05:30 서울행에 연결된다. 시내·서울 환승 보행과 승차 여유를 둔 시간표 기반 결과다. [1-4,6]')
table(['핵심 발견','제안에 주는 의미'],[
('같은 혁신도시도 결과가 다르다','센텀·LH3/LH5는 승차장까지 걸어갈 수 있다. ‘신도시 전체 불이익’으로 일반화하지 않는다.'),
('93분은 이동시간 절약이 아니다','두 상세 사례는 100분 일찍 출발해 93분 일찍 도착한다. 기본 가정에서 여정은 7분 늘어난다.'),
('20개 표본으로 비교 범위를 확대','혁신·서부·북부·동부·남부 각 4곳. 09:30 이전 도착 가능 표본은 6곳에서 8곳으로 증가한다.'),
('신규 수요가 적을 가능성도 고려','실제 승차 통계와 예약 인원별 비용 기준으로, 개별 이동 지원과 짧은 연계편을 비교한다.')
],[142,365])
add('데이터 결합과 계산 방법',sub)
add('BIS 노선·정류장 순서와 예상 통과시각에 TAGO 장거리 출발·도착을 연결했다. 04:00 이후 출발, 외부 보행20분 이내에서 ‘도착+승차 여유≤다음 출발’인 경로만 남겼다. 서울 구간은 같은 열차번호의 승차·하차 시각을 맞춘 뒤, 후보별 최종 도착시각을 비교한다.',small)
add('분석의 단위와 주장 범위',sub)
add('주 분석은 대표 정류장 20곳의 탐색적 비교이며 인구 대표 표본이 아니다. 2026년 10월 8일 평일 시간표와 공개 예상시간에서 열거한 경로 중 가장 이른 결과를 찾았다. 두 핵심 사례는 아파트 지도 지점·정문부터의 접근 보행을 별도로 검토했다. 목적지 도착은 강남역 2호선 하차 후 지상 이동 3분을 가정한다. 실제 도착·이용수요를 관측한 결과는 아니다.',small)
page()

head('02','서부 네 곳을 넘어, 20곳 비교','분석 내용 및 결과')
story.append(ArrivalPlot())
add('남색 점: 기존 / 청록 점: 04:45 연계편 추가 / 점선: 09:30. 그래프의 시간은 공개 시간표와 보행 가정으로 계산한 값이며 지연을 포함한 실측값이 아니다. [1-4,6]',small)
add('표본을 넓혀도 핵심 연결 공백은 남았다',sub)
add('기존 비교는 서부 네 곳이 모두 251번에 의존했다. 이번에는 결과 계산 전에 생활권별 네 곳을 선정해 다른 노선과 터미널 보행 대안을 포함했다. 남부의 세 표본은 개양 승차장까지 도보 8·10·16분, 금호석류 표본은 고속터미널까지 도보 14분으로 계산됐다. 같은 혁신도시 안에서도 걸어서 05:30편을 탈 수 있는 곳과 그렇지 않은 곳이 갈린다.')
add('도보 접근 한도는 외부 보행 합계 20분이며 승강장 접근은 별도 가정이다. 모든 버스 환승을 완전 탐색한 결과가 아니므로 ‘지역별 절대 최단시간’이나 신도시 개발의 인과효과로 해석하지 않는다. 개양 출발편을 제외해도 LH10·풀에버의 기존 11:00 결과는 유지된다.',small)
page()

head('03','연결되는 시간표, 달라지는 여정','검증과 개선안')
add('운행 제안: 04:45 풀에버 → 04:51 LH10 → 05:00 혁신 승차장',sub)
add('승객 운송 구간은 기존 150번 경로의 약 3.066km. BIS 구간 예상시간 11분과 경로검색 약 13.4분을 참고해 15분을 계획했다. 주행 18분·승차장 이동 10분·장거리 승차 여유 15분을 적용해도 05:28에 연결 조건을 만족한다. 앞선 04:50안은 이 조건에서 3분 부족해 5분 앞당겼다. [1]')
table(['구간','기존 핵심 경로','추가 연계 경로'],[
('장거리 승차','혁신 07:00 → 서울경부 10:35','혁신 05:30 → 서울경부 09:05'),
('서울 도시철도','3호선 10:45:30 → 교대\n2호선 10:55:30 → 강남 10:57','3호선 09:15:30 → 교대\n2호선 09:22:30 → 강남 09:24'),
('지상 도착 가정','11:00','09:27')
],[104,201,202])
add('서울 경부터미널 하차→3호선 승강장 8분, 교대 환승 4분, 승차 여유 30초, 강남 지상 이동 3분은 계획 가정이다. 열차 출발·도착은 2026.09.01 적용 공식 CSV의 같은 열차번호를 연결했다. 지도 소요시간 단순 덧셈을 대체했다. [4]',small)
table(['상세 출발점','기존 출발 → 도착 / 여정','추가편 출발 → 도착 / 여정'],[
('LH10 아파트 지도 지점','06:23 → 11:00 / 277분','04:43 → 09:27 / 284분'),
('풀에버 아파트 정문','06:21 → 11:00 / 279분','04:41 → 09:27 / 286분')
],[144,181,182])
add('기존 300번 후속편의 예상 통과시각을 사용한 직통 후보 비교다. 승차 방향은 LH10 49007, 풀에버 49035로 맞췄고 보행은 각각 6분·2분이다. 300번 공식 안내의 중간 통과 ±5~7분 변동을 고려해 7분 일찍 나가면 기존 여정도 7분 늘어, 양안의 여정 차이는 0분이 된다. 도착 기회를 93분의 시간절약 편익으로 환산하지 않는다. [1,6]',small)
table(['추가 운행 대안','두 핵심 표본 강남 도착','판단'],[
('단거리 연계편 04:45','09:27','수요·견적에 따라 예약 운행'),
('150번 04:40편 추가','09:27','기존 05:30 유지, 편도 노선 19km'),
('150-1번 05:05편 추가','10:39','06:10 KTX→서울역 경유, 21분 앞당김')
],[160,141,206],True)
add('광명 도착만 빠르다고 최종 도착이 빠르지는 않다. 09:33 하차 후 이동 10분이면 09:39 셔틀을 놓쳐 10:05편을 타게 된다. 서울역 경유가 이 후보 집합에서 더 빠르다. [3-5]',small)
page()

head('04','실제 승차 통계에서 운영 기준으로','수요와 비용 비교')
add('진주시 ITS의 2026년 9월 공개 승차 집계 [7]',sub)
table(['노선','월 승차 건수','05시대 건수','05시대 일평균'],[[r['route'],f"{r['monthly_boardings']:,}",str(r['hour05']),f"{r['hour05']/30:.1f}"] for r in D['demand']['routes']],[88,140,135,144])
add('150번 05시대 176건은 하루 평균 5.9건이다. 그러나 노선 전체의 기존 승차이며 신규 04:45 연계편 수요도, 서울행 승객 수도 아니다. 시간대·일별·노선별 월 합계를 대조했다. 04시대 0건도 그 시간에 서비스가 없으면 잠재수요 0의 근거가 되지 않는다.',small)
add('‘하루 몇 명’ 예측 대신, 예약 인원에 따른 전환 기준',sub)
story.append(CostPlot())
add('지도 택시 참고액은 LH10→혁신 승차장 4,600원, 풀에버 정문→승차장 5,000원. 새벽 호출·예약료와 배차 가능 여부는 미확정이다. 그림의 8,000원은 추가비용을 고려한 가정이며 실제 견적이 아니다. 1인 1대·합승 없음 기준이다. 비교는 지역 접근 구간 비용이며 같은 서울행 이후 운임은 제외한다. [6]',small)
callout('예: 6명이 확정 예약하고 택시 총액이 1대당 5,000원이라면,<br/>고정 연계편의 모든 비용을 포함한 견적이 <font color="#008C88">30,000원 이하</font>여야 개별 택시보다 저렴하다. 견적 60,000원을 가정하면 12명부터 동률이다. 이는 수요 예측이나 실제 운송원가가 아니다.')
add('권고: 예약 인원과 실제 견적을 받은 뒤 수단을 선택',sub)
add('05:30 장거리편 이용이 확인된 예약자를 대상으로 동일 목적지 도착 조건을 맞춘다. 소수이면 개별 사전예약 이동 지원, 예약이 모이면 좌석 수와 회송을 포함한 연계편 견적을 비교한다. 두 방식에 같은 본인부담 1,650원을 적용하면 비용 비교에서 본인부담은 상쇄된다. 운전자 유급시간·출고·회송·배차·보험을 뺀 비용으로 판단하지 않는다. 기존 첫 운행을 빼앗는 조정은 제안하지 않는다. [8]')
page()

head('05','조건을 바꿔도 정직한 결론','민감도·실행 기준·AI 활용')
table(['변경 조건','계산 결과 / 해석'],[
('주행18분 + 승강장10분 + 승차여유15분','04:45 출발이면 05:28. 여유 2분. 주행22.5분이면 05:32:30으로 놓침 → 같은 여유를 유지하려면 04:40 출발 검토.'),
('서울 도착 지연 또는 접근보행 증가','정시·기본 보행은 09:27. 서울 경부 도착이 5분 늦으면 09:33. ‘09:30 도착 보장’으로 주장할 수 없음.'),
('걷기 허용범위 확대','LH10 지도 지점에서 28분, 풀에버 정문에서 31분을 걸으면 기존 05:30편 접근이 가능. 그 경우 도착 앞당김보다 보행 부담 완화가 편익.'),
('미확정 시외버스 시간표 추가','날짜가 없는 서울남부행을 보조로 넣으면 서부 표본이 10:08→09:55. LH10·풀에버의 11:00은 유지.'),
('개양 출발편 제외','남부 세 표본의 결과는 달라지지만 두 핵심 표본의 연결 공백과 개선 결과는 유지.')
],[153,354],True)
table(['도착 기한','기존 가능 표본','연계편 추가'],[[r['deadline'],f"{r['baseline']} / 20",f"{r['feeder']} / 20"] for r in D['deadlines'][:4]],[171,168,168],True)
add('이 수치는 주민 비율이나 실제 도착 성공률이 아니다. 특히 09:00 기회는 개선하지 못한다. 09:30은 정시 조건에 민감해 시범운영에서는 10:00 이전 도착과 장거리 환승 성공도 함께 평가한다.',small)
add('운영기관이 확인할 시범운행 기준',sub)
add('4주 평일 시범을 제안한다. 장거리 출발 15분 전 승차장 도착, 예약 대비 실제 탑승, 놓친 연결, 1인당 순지원액, 기존 첫차 유지 여부를 운행·예약 기록으로 집계한다. 목표는 승차장 15분 전 도착 95% 이상으로 제안하되, 현 분석이 달성률을 입증한 것은 아니다. 비용은 같은 인원의 사전예약 택시 대안과 매주 비교하고, 지연 또는 좌석 부족 시 운영조건을 수정한다.',small)
add('공개자료 분석의 한계와 재현성',sub)
add('보행은 지도 추정, 시내버스 통과는 BIS 예상시간이다. 50개 노선·방향의 첫차 요약/상세 불일치와 현재 노선에 대응되지 않은 추천 경로는 제외했다. 미확인 경로 때문에 더 이른 대안이 남을 수 있다. 시외버스 API 빈 응답은 무운행으로 처리하지 않았다. 주말 전체 연결·실제 새벽 배차·운송원가는 입증하지 않았다. 직접 현장 조사 없이 이 한계를 공개한다.',small)
add('AI 활용',sub)
add('ChatGPT/Codex로 공식 자료 탐색, API·표 수집, Python 경로 계산, 오류 검사, 민감도 분석과 보고서 작성을 수행했다. 핵심 요청: ‘같은 서울 목적지 도착과 첫 운행 조정 효과’, ‘기차 포함’, ‘네 가지 보강’, ‘직접 조사 없이 공개자료 중심’. 열차번호·시간순서·집계합·비용 식 등 292개 검사를 통과했다. 예측모델 학습·실제 수요 생성·현장 실측은 하지 않았다.',small)
page()

head('06','자료 출처와 재현','참고문헌 / 본문 5쪽 외')
sources=[
('[1] 진주시 BIS','노선·정류장·시간표(2026.08.18 적용 PDF), 예상 소요시간, 환승검색','https://bis.jinju.go.kr/addInfo/addInfoTimeTable.do'),
('[2] 국토교통부 TAGO 고속버스정보','진주·개양·혁신→서울경부, 2026.10.08 API 조회 원문','https://www.data.go.kr/data/15098522/openapi.do'),
('[3] 국토교통부 TAGO 열차정보','진주 출발 서울·광명·수서 등 열차 시각/번호, 2026.10.08','https://www.data.go.kr/data/15098552/openapi.do'),
('[4] 서울교통공사 열차운행 시각표','2026.09.01 적용 CSV. 요일·노선·방향·열차번호로 환승 계산','https://www.data.go.kr/data/15098251/fileData.do'),
('[5] 한국철도공사 열차시각표','KTX 10/1, 광명셔틀 9/1, 수인분당선 8/22 적용 공식표','https://www.korail.com/com/userBoard.do?mode=list&amp;schBcid=ticketTable'),
('[6] 카카오맵','2026.10.08 공개 화면. 실제 보행 경로, 승차 방향, 택시 예상액 기록','https://map.kakao.com/'),
('[7] 진주시 ITS 교통통계','2026.09.01~09.30 노선·시간대·일별·행정동 승차 집계','https://its.jinju.go.kr/its/stt/view'),
('[8] 진주시 시내버스 요금','성인 교통카드 1,650원: 정책 비교의 공통 본인부담 가정에 사용','https://bis.jinju.go.kr/addInfo/addInfoCharge.do'),
('[9] KOBUS / 진주시외버스터미널','개양→서울경부 10/13 첫차04:40·소요215분 보조 대조 / 남부행 게시표','https://www.kobus.co.kr/oprninf/alcninqr/oprnAlcnPage.do'),
('[10] TAGO 시외버스정보','조사 구간 빈 응답을 자료 공백으로 처리. 터미널 게시표는 적용일 미확인','https://www.data.go.kr/data/15098541/openapi.do'),
('[11] 숲과나눔 공모전 안내','보고서 형식·정책 제안·데이터 출처·AI 활용 내역 확인','https://koreashe.org/notice/?mod=document&amp;uid=95427')]
for label,desc,url in sources:
    add(label+' / '+desc,small);add('<link href="'+url+'" color="#008C88">'+url+'</link>',mini)
add('시외터미널 보조 출처: <link href="http://jinjuterminal.kr/index.php?mid=sub_2_1" color="#008C88">http://jinjuterminal.kr/index.php?mid=sub_2_1</link>',mini)
add('재현: RUN_ANALYSIS.txt 및 analysis/analyze_strengthened.py, metro_connections.py, check_strengthened.py. 원문·정제·결과·메타데이터와 SHA-256 목록을 함께 보관한다. API 키는 결과/배포 묶음에 포함하지 않는다. 코드 공개 링크 발행과 출품 접수는 수행하지 않았다.',small)
build('jinju_first_connection_analysis.pdf','첫차의 연결이 서울 도착 기회를 바꾼다')

# Evidence appendix, intentionally separate from the five-page submission body.
story=[]
head('A1','20개 표본의 선택과 결과','공개자료 검증 부록')
add('결과를 계산하기 전에 각 생활권에서 네 곳을 선택했다. 생활권 명칭은 분석용 지리 구분이며 행정동 경계가 아니다. 기존 혁신·서부 8곳에 북부·동부·남부 12곳을 추가한 목적표본이다. 모집단 대표성·표본오차를 주장하지 않는다.',small)
rows=[]
for i,r in enumerate(B['results']):
    rows.append([str(i+1),r['zone'],r['origin_id']+' '+r['origin'],r['arrival_hhmm'],F['results'][i]['arrival_hhmm'],' + '.join(r['city_path']['routes'])])
table(['번호','권역','대표 정류장 ID / 이름','기존','개선','기존 시내 접근'],rows,[29,33,169,49,49,178],True)
add('20개 표본의 좌표·선정 규칙은 sample_selection.json, 각 결과의 원문 파일·시내 경로·도시철도 열차번호는 analysis.json에 보관한다. 동일 이름의 정류장도 진행방향에 따라 ID가 다르다. 개별 아파트 내부 출발은 이 표의 모집단이 아니다.',small)
add('강남 도착시각은 초 단위 계산 결과를 분 단위로 올림 표시했다. 예를 들어 10:07:30은 10:08이다. 도착 기한 판정은 올림 이전 값을 사용한다. 각 결과는 열거한 경로 안의 최솟값이다.',small)
page()
head('A2','지리와 보행을 함께 점검','출발점·승차 방향·보행 근거')
story.append(SpatialPlot())
table(['출발 지점','도착 / 방향','보행 계산값'],[
('LH10 아파트 지도 POI','49007 / LH8·LH9 방면','6분 / 364m'),
('풀에버 아파트 정문','49035 / 부영11·중흥12 방면','2분 / 104m'),
('LH10 아파트 지도 POI','혁신 장거리 승차장','28분 / 1.8km'),
('풀에버 아파트 정문','혁신 장거리 승차장','31분 / 2.0km'),
]+[[r['start'],r['destination'],f"{r['minutes']}분 / {r['meters']}m"] for r in M['additional_walks']],[216,174,117],True)
add('카카오맵 2026.10.08, 성인 보행 4km/h, 최단거리 옵션. LH10은 정문이 확인된 것이 아니라 아파트 지도 지점이다. 출입구·횡단 대기·야간 통행환경은 실측하지 않았다. 짧은 정류장 연결은 직선거리×1.3/4km/h 추정이며, 표의 경로검색 보행과 구별한다.',small)
add('외부 보행 20분 후보는 지도 확인된 추가 보행과 기존 혁신 보행을 포함한다. 모든 30·40분 권역까지 걸을 수 있는 완전 보행망을 만든 것은 아니다. 28·31분 민감도는 두 핵심 아파트 지점에 한정한다.',small)
page()
head('A3','승차 연결을 검산할 수 있는 기록','시간표·예상시간·가정의 구분')
table(['증거 수준','실제로 확보한 것','확보하지 않은 것'],[
('공식 운행계획','TAGO 기준일 시간표, BIS 기점 출발, 공식 도시철도 CSV, KTX204 06:10→서울09:52 매일운행','당일 GPS 실제 통과·지연·결행'),
('공식 예상값','BIS 구간 통과시간, 터미널 공시 소요시간','확률분포·95백분위 지연'),
('지도 계산값','보행 동선/분/거리, 택시 참고액','현관부터 실측, 실제 예약 견적'),
('명시적 계획 가정','지역 승차여유2분, 승강장5분, 장거리여유10분, 서울 접근·환승·지상 이동','이 값으로 보장된 운행 성공률')
],[84,232,191],True)
add('핵심 시간순 연결',sub)
table(['단계','기본 계산','지연에 대한 검토'],[
('풀에버 연계편','04:45 출발, LH10 04:51','주행15→18분; LH10 통과는 계획시각'),
('혁신 승차장','05:00 하차 +5분 이동 =05:05','18분 주행+10분 이동이면05:13'),
('장거리 승차','05:30 출발, 여유10분 외15분 잔여','위 보수조건 +15분 여유 =05:28'),
('서울경부 도착','09:05 예정 / 접근8분','09:13 승강장 준비'),
('3호선 3087','09:15:30→09:17:30 교대','환승4분, 승차여유30초'),
('2호선 2117','09:22:30→09:24 강남','지상 이동3분 →09:27')
],[115,195,197],True)
add('철도 대안의 마지막 연결',sub)
table(['장거리 하차','도시철도 첫 승차 / 연결','강남 지상 도착'],[
('서울 09:52 / KTX204','4호선10:05:30→사당→2호선','10:39'),
('광명 09:33 / KTX204','09:39 셔틀 놓침→10:05→신도림→2호선','11:00'),
('수서 10:41 / 열차382','수인분당10:58:30→선릉→2호선','11:25')
],[154,257,96],True)
add('KTX 공식표의 광명09:34:30은 TAGO 도착09:33과 기록 기준(중간역 출발 등)이 다를 수 있어 충돌로 단정하지 않았다. 서울 도착09:52·진주 출발06:10은 일치한다. 광명 두 값 모두 접근10분 조건에서09:39 셔틀을 놓친다. 같은 KTX204의 두 하차 대안을 독립 열차로 세지 않는다.',small)
add('범위: 진주 지역 직접·BIS 추천 1회 환승 및 지정 보행, 서울의 명시한 철도 경로. 서울 버스·추가 환승·모든 경로의 전역 최적해는 아니다. 주말 철도표를 보유했어도 진주 시내·장거리 주말 전체 연결은 검증하지 않았다.',small)
page()
head('A4','지연과 비용의 경계조건','성공률을 만들지 않는 민감도')
add('장거리 승차장 이동 10분, 승차 여유 15분일 때',sub)
table(['풀에버 출발','구간15분','구간18분','구간22.5분'],[[hhmm(start)]+[(('가능 / '+str(round(330-start-runtime-25,1))+'분 여유') if start+runtime+25<=330 else ('불가 / '+str(round(start+runtime+25-330,1))+'분 부족')) for runtime in [15,18,22.5]] for start in [280,285,290]],[105,134,134,134],True)
add('04:45는 20% 주행 증가를 포함한 조건에 맞춘 제안이다. 구간22.5분·승강장10분까지 대비하려면 04:40이 필요하다. 계산 조합의 통과 비율을 실제 성공확률로 표현하지 않는다.',small)
table(['서울경부 도착 지연','접근 기본8분','접근+5분','접근+10분'],[[str(delay)+'분']+[hhmm(next(r['arrival'] for r in D['arrival_delay_grid'] if r['coach_delay']==delay and r['entry_extra']==extra)) for extra in [0,5,10]] for delay in [0,5,10,20,30]],[141,122,122,122],True)
add('서울 환승 중 교대 보행4분은 위 표에서 고정했다. 접근만 늘린 조건이며 모든 보행 지연의 최악상황은 아니다. 정시 09:27이 09:30 ‘보장’이 될 수 없다는 점을 보여준다.',small)
add('고정 운행 비용이 개별 택시 이하가 되는 최소 인원',sub)
table(['총 견적 Q (가정)','택시4,600원','택시5,000원','택시8,000원'],[[f'{q:,}원']+[str(next(r['riders_at_equality'] for r in D['cost']['thresholds'] if r['all_in_quote']==q and r['taxi_unit']==t))+'명' for t in [4600,5000,8000]] for q in [30000,60000,90000,120000]],[141,122,122,122],True)
add('계산식: 고정편 순지원액=max(0,Q-1,650N), 개별지원=N×max(0,T-1,650). 동일 이용 인원과 본인부담이고 Q≥1,650N이면 Q≤N×T에서 고정편이 더 저렴하다. 좌석 수를 넘으면 더 큰 차량 또는 여러 편의 총 견적으로 다시 계산한다. 표는 실제 견적·예약인원·배차 가능성을 뜻하지 않는다.',small)
add('운행 방식별 확보할 입력값',sub)
add('단거리편: 유급 운전자 시간, 차고지 출고/회송, 승객 운송15~22.5분, 차량비, 배차·보험, 좌석. 150 추가편: 편도19km 외 전체 차량 회차와 기존편 보호. 개별지원: 새벽 배차 확약, 호출·예약료 포함 총액, 지연 대체 조건. 승객이 모이지 않으면 무조건 증편하지 않고 동일 도착 조건의 대안을 선택한다.',small)
page()
head('A5','집계 검증과 실행 가능한 후속 기준','공개자료 중심의 수요 판단')
add('공식 통계 합계 대조',sub)
table(['9월 집계 기준','승차 건수','해석'],[
('시간대 합계',f"{D['demand']['totals']['hourly']:,}",'일별·노선별 합계와 일치'),
('일별 합계',f"{D['demand']['totals']['daily']:,}",'30일 합계'),
('노선별 합계',f"{D['demand']['totals']['routes']:,}",'전체 노선'),
('행정동별 합계',f"{D['demand']['totals']['admin']:,}",'노선 합계보다3,697건 적음; 원인 미확인'),
('충무공동', '128,796','전체 시간·노선의 승차 건수; 서울행 수요 아님')
],[147,113,247],True)
add('시 전체 합계의 약0.186%가 행정동 집계와 차이 난다. 미분류라고 추정해 특정 동에 임의 배분하지 않았다. 150·150-1·300·251은 시간대·일별·노선별 합계가 모두 일치하고 30일 중0일은 없다. 10월7일 전노선 일별0은 미집계 가능성이 있어 최근 7일의 평균을 수요 근거로 채택하지 않았다.',small)
add('분석으로 말할 수 있는 것 / 없는 것',sub)
add('05시대 실제 이용이 있는 관련 노선을 확인했다. 그러나 두 아파트에서05:30 서울행을 탈 예약 인원은 알 수 없다. 통계 단위도 고유 인원이 아닌 승차 건수다. 따라서 신도시 주민 수×이용률, 전 노선 승차×임의전환율, 예상 이용자×93분 등의 편익 산정은 하지 않았다.',small)
table(['시범운영 지표','정의','판단 기준 (제안)'],[
('환승 준비','승차장 도착≤장거리출발-15분','4주 평일95% 이상 목표; 실적 미확보'),
('기회 실현','예약자의 실제05:30 장거리 탑승','연계 실패 원인·대체편 제공 기록'),
('비용','(총액-총 본인부담) / 실제 탑승인원','같은 인원의 예약택시 순지원액과 비교'),
('예약 신뢰','예약 대비 탑승 / 취소 / 미탑승','공석·노쇼를 반영해 발차 기준 수정'),
('기존 이용자','기존 첫차·후속편 운행 유지','기존편 감편이나 전용을 효과로 포장하지 않음')
],[82,207,218],True)
add('이 조사와 운행은 본 분석에서 실시하지 않았다. 향후 지자체·운송기관의 예약·운행 기록으로 판단할 제안이며, 사용자의 직접 현장 조사를 전제로 하지 않는다. 실제 견적·승객 예약이 없는 상태에서는 최적 대수, 실제 지원예산, 비용편익비를 확정할 수 없다.',small)
page()
head('A6','다시 계산할 수 있게 남긴 것','분석 절차·품질 점검·제출 준비')
table(['단계','파일 / 역할'],[
('표본·노선 수집','collect_expanded_samples.py / 20개 표본, 직접848·추천1,799개 후보'),
('공식 통계 수집','collect_public_demand.py / 익명 공개 ITS 조회·월 집계'),
('철도표 정리','prepare_korail_transfers.py / 수인분당선 시각과 KTX 대조 셀'),
('서울 시간순 연결','metro_connections.py / 날짜분류·노선·방향·열차번호 연결'),
('전체 계산','analyze_strengthened.py /20개 결과·출발/여정·민감도·수요/비용'),
('논리 검증','check_strengthened.py /292개 검사, 결측·순서·집계·비용 식'),
('출판','build_strengthened_report.py / 본문5쪽+참고문헌, 검증부록'),
('입력과 결과','data/raw/strengthening/, outputs/strengthened/, RUN_ANALYSIS.txt')
],[123,384],True)
add('후보 수와 데이터 공백',sub)
add('직접848개·노선에 대응된 추천1,799개를 확보했다. 추천 경로 중 대응되지 않은471개는 원문과 구분해 제외했다. 계산에서 유효한 접근 후보는1,942개이고, 시간 불일치/누락 등 제외 건수는252개다. 제외 건수는 처리 경로의 합으로 고유 노선 수와 다르다. 전체 시간표 요약·상세 대조에서50개 노선·방향 불일치가 남아 해당 방향을 사용하지 않았다.',small)
add('재현 범위',sub)
add('캐시 계산은 인증키 없이 가능하다. 새로운 날짜 API 수집만 .env의 키를 사용한다. 원문 캐시와 정제 결과의 SHA-256 목록을 생성했다. 데이터 묶음에 인증키·쿠키·CSRF 토큰을 넣지 않았다. 저장 원문의 기관 이용조건을 따라야 하며 로컬 재현 묶음은 외부 게시가 아니다.',small)
add('AI 작업의 추적과 사람의 최종 판단',sub)
add('사용자 요청을 분석 질문으로 정리하고 공개자료를 수집·계산했다. 반례 점검은 보행 대안, 도착 기회와 여정의 구분, 광명 셔틀 대기, 공식 집계 불일치, 신규수요 미확인, 견적 전환 기준에 집중했다. 검사 통과는 계산의 내부 일관성을 뜻하며 현실의 운행 성공이나 수상 가능성을 보증하지 않는다.',small)
add('남은 행정 절차',sub)
add('참가자·팀 정보를 공모전 접수 양식에 기입하고, 제출 직전 기준일 시간표를 갱신한다. 실제 출품 접수와 코드 공개 링크 발행은 수행하지 않았다. 공개 링크가 필요한 단계에서는 키를 제외한 재현 자료의 공개 범위를 정해야 한다. 분석상의 공개자료 한계는 본문에 이미 명시했으며 현장 조사 자료가 있는 것처럼 채우지 않는다.',small)
add('출처: 본 보고서 참고문헌 [1]-[11]과 원문 메타데이터. 이 부록은 본문5쪽 제한을 보완하기 위한 별도 검증 자료다.',small)
build('jinju_first_connection_evidence.pdf','첫차 연결 분석: 검증과 운영 의사결정 부록')
