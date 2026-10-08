"""Three preselected common destinations; explicit scheduled corridor set.

No claim to a complete Seoul network optimum. All entry/transfer/exit walking
times are planning assumptions. Train pairing is inherited from the audited
official metro table, by line, day class, direction and train number.
"""
from functools import lru_cache
from metro_connections import ITINERARIES, connections, finish

CORRIDORS = {
 '서울역': {
  '서울경부': [(8,[('3','고속터미널','충무로',5),('4','충무로','서울역',0)])],
  '서울남부': [(5,[('3','남부터미널','충무로',5),('4','충무로','서울역',0)])],
  '광명': [(10,[('1','광명','서울역',0)])],
  '수서': [(8,[('3','수서','충무로',5),('4','충무로','서울역',0)])]},
 '사당': {
  '서울경부': [(8,[('3','고속터미널','교대',4),('2','교대','사당',0)])],
  '서울남부': [(5,[('3','남부터미널','교대',4),('2','교대','사당',0)])],
  '서울': [(10,[('4','서울역','사당',0)])],
  '광명': [(10,[('1','광명','신도림',5),('2','신도림','사당',0)]),
          (10,[('1','광명','가산디지털단지',6),('7','가산디지털단지','대림',5),('2','대림','사당',0)])],
  '수서': [(8,[('3','수서','교대',4),('2','교대','사당',0)]),
         (10,[('수인분당','수서','선릉',5),('2','선릉','사당',0)])]}
}

@lru_cache(None)
def finish_target(gateway, arrival, day='DAY', target='강남', extra=0):
    if target == '강남': return finish(gateway, arrival, day, extra)
    if target == '서울역' and gateway == '서울':
        return {'arrival':arrival+10+extra, 'legs':[], 'walking_minutes':10+extra,
                'scope':'서울역 장거리 열차 하차→공통 지상 도착점 10분 가정'}
    options=[]
    for entry, legs in CORRIDORS[target].get(gateway, []):
        clock=arrival+entry+extra; trace=[]; walking=entry+extra+3
        for line, start, end, after in legs:
            choices=[r for r in connections(line,start,end,day) if r['dep'] >= clock+.5]
            if not choices: break
            r=min(choices,key=lambda x:(x['arr'],x['dep']))
            trace.append(r|{'ready':clock,'wait':r['dep']-clock})
            clock=r['arr']+after; walking+=after
        else:
            options.append({'arrival':clock+3,'legs':trace,'walking_minutes':walking})
    return min(options,key=lambda x:x['arrival']) if options else None
