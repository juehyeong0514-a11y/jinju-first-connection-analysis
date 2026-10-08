"""Date-class scheduled transfers, matched by line/day/direction/train code.

Official 2026-09-01 Seoul Metro CSV. Walking/entry/exit minutes are explicit
planning assumptions, not measurements. Kept distinct from actual train times.
"""
import csv
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/strengthening'

def mins(value):
    if not value:return None
    h,m,s=map(int,value.split(':'))
    return h*60+m+s/60

@lru_cache(None)
def records():
    needed={'고속터미널','교대','강남','서울역','사당','대림','가산디지털단지','남부터미널','광명','수서','선릉','신도림','충무로'}
    grouped=defaultdict(list)
    with (RAW/'seoul_metro_20260901.csv').open(encoding='cp949') as stream:
        for r in csv.DictReader(stream):
            if r['역사명'] not in needed:continue
            grouped[(r['호선'],r['역사명'],r['주중주말'])].append({'train':r['열차코드'],'direction':r['방향'],'arr':mins(r['열차도착시간']),'dep':mins(r['열차출발시간']),'source_row':r['고유번호']})
    for r in json.loads((RAW/'korail_suin_records.json').read_text()):
        grouped[(r['line'],r['station'],r['day'])].append(r)
    return grouped

@lru_cache(None)
def connections(line,start,end,day):
    groups=records();end_map=defaultdict(list);pairs=[]
    for r in groups[(line,end,day)]:end_map[(r['train'],r['direction'])].append(r)
    for a in groups[(line,start,day)]:
        if a['dep'] is None:continue
        for b in end_map[(a['train'],a['direction'])]:
            # Short named corridors; reject opposite-direction circle journeys.
            if b['arr'] is not None and 0 < b['arr']-a['dep'] <= 40:
                pairs.append({'line':line,'start':start,'end':end,'dep':a['dep'],'arr':b['arr'],'train':a['train'],'direction':a['direction'],'source_rows':[a['source_row'],b['source_row']]})
    return sorted(pairs,key=lambda x:(x['dep'],x['arr']))

# Minutes from long-distance alighting to platform, then transfer corridors.
# End point is a Gangnam Line 2 street exit, modeled 3 min after train arrival.
ITINERARIES={
 '서울경부':[(8,[('3','고속터미널','교대',4),('2','교대','강남',0)])],
 '서울남부':[(5,[('3','남부터미널','교대',4),('2','교대','강남',0)])],
 '서울':[(10,[('4','서울역','사당',5),('2','사당','강남',0)])],
 '광명':[(10,[('1','광명','가산디지털단지',6),('7','가산디지털단지','대림',5),('2','대림','강남',0)]),
          (10,[('1','광명','신도림',5),('2','신도림','강남',0)])],
 '수서':[(8,[('3','수서','교대',4),('2','교대','강남',0)]),
         (10,[('수인분당','수서','선릉',5),('2','선릉','강남',0)])]
}

@lru_cache(None)
def finish(destination,arrival,day='DAY',walk_extra=0):
    options=[]
    for entry,legs in ITINERARIES.get(destination,[]):
        clock=arrival+entry+walk_extra;trace=[];valid=True;walking=entry+walk_extra+3
        for line,start,end,after_walk in legs:
            # 30 seconds boarding buffer; no zero-duration instantaneous boarding.
            choices=[r for r in connections(line,start,end,day) if r['dep']>=clock+.5]
            if not choices:valid=False;break
            r=min(choices,key=lambda r:(r['arr'],r['dep']))
            trace.append(r|{'ready':clock,'wait':r['dep']-clock})
            clock=r['arr']+after_walk;walking+=after_walk
        if valid:options.append({'arrival':clock+3,'legs':trace,'walking':walking,'entry_walk':entry+walk_extra,'exit_walk':3,'day_type':day,'source':'서울교통공사 2026-09-01 CSV 및 코레일 수인분당 2026-08-22 XLSX; 보행분은 계획 가정'})
    return min(options,key=lambda r:r['arrival']) if options else None

if __name__=='__main__':
    from analyze_connections import hhmm
    for d,t in [('서울경부',545),('서울경부',635),('서울경부',585),('서울',592),('광명',573),('수서',641)]:
        r=finish(d,t)
        print(d,hhmm(t),hhmm(r['arrival']) if r else None, r)
