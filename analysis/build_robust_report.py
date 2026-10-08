"""Five body pages plus references; complete separate evidence appendix (v3)."""
import json
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,Flowable
from analyze_connections import ROOT,hhmm
D=json.loads((ROOT/'outputs/robust/analysis.json').read_text())
V=json.loads((ROOT/'outputs/robust/validation.json').read_text())
A=D['alias_audit'];H=D['housing'];WIDTH=507
IDENTITY=json.loads((ROOT/'submission/identity.json').read_text()) if (ROOT/'submission/identity.json').exists() else {}

def scenario(date='2026-10-08',target='강남',mode='matched',policy='baseline'):
    return next(e for e in D['experiments'] if all(e['parameters'][k]==v for k,v in [('date',date),('target',target),('branch_mode',mode),('policy',policy)]))
B=scenario();F=scenario(policy='feeder')
FONT=Path('/System/Library/Fonts/Supplemental/AppleGothic.ttf')
# Set KR_FONT to a redistributable installed Korean TTF on other systems.
import os
FONT=Path(os.environ.get('KR_FONT',str(FONT)))
pdfmetrics.registerFont(TTFont('KR',str(FONT)));pdfmetrics.registerFontFamily('KR',normal='KR',bold='KR',italic='KR',boldItalic='KR')
NAVY=colors.HexColor('#163547');TEAL=colors.HexColor('#008C88');GRAY=colors.HexColor('#526B79');LIGHT=colors.HexColor('#EDF5F5');AMBER=colors.HexColor('#B56036');PALE=colors.HexColor('#F7F9FB')
body=ParagraphStyle('body',fontName='KR',fontSize=9.6,leading=14.7,textColor=NAVY,wordWrap='CJK',spaceAfter=8)
small=ParagraphStyle('small',parent=body,fontSize=8.1,leading=12.0,textColor=GRAY,spaceAfter=6)
mini=ParagraphStyle('mini',parent=small,fontSize=7.4,leading=10.2,spaceAfter=2)
large=ParagraphStyle('large',parent=body,fontSize=22,leading=29,spaceAfter=11)
sub=ParagraphStyle('sub',parent=body,fontSize=12.2,leading=17,textColor=TEAL,spaceBefore=6,spaceAfter=7)
story=[]
def p(t,s=body):return Paragraph(str(t).replace('\n','<br/>'),s)
def add(t,s=body):story.append(p(t,s))
def head(k,title,kicker):add(f'{k} / {kicker}',small);add(title,large)
def page():story.append(PageBreak())
def table(headers,rows,widths=None,compact=False):
    st=mini if compact else small
    t=Table([[p(x,st) for x in headers]]+[[p(x,st) for x in row] for row in rows],colWidths=widths or [WIDTH/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),4 if compact else 6),('BOTTOMPADDING',(0,0),(-1,-1),3 if compact else 5),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE])]))
    story.extend([t,Spacer(1,7)])
def callout(text):
    t=Table([[p(text)]],colWidths=[WIDTH]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.5,TEAL),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.extend([t,Spacer(1,8)])
class ArrivalPlot(Flowable):
    def __init__(self):super().__init__();self.width=WIDTH;self.height=367
    def draw(self):
        c=self.canv;left=169;scale=318/165
        def x(t):return left+(t-510)*scale
        for t in [510,540,570,600,630,660]:
            c.setStrokeColor(colors.HexColor('#DDE6EB'));c.setLineWidth(.5);c.line(x(t),24,x(t),351);c.setFillColor(GRAY);c.setFont('KR',8);c.drawCentredString(x(t),8,hhmm(t))
        c.setStrokeColor(AMBER);c.setDash(2,3);c.line(x(570),24,x(570),351);c.setDash()
        for i,(a,b) in enumerate(zip(B['results'],F['results'])):
            y=342-i*16.4
            c.setFont('KR',8.4);c.setFillColor(NAVY);c.drawString(0,y-3,a['zone']+'  '+a['origin'])
            c.setStrokeColor(TEAL);c.setLineWidth(2);c.line(x(a['arrival']),y,x(b['arrival']),y)
            c.setFillColor(NAVY);c.circle(x(a['arrival']),y,3,fill=1,stroke=0)
            if a['arrival']!=b['arrival']:
                c.setFillColor(TEAL);c.circle(x(b['arrival']),y,3,fill=1,stroke=0);c.setFont('KR',7.8);c.drawString(x(b['arrival'])+7,y+4,'93분 앞당김')
class CostPlot(Flowable):
    def __init__(self):super().__init__();self.width=WIDTH;self.height=178
    def draw(self):
        c=self.canv;left=43;bottom=27;w=415;h=114
        c.setFont('KR',7.5);c.setFillColor(GRAY)
        for v in [0,30000,60000,90000,120000]:
            y=bottom+v/120000*h;c.setStrokeColor(colors.HexColor('#DFE7EB'));c.line(left,y,left+w,y);c.drawRightString(left-5,y-3,str(v//10000)+'만')
        for n in [0,4,8,12,16,20]:c.drawCentredString(left+n/20*w,9,str(n)+'명')
        for party,color,label in [(1,TEAL,'1명씩 독립 일행'),(2,AMBER,'2명씩 가족·기존 일행')]:
            values=[]
            for n in range(21):values.append(5000*((n+party-1)//party))
            c.setStrokeColor(color);c.setLineWidth(1.7)
            for n in range(20):
                x1=left+n/20*w;x2=left+(n+1)/20*w;y1=bottom+values[n]/120000*h;y2=bottom+values[n+1]/120000*h
                c.line(x1,y1,x2,y1);c.line(x2,y1,x2,y2)
            c.setFillColor(color);c.drawString(left+260,155 if party==1 else 144,label)
        # Reservation cost of a feeder, Q=60k and 12 seats.
        c.setStrokeColor(NAVY);c.setDash(3,2);y=bottom+60000/120000*h;c.line(left+1/20*w,y,left+12/20*w,y);c.line(left+12/20*w,y,left+12/20*w,bottom+h);c.line(left+12/20*w,bottom+h,left+w,bottom+h);c.setDash()
        c.setFillColor(NAVY);c.drawString(left,165,'총비용 가정: 택시 5천원/대, 연계편 6만원/대·12석, 취소·불참 없음')
def footer(c,doc):
    c.setFillColor(TEAL);c.rect(0,834,595.276,8,fill=1,stroke=0);c.setStrokeColor(colors.HexColor('#D2E0E6'));c.line(44,45,551,45)
    c.setFont('KR',7.4);c.setFillColor(GRAY);c.drawString(44,30,'2026.10.08 | v3 공개자료 검증판 | 시간표 계산·운영 가정');c.drawRightString(551,30,str(doc.page))
def build(name,title):
    path=ROOT/'output/pdf'/name
    doc=SimpleDocTemplate(str(path),pagesize=(595.276,841.89),leftMargin=44,rightMargin=44,topMargin=40,bottomMargin=58,title=title,author=IDENTITY.get('participant','교통 데이터 분석 / Codex 협업'))
    doc.build(story,onFirstPage=footer,onLaterPages=footer);print(path)

def cost_rows():
    labels=['12명, 독립 12일행','12명, 2명씩 6일행','12명, 독립 일행·연계 8석','12명 예약→4명 사전 취소','12명 예약→4명 불참, 미사용 0%','12명 예약→4명 불참, 미사용 50%','12명, 2명씩 일행→4명 불참']
    return [[label,f"{r['actual']}명",f"{r['feeder_vehicles']}대 / {r['active_taxis']}대",f"{r['feeder_gross']/10000:g} / {r['taxi_gross']/10000:g}",f"{r['feeder_public']/10000:g} / {r['taxi_public']/10000:g}"] for label,r in zip(labels,D['cost']['examples'])]

head('01','첫차의 연결이\n서울 도착 기회를 바꾼다','주제 · 분석 배경 및 목적')
if IDENTITY.get('participant'):add('이름/팀명: '+escape(IDENTITY['participant'])+' / 개인 참가',small)
add('진주 5개 생활권 20개 대표 정류장 / 버스·철도 / 5개 날짜·3개 목적지',sub)
add('어느 주거지에서 서울의 같은 목적지에 더 일찍 도착할 수 있으며, 첫 운행을 어떻게 조정하면 그 차이가 줄어드는가? 장거리 첫차가 있어도 집 근처 버스가 승차장에 늦게 도착하면 그 첫차를 이용할 수 없다. 기존 장거리편에 연결하는 짧은 접근 서비스를 검토한다.')
callout('평일 두 핵심 표본의 강남역 지상 도착<br/><font size="22" color="#008C88">11:00 → 09:27</font> / 93분 앞당김<br/>첫 서울행 50분 전 출발하는 짧은 연계편을 추가한 공개 시간표 계산. 10/8·13·15 및 세 지선 배정 가정에서 같은 결과다. [1-6,9]')
add('보강 1. 지역 규모를 수요와 구분한다',sub)
table(['공식 공개자료 · 2026.07.01 기준','확인 규모','해석'],[
('한림풀에버 공동주택 현황','1,421호','관련 단지의 주택 수'),('혁신도시 NHF10단지 현황','404호','두 단지 합계 1,825호'),('충무공동 일반현황','33,698명 / 12,904세대','행정동 전체의 주민등록 규모')],[192,119,196])
add('1,825호는 실제 수혜 가구나 탑승 수요가 아니다. 두 대표 지점에서 연결 공백을 확인했지만 단지 내 모든 동·현관·출입구를 조사하지 않았다. 행정동 인구를 단지별로 배분하거나 평균 가구원수로 거주 인구를 만들어내지 않는다. [12,13]',small)
add('분석 대상과 기대 효과',sub)
add('혁신도시 LH10단지와 풀에버정문을 상세 사례로 삼고, 생활권별 4곳을 사전에 선정해 도보·다른 터미널·철도 대안을 비교했다. 기대 효과는 선택 가능한 도착시각의 확대다. 평일 105분 일찍 출발해 93분 일찍 도착하므로 여정은 12분 늘어난다. 수요·실제 배차·원가를 확인하기 전 시간 절약액이나 사업 편익으로 환산하지 않는다.')
page()
head('02','서부 네 곳을 넘어, 20곳 비교','활용 데이터 · 분석과정 및 방법')
story.append(ArrivalPlot())
add('10/8 평일 강남역 / 남색: 기존 / 청록: 04:40 연계편 추가 / 점선: 09:30. 결과는 경로 후보 내 계산값이며 실제 도착 기록이 아니다. 09:30 이전 가능 표본은 6곳→8곳으로 늘었다.',small)
table(['자료 [출처]','수집·전처리와 선정 이유'],[
('BIS 노선·시간표·예상시간 [1]','정류장 순서·방향·요일을 연결. 50개 기존 제외 방향의 첫차 복원, 추천 127개는 좌표·순서로 복원.'),
('TAGO·KOBUS·코레일 [2,3,5,9,10]','10/8 API + 4개 추가 날짜 공개 배차. 빈 응답을 무운행으로 단정하지 않고 공식 열차표로 보완.'),
('서울 전철·지도 [4,6]','같은 열차번호의 승하차를 연결. 서울 접근·환승·지상 보행은 계획 가정.'),
('ITS·공동주택·동 현황 [7,12,13]','현재 승차 규모와 지역 주택·인구 맥락을 확인. 신규 새벽 서울행 수요로 대체하지 않음.')],[174,333],True)
add('04:00 이후 출발, 외부 접근 보행 합계 20분 이내, 지역 승차 여유 2분, 장거리 승강장 이동 5분·승차 여유 10분. 시내 후보 848개와 대응된 추천 1,926개를 검토한다. 허브별 가장 이른 준비시각에 승차 가능한 장거리편을 연결하고, 명시한 서울 전철 회랑 중 최종 도착이 가장 이른 후보를 선택한다. 모든 환승을 완전 탐색한 최적해는 아니다. 자료별 제공기관·플랫폼·URL·선정 이유는 참고문헌의 활용 데이터 목록에 제시했다.',small)
page()
head('03','요일과 목적지가 바뀌면','보강 3 · 분석 결과와 출발시각 설계')
add('5개 날짜 × 3개 목적지 × 20개 표본을 비교',sub)
table(['날짜 / 핵심 두 표본','강남역','서울역','사당역'],[
('평일 10/8·13·15\nLH10·풀에버 동일','11:00→09:27\n93분','11:21→09:44\n96.5분','11:04→09:33\n91분'),
('토 10/17 LH10\n비고 매칭 후보','10:59→09:37\n82분','11:16→09:58\n78분','11:06→09:44\n82분'),
('토 10/17 풀에버\n비고 매칭 후보','11:19→09:37\n102분','11:40→09:58\n102분','11:23→09:44\n99분'),
('토요일 배정 불확실성\n두 표본의 경계','82~102분','78~102분','82~99분'),
('일 10/18\nLH10·풀에버 동일','10:59→09:05\n114분','11:16→09:28\n108분','11:06→09:11\n115.5분')],[159,116,116,116])
add('시각은 분 단위 올림 표기, 개선 폭은 초까지 유지해 계산했다. 토요일은 지선 후속 운행의 확정 배정이 없어 단일 효과를 확정하지 않는다. 첫·막차만 쓰는 보수적 계산과 전체 노선번호 묶음을 허용하는 낙관적 계산 사이의 범위다. 300개 비교 중 36개는 배정 가정에 영향을 받았다. 전체 망의 보장 범위는 아니다.',small)
add('새 제안: 첫 서울행 출발 50분 전에 풀에버 출발',sub)
table(['요일','혁신 첫 서울행','풀에버→LH10→승차장','계획 스트레스 여유'],[
('평일','05:30','04:40→04:46→04:55','2.5분'),('토요일','05:40','04:50→04:56→05:05','2.5분'),('일요일','05:10','04:20→04:26→04:35','2.5분')],[74,111,213,109])
add('승객 운송 약 3.066km·15분 계획. 22.5분 주행(1.5배) + 승강장 이동 10분 + 승차 여유 15분에도 2.5분이 남는다. 성공률을 추정한 수치가 아니다. 기존 04:45 고정안은 일요일 첫차를 놓쳐 강남 10:59가 된다. 150번 전 구간 추가편도 요일별 시각 조정이 필요하다.',small)
callout('좌석과 날짜를 함께 확정한다. 조회 당시 10/17 혁신 첫 서울행 잔여석은 9석이었다. 12석 연계 차량을 확보해도 장거리 12석이 자동 확보되지 않는다. 먼저 실제 승차권을 확인한다. [9]')
page()
head('04','인원보다 일행과 좌석을 먼저','정책제안 및 기대효과 · 수요와 운영비 비교')
add('운영비 예시는 실제 견적이 아닌 조건 비교다',sub)
add('같은 인원·같은 본인부담에서 총비용을 비교한다. 가족·기존 일행은 택시 한 대를 함께 이용하지만 서로 모르는 예약자는 합치지 않는다. 연계편 차량 수는 취소 마감 후 확정 인원을 좌석 수로 나누어 올림한다. 뒤늦은 불참은 이미 계약한 연계 차량 비용을 줄이지 않는 가정이다.')
table(['예약·일행·운영 조건','탑승','연계 / 운행택시','총비용 연계/택시\n만원','지원비 연계/택시\n만원'],cost_rows(),[184,39,79,102,103],True)
add('기본 가정: 연계 6만원/대·12석, 택시 5천원/대·3석, 탑승자 본인부담 1,650원. 미사용 예약택시 요금 0/50/100%는 조건 격자다. 표의 지원비=max(0, 총비용-실제 탑승자 본인부담). 사전 취소는 계약 전에 반영하고, 4명 불참은 명시한 일행 배열 뒤부터 차감한 한 사례다. [6,8]',small)
story.append(CostPlot())
add('남색 점선: 연계편 계약 총비용. 12석을 넘으면 2대가 필요해 6만→12만원으로 뛴다. 같은 12명도 독립 일행이면 택시 12대, 2명씩 일행이면 6대다. 단순 ‘몇 명이면 버스’ 기준을 폐기했다.',small)
add('실제 승차 통계는 운영 맥락으로 사용한다',sub)
add('진주 ITS 9월 150번 승차 68,904건 중 05시대는 176건, 하루 평균 5.9건이다. 노선 전체의 기존 승차이며 새벽 서울행 수요가 아니다. 시간대·일별·노선별 전체 합계 1,983,808건은 일치하지만 행정동 합계는 3,697건 작아 공간 재배분하지 않았다. [7]',small)
add('당일 선택: 승차권 확보→취소 마감→일행별 택시 대수·연계 좌석/차량 확보→동일 서비스 범위의 견적 비교→날짜별 출발시각 확정. 연계 견적이 비싸면 개별 접근 지원을 선택할 수 있다. 인허가·보험·새벽 배차·회송·취소 규정은 업체 확인이 필요하다.',small)
page()
head('05','복원해도 유지되는 결론, 남는 한계','보강 2 · 검증 · 정책 효과 · AI 활용')
table(['검증 항목','수정과 확인 결과'],[
('기존 시간표 제외 50방향','상세표의 최솟값은 노선번호 전체 묶음이었다. 각 지선 첫차가 묶음 안에 존재해 모두 복원. 비고 매칭을 확정 지선 배정으로 부르지 않음.'),
('미대응 추천 471개','좌표 3m 이내 + 앞 정류장 순서 일치 + 유일한 방향일 때 127개 복원. 344개는 남음(핵심 두 지점 22개). 원문·대응표를 별도 보존.'),
('세 배정 가정·180개 시나리오','첫·막차 / 첫차와 동일 비고 / 전체 묶음 허용을 비교. 평일 핵심 두 지점의 93분 개선은 세 가정에서 일치.'),
('주말·목적지·좌석 검증','토요일 지선 경계 공개, 일요일 출발 수정, 잔여 0석편을 제외한 별도 계산. 미래 TAGO 빈 응답을 공개 배차로 대조.'),
('코드 내부 일관성','공개 캐시의 순서·정류장 대응·경계·비용 계산을 검사. 실제 운행 성공·새 수요·계약 원가를 입증하는 검사는 아님.')],[144,363],True)
add('도착 기회와 여정 길이를 구분한다',sub)
table(['동일 상세 출발점','기존 출발→도착 / 여정','추가 출발→도착 / 여정'],[
('LH10 지도 지점','06:23→11:00 / 277분','04:38→09:27 / 289분'),('풀에버 정문','06:21→11:00 / 279분','04:36→09:27 / 291분')],[138,184,185])
add('105분 일찍 나가서 93분 일찍 도착한다. 기본 여정은 12분 늘며, 기존 300번 예상 통과의 7분 여유를 추가해도 5분 더 길다. 약속·진료·업무의 이른 도착 선택지를 넓힐 수 있지만 목적별 수요를 조사한 것은 아니다.',small)
add('해석과 실행의 한계',sub)
add('표본은 인구 대표 표본이 아니며 신도시 개발의 인과효과도 아니다. 버스·서울 전철의 모든 환승을 탐색하지 않아 완전망 최적해를 보장하지 않는다. 미래 철도는 공식 매일 운행 KTX 204·382·206으로 보완했으나 일반열차 전체를 완전 수집하지 않았다. 시내 예상 통과, 보행, 공휴일·임시 배차 변경, 서울 도로 지연은 갱신·확인이 필요하다. 현장조사 없이 수요·실측 신뢰도·비용 편익비를 만들어내지 않는다.',small)
add('AI 기술 활용 · 도구·범위·주요 프롬프트',sub)
add('OpenAI Codex로 공개자료 수집·정류장 대응·시간표 연결·민감도·코드·PDF를 작성했다. 주요 지시는 “같은 서울 목적지의 이른 도착과 첫 운행 조정 효과를 분석”, “버스 외 철도 대안을 포함”, “공개자료 중심으로 규모·누락·요일/목적지·운영비를 보강”이다. 반례는 주말 고정안 실패, 가족 동승, 좌석 부족, 지선 배정 불확실성, 도착과 여정의 차이로 점검했다. 참가자의 자료·해석 최종 확인이 필요하다.',small)
add('분석도구: Python 3의 CSV·JSON 처리와 시간순 경로 탐색, openpyxl(공식 철도표 전처리), reportlab(PDF), 공개 원문 대조. RUN_ANALYSIS.txt에 캐시 재현 절차를 제시했다. 시간표는 Python 계산만으로 확인 가능하며 AI 서비스 접속을 요구하지 않는다.',small)
if IDENTITY.get('code_url'):
    url=IDENTITY['code_url'];add('분석 코드(GitHub): <link href="'+escape(url,quote=True)+'" color="#008C88">'+escape(url)+'</link>',small)
else:add('분석 코드 공개 링크는 제출 정리 단계에서 확정한다. [11]',small)
page()
head('06','활용 데이터 목록과 출처','분석도구 및 참고문헌 / 본문 5쪽 외')
refs=[
('[1] 진주시 BIS','노선·방향·요일·예상 통과·추천 경로. 상세 묶음표와 지선 요약표 구분.','https://bis.jinju.go.kr/addInfo/addInfoTimeTable.do'),
('[2] TAGO 고속버스정보 / 국토교통부','2026.10.08 출발·도착 API 원문. 날짜·허브 메타데이터 보존.','https://www.data.go.kr/data/15098522/openapi.do'),
('[3] TAGO 열차정보 / 국토교통부','2026.10.08 진주 출발 열차 번호·시각. 버스 대비 철도 대안.','https://www.data.go.kr/data/15098552/openapi.do'),
('[4] 서울교통공사 열차운행 시각표','2026.09.01 적용 CSV. 요일·방향·같은 열차번호 승하차 연결.','https://www.data.go.kr/data/15098251/fileData.do'),
('[5] 한국철도공사 열차시각표','KTX 10/1·광명셔틀 9/1·수인분당 8/22 적용 공식 원문.','https://www.korail.com/com/userBoard.do?mode=list&schBcid=ticketTable'),
('[6] 카카오맵','10/8 공개 화면의 보행·승차 방향·택시 참고액. 실측이나 견적 아님.','https://map.kakao.com/'),
('[7] 진주시 ITS','9/1~9/30 노선·시간대·일별·행정동 승차. 신규 수요로 사용하지 않음.','https://its.jinju.go.kr/its/stt/view'),
('[8] 진주시 BIS 요금','성인 카드 1,650원을 두 안의 공통 본인부담 가정에 사용.','https://bis.jinju.go.kr/addInfo/addInfoCharge.do'),
('[9] KOBUS','10/13·15·17·18, 3개 허브의 09시 이전 공개 배차·소요·잔여석 대조.','https://www.kobus.co.kr/oprninf/alcninqr/oprnAlcnPage.do'),
('[10] TAGO 시외버스정보 / 국토교통부','빈 응답·게시표 적용일 미확인은 결측으로 취급. 별도 보조 계산.','https://www.data.go.kr/data/15098541/openapi.do'),
('[11] 숲과나눔 공모전 안내','필수 보고서 항목·본문 약 5쪽·초기 코드 공개 링크 등 형식.','https://koreashe.org/notice/?mod=document&uid=95427'),
('[12] 경상남도 진주시 공동주택현황','2026.07.01 공공데이터포털 CSV. 두 관련 단지의 주택 수.','https://www.data.go.kr/data/15046124/fileData.do'),
('[13] 진주시 충무공동 일반현황','2026.07.01 세대 및 인구 표. 행정동 전체 규모.','https://www.jinju.go.kr/00135/01114/01906.web')]
if (ROOT/'submission/data_catalog.json').exists():
    catalog=json.loads((ROOT/'submission/data_catalog.json').read_text())
    rows=[]
    for r in catalog:
        url=r['url'];rows.append(['['+r['reference']+'] '+r['data_name'],r['provider'],r['platform'],'<link href="'+escape(url,quote=True)+'">'+escape(url)+'</link>',r['selection_reason']])
    table(['활용 데이터(명)','제공기관','출처 플랫폼','URL','선정 이유'],rows,[112,68,64,165,98],True)
    add('[11] 숲과나눔 공모전 공식 안내 및 붙임2 분석보고서 양식<br/><link href="https://koreashe.org/notice/?mod=document&amp;uid=95427">https://koreashe.org/notice/?mod=document&amp;uid=95427</link>',mini)
else:
    for title,reason,url in refs:
        add(title,ParagraphStyle('refhead',parent=small,textColor=TEAL,spaceAfter=1))
        add(escape(reason)+'<br/><link href="'+escape(url,quote=True)+'" color="#526B79">'+escape(url)+'</link>',mini)
add('조회일 2026.10.08. 날짜별 배차·잔여석은 조회 당시 정보다. 원문·요청조건·출처는 로컬 재현 묶음에 보존하되 인증키·쿠키·CSRF가 든 페이지는 배제한다. 공개 GitHub는 코드와 집계표를 제공하며 전체 원문 캐시의 이용허락을 새로 부여하거나 재배포하는 저장소가 아니다.',small)
build('jinju_first_connection_analysis.pdf','첫차의 연결이 서울 도착 기회를 바꾼다: 공개자료 검증판')
if IDENTITY.get('participant'):
    import shutil
    shutil.copyfile(ROOT/'output/pdf/jinju_first_connection_analysis.pdf',ROOT/'output/submission'/f"{IDENTITY['participant']}_분석보고서.pdf")

story=[]
head('A1','표본과 분석 재현 범위','검증 부록 / 본문 외')
add('본문의 결론을 재계산할 수 있도록 입력·배정 가정·요일·좌석·비용과 남는 결측을 제시한다. 경로는 후보 집합의 계산 결과이며 실제 운행·승객 수 관측이 아니다.',small)
table(['권역','대표 정류장','기존 강남','연계 강남','기존 장거리 허브'],[[a['zone'],a['origin']+' / '+a['origin_id'],a['arrival_hhmm'],b['arrival_hhmm'],a['trip']['hub']] for a,b in zip(B['results'],F['results'])],[48,189,72,72,126],True)
add('핵심 승차 방향: LH10 49007, 풀에버 49035. 지도 지점→승차 정류장 보행은 각각 6분·2분. 대표 정류장의 계산과 단지 내 전 세대의 접근성은 서로 다른 범위다. [6]',small)
add('입력: direct 848 + 기존 대응 추천1,799 + 좌표 대응 추천127. 기본 유효 후보 '+str(B['evaluated_paths'])+'개, 예상시간 누락/순서 문제 '+str(B['missing_offsets'])+'건. 수치는 고유 노선 수가 아닌 후보 처리 수다.',small)
page()
head('A2','주택 규모와 수요의 근거','보강 1 / 공식 원문과 단위')
table(['단지','시 공식 CSV 주소','주택 수','동 수'],[[r['아파트명'],r['새주소'],r['세대수'],r['동수']] for r in H['housing_rows']],[171,185,75,76])
add('공동주택 CSV 총 282행, 기준일 2026.07.01. 단지명으로 두 행을 고르고 세대수 칼럼을 합했다. 1,421+404=1,825호. 주택 호수는 실제 입주 가구 수·거주자 수·서울행 승객 수를 뜻하지 않는다. [12]')
table(['충무공동 시 공식 현황 / 2026.07.01','값'],[['등록 세대',f"{H['admin_registered_households']:,}"],['등록 인구',f"{H['admin_population']:,}"],['남 / 여',f"{H['admin_men']:,} / {H['admin_women']:,}"]],[302,205])
add('공식 페이지의 “세대 및 인구” 표를 텍스트로 보존했다. 16,597+17,101=33,698. 행정동 인구를 두 아파트나 접근 권역에 배분하지 않는다. 차량 보유·근로시간·서울행 목적별 인구 자료는 확보하지 않았다. [13]',small)
table(['노선 / 9월','월 승차','05시 승차','일평균','시간/일/노선 합계'],[[r['route'],f"{r['monthly_boardings']:,}",r['hour05'],f"{r['hour05']/30:.1f}",'일치' if r['reconciled'] else '불일치'] for r in D['demand']['routes']],[68,102,99,84,154])
add('승차 건수는 반복 이용을 포함한 연인원이다. 전체 시간대/일별/노선 합계 1,983,808건, 행정동 합계 1,980,111건(3,697건 차이). 04시대 승차 0을 잠재 수요 0으로 읽지 않는다. 서비스 미운행 때문에 발생한 0일 수 있다. [7]',small)
add('실제 수혜 규모를 알려면 예약·승차권·개별 이용 목적을 추가 관측해야 한다. 공개 자료로는 관련 주택·행정동·기존 승차 규모까지만 제시한다.',small)
page()
head('A3','제외 규칙을 고친 근거','보강 2 / 정류장 코드와 지선 운행')
add('노선번호별 상세 시간표는 여러 지선의 묶음이다. 묶음의 최솟값과 개별 지선 요약 첫차가 다르다는 이유로 제외한 50방향을 모두 복원했다. 각각의 요약 첫차가 상세 묶음에 존재한다. 세 가지 배정 방식으로 결과 경계를 비교한다.')
table(['배정 모드','사용 시각','해석'],[['strict','해당 방향 요약 첫·막차','확인 가능한 끝 시각만. 실제 운행 전체보다 적은 후보.'],['matched','첫·막차 + 첫차와 동일 비고, 첫~막 범위','경로 비고가 같아도 지선별 확정 배정은 아님. 주 표의 후보 계산.'],['optimistic','첫·막차 + 해당 노선번호 모든 출발','지선에 운행을 과하게 배정하는 검증 경계. 이용 안내로 제공하지 않음.']],[69,174,264])
add('추천 경로는 원문 2,270개 중 1,799개를 기존 방향·순서로 대응했다. 미대응 471개 중 127개는 원문 마지막 좌표와 현재 방향의 정류장 좌표 3m 이내, 앞 정류장 전부의 순서 일치, 유일한 방향 조건을 모두 통과해 추가했다. 같은 이름만으로 매핑하지 않았다.')
counts={}
for r in A['crosswalk']:
    k=(r['raw_stop'],r['network_stop']);counts[k]=counts.get(k,0)+1
table(['추천 코드 → 현 노선 코드','대응 leg 수','근거'],[[a+' → '+b,n,'좌표 ≤3m, 앞 정류장 순서, 방향 유일'] for (a,b),n in sorted(counts.items())],[204,74,229],True)
add(f"복원 후 남는 추천은 {A['remaining_paths']}개, 핵심 두 지점의 남는 추천은 {A['focal_remaining']}개다. 코드 목록에 없는 4개 노선 ID는 공개 노선 조회도 rows=0이었다. 폐선으로 단정하지 않으며, 나머지는 좌표·전체 정류장 순서·방향을 유일하게 확정할 수 없었다. 따라서 완전망 최적해를 주장하지 않는다.",small)
add('이 절차는 공개 자료 안의 별도 코드 대응이며 현장 승강장 위치와 실제 운행을 검증한 것은 아니다. 검증 코드와 대응 좌표·원문 경로 파일명을 alias_audit.json에 보존했다.',small)
page()
restored=D['branches']['previous_exclusions']
for part in range(2):
    head('A'+str(4+part),'복원한 50개 노선·방향','요약 첫차와 상세 묶음의 비교 '+str(part+1)+'/2')
    table(['노선','base ID','방향','요약 첫차','묶음 첫차','첫차 존재'],[[r['label'],r['base'],r['direction'],hhmm(r['first']),hhmm(r['family_first']),'예' if r['first_present'] else '아니오'] for r in restored[part*25:(part+1)*25]],[82,115,45,80,80,105],True)
    add('방향 2는 ed_firsttime/btt_endtime, 나머지는 firsttime/btt_starttime을 대조했다. 지선 비고·첫/막차·모든 후보 시각은 analysis.json의 branches에 있다. 첫차가 묶음 안에 있다는 확인과 모든 후속 운행의 지선 배정 확정은 서로 다르다.',small)
    page()
head('A6','날짜·목적지별 정확한 계산값','보강 3 / 두 상세 사례, 단위 분')
table(['날짜','목적지','표본','기존','연계','앞당김'],[[r['date'][5:],r['target'],r['origin'],r['baseline'],r['feeder'],f"{r['advance']:g}"] for r in D['focal_comparison']],[65,69,132,75,75,91],True)
add('비고 매칭 후보 계산. 시각은 분 올림, 앞당김은 분 소수점 유지. 토요일 범위: 강남 82~102 / 서울역 78~102 / 사당 82~99분. 경계 모드·300개 전체 표본 비교·개별 전철 열차번호는 JSON/CSV에 보존한다.',small)
page()
head('A7','날짜와 좌석의 증거를 함께','장거리 공개 배차 · 요일별 시내표 · 철도')
raw=json.loads((ROOT/'data/raw/strengthening/robust/kobus_calendar.json').read_text())
table(['날짜','허브','09시 전 배차 수','첫차','예상 소요','첫차 잔여석'],[[r['date'][5:],r['hub'],len(r['departures']),r['departures'][0],str(r['duration'])+'분',r['remaining_seats'][0]] for r in raw['records']],[65,102,82,80,84,94],True)
add('09시 이전 배차만 공개 화면에서 대조했다. KOBUS 도착은 출발+공시 예상 소요시간이며 실제 도착 기록이 아니다. 잔여석은 10/8 조회 순간의 값이다. 10/17 혁신 첫차 9석, 07:00 개양편 0석. 0석편을 제외한 별도 계산에서는 두 핵심 표본 강남 기존 11:19→연계 09:37이다. 좌석 존재를 미래 예약 보장으로 해석하지 않는다. [9]',small)
add('미래 TAGO 고속버스 빈 응답은 공개 배차와 모순되므로 자료 공백으로 처리했다. 미래 열차는 코레일 10/1 적용 경전선 KTX의 매일 운행 204(진주06:10)·382(07:08)·206(08:56)을 서울·광명·수서까지 연결했다. 중간역 공시 시각은 도착보다 늦을 수 있어 보수적으로 사용했다. 미래 일반열차를 모두 확보한 결과는 아니다. [2,3,5]',small)
add('시내 요약표: 평일190개·토/일177개 노선. 상세표 추가214요청 중210개는 요일 분류 일치, 901/902의 4응답은 요일 필드가 없어 별도 저장하고 상세 운행 배정에 쓰지 않았다. 이 경우 요약 첫·막차는 유지한다. 서울 전철은 DAY/SAT/END 분류를 각각 적용했다. 임시 공휴일·배차 변경은 별도 갱신이 필요하다. [1,4]',small)
page()
head('A8','운행 비용과 취소를 계산하는 식','보강 4 / 비용·좌석·계약 조건')
add('n은 취소 마감 후 확정 인원, s는 연계차 좌석, Q는 차량 한 대의 전체 견적, T는 택시 한 대 요금, α는 미사용 예약택시 수수료율이다. 기존 일행별 택시 대수는 일행 인원/택시 좌석의 올림을 합한다. 서로 모르는 일행을 합쳐 택시 대수를 줄이지 않는다.')
callout('연계 총비용 = ceil(n/s) × Q<br/>택시 총비용 = T × (실제 운행 대수 + α × 미사용 예약 대수)<br/>공공지원 = max(0, 총비용 - 1,650 × 실제 탑승자 수)')
table(['조건','탑승','연계 / 운행택시','총비용 연계/택시\n만원','지원비 연계/택시\n만원'],cost_rows(),[184,39,79,102,103],True)
add('8,100개 조합: 예약4/8/12/16/20명, 기존 일행1/2/3명, 연계 견적3/6/9/12만원, 택시4,600/5,000/8,000원, 연계8/12/16석, 미사용택시0/50/100%, 취소·불참 다섯 패턴. 조건을 바꾸면 유리한 수단이 달라지며 현재 비교는 새벽 계약 견적이나 운송 사업 승인을 대신하지 않는다.',small)
add('부분 불참은 일행 목록 끝에서 인원을 제거한다. 같은 예약인원·불참자수라도 일행 내 불참 분포가 다르면 실제 택시 대수가 달라지므로 운영 시 개별 일행을 확인해야 한다. Q와 T는 회송·노무·예약요금 등 동일 서비스 범위로 비교해야 한다.',small)
add('12명 독립 일행, 12석·6만원이면 총비용 동률. 2명씩 가족 여섯 일행이면 택시는 3만원으로 더 저렴하다. 8석이라면 연계차 두 대가 필요해 12만원이다. ‘일 12명 이상이면 버스’ 같은 고정 인원 기준은 쓰지 않는다.',small)
page()
head('A9','실행과 검증의 기록','재현 · AI 활용 · 자료 공백')
table(['순서','실행 / 결과'],[
('1. 원문 별칭 복원','python3 analysis/repair_transfer_aliases.py'),('2. 주 분석','python3 analysis/analyze_robustness.py\noutputs/robust/analysis.json, calendar_destination_comparison.csv'),('3. 논리 검증','python3 analysis/check_robustness.py\noutputs/robust/validation.json'),('4. 보고서 작성','python3 analysis/build_robust_report.py\nreportlab 및 한글 TTF 필요'),('5. 재현 묶음','python3 analysis/create_reproduction_bundle.py\n키·세션 자료를 제외한 allowlist와 SHA-256 목록')],[108,399])
add(f"검사 {V['passed']:,}개 통과: 원문 코드 대응 보존, 시내/장거리/전철 시간순서, 같은 전철 열차번호, 지선 경계 포함관계, 추가편의 기존 서비스 보존, 여정 산식, 비용·좌석·취소·불참 계산. 검사 수는 내부 일관성의 범위이며 관측 정확도나 수상 가능성의 척도가 아니다.",small)
add('주요 AI 지시와 적용',sub)
add('① 같은 목적지의 이른 도착과 첫 운행 개선을 분석 ② 버스 외 철도 대안도 확인 ③ 공개자료 중심으로 지역 규모·누락 경로·요일/목적지·비용을 보강. Codex가 수집·계산·반례·문서 작업을 수행했다. 핵심 반례: 첫차 묶음과 지선 혼동, 가상 정류장 코드, 일요일 고정안 실패, 토요일 매진, 가족 동승, 좌석 초과, 도착 기회와 긴 여정.',small)
add('공개자료 분석으로 남는 것',sub)
add('추가 설문·현장 관측 없이 신규 탑승 수요나 실측 성공률을 확인하지 않았다. 남는 미대응 추천344개, 요일 미분류 상세표4응답, 미래 일반열차 불완전 수집, 임시 시간표, 보행·통과 예상치, 실제 새벽 견적을 명시했다. 분석 질문의 답은 조건부 후보 비교이며 모든 대안의 최적해나 사업 타당성 확정이 아니다.',small)
add('본문 참고문헌 [1]-[13] 및 캐시 메타데이터를 함께 보관한다. 김주형 개인 참가 보고서에 공개 GitHub 코드 링크를 기입했다. 공개 저장소의 review_results.py는 집계표와 비용을 키 없이 검토하며, 원문 경로 결합의 전체 재현은 별도 로컬 캐시 묶음을 사용한다. 공식 참가신청서의 소속·연락처·동의·서명은 참가자가 확인/작성해야 한다. 이메일 접수는 수행하지 않았다.',small)
build('jinju_first_connection_evidence.pdf','첫차 연결 분석: 공개자료 복원과 운영 검증 부록')
