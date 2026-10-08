"""Party-aware cost/capacity/cancellation scenarios, not demand forecasts.

Parties represent families or people already travelling together. Independent
parties are never combined in a taxi. Quotes, seats and cancellation terms are
explicit assumptions; no actual contract is implied.
"""
import math
from itertools import product

def remove_people(parties, count):
    if not math.isfinite(count) or int(count)!=count or count < 0 or count > sum(parties): raise ValueError('Invalid removal count')
    out = list(parties)
    for i in range(len(out)-1, -1, -1):
        take=min(count,out[i]);out[i]-=take;count-=take
    return out

def evaluate(parties, quote=60000, taxi=5000, seats=12, taxi_seats=3,
             cancellations=0, no_shows=0, no_show_fee=0, copay=1650):
    if any(not math.isfinite(n) or n<=0 or int(n)!=n for n in parties): raise ValueError('Invalid party size')
    if any(not math.isfinite(n) or n<=0 or int(n)!=n for n in [seats,taxi_seats]) or not 0<=no_show_fee<=1: raise ValueError('Invalid capacity/fee')
    if any(not math.isfinite(n) or n<0 for n in [quote,taxi,copay]):raise ValueError('Invalid monetary input')
    booked=sum(parties); committed=remove_people(parties,cancellations)
    shown=remove_people(committed,no_shows); confirmed=sum(committed); actual=sum(shown)
    feeder_vehicles=math.ceil(confirmed/seats)
    # Vehicle assignments are reserved per party, with available taxi seats.
    reserved_taxis=sum(math.ceil(n/taxi_seats) for n in committed)
    active_taxis=sum(math.ceil(n/taxi_seats) for n in shown)
    taxi_gross=taxi*(active_taxis+(reserved_taxis-active_taxis)*no_show_fee)
    feeder_gross=feeder_vehicles*quote
    # Co-pay is capped by total cost; paid only by actual boarding passengers.
    feeder_public=max(0,feeder_gross-copay*actual)
    taxi_public=max(0,taxi_gross-copay*actual)
    return {'booked':booked,'party_sizes':parties,'confirmed':confirmed,'actual':actual,
            'pre_dispatch_cancellations':cancellations,'late_no_shows':no_shows,
            'seats_per_feeder':seats,'taxi_seats':taxi_seats,'feeder_vehicles':feeder_vehicles,
            'reserved_taxis':reserved_taxis,'active_taxis':active_taxis,
            'quote_per_feeder':quote,'taxi_per_vehicle':taxi,'unused_taxi_fee_fraction':no_show_fee,
            'feeder_gross':feeder_gross,'taxi_gross':taxi_gross,
            'feeder_public':feeder_public,'taxi_public':taxi_public,
            'feeder_cheaper_or_equal':feeder_public<=taxi_public,
            'public_cost_difference':feeder_public-taxi_public,
            'gross_quote_ceiling_per_feeder':taxi_gross/feeder_vehicles if feeder_vehicles else 0,
            'actual_load_factor':actual/(seats*feeder_vehicles) if feeder_vehicles else 0,
            'served_within_reserved_capacity':actual<=feeder_vehicles*seats}

def scenarios():
    grid=[]
    for n, party, q, t, seat, fee in product([4,8,12,16,20],[1,2,3],[30000,60000,90000,120000],[4600,5000,8000],[8,12,16],[0,.5,1]):
        sizes=[party]*(n//party)+([n%party] if n%party else [])
        for cancel, absent in [(0,0),(2,0),(0,2),(0,4),(2,2)]:
            if cancel+absent<=n:
                grid.append(evaluate(sizes,q,t,seat,cancellations=cancel,no_shows=absent,no_show_fee=fee))
    examples=[evaluate([1]*12),evaluate([2]*6),evaluate([1]*12,seats=8),
              evaluate([1]*12,cancellations=4),evaluate([1]*12,no_shows=4),
              evaluate([1]*12,no_shows=4,no_show_fee=.5),evaluate([2]*6,no_shows=4)]
    return {'unit':'원/운행일 1회, 지역 접근 구간만 비교','copay':1650,
            'grid':grid,'examples':examples,
            'formula':'동일 본인부담에서 총비용 비교: V_연계 Q ≤ T × (V_실제택시+α V_미사용예약택시). 공공지원은 각 총비용에서 실제 탑승자 본인부담을 빼고 0 하한.',
            'dispatch_rule':'취소 마감 후 확정 인원으로 좌석·차량을 확보한다. 이후 불참은 연계편 계약 비용을 줄이지 않는 가정. 장거리 승차권과 연계편 좌석을 동시에 확인한 뒤 출발시각 확정.',
            'limits':['예시 견적·8/12/16석·택시 3석·취소 마감 전 무상취소·미사용 예약택시 0/50/100% 요금은 계약 조건 가정이다.',
                      '가족·기존 일행 동승만 계산한다. 서로 모르는 예약자의 택시 합승이나 새로운 운송사업 인허가를 가정하지 않는다.',
                      '좌석 부족 시 연계편 2대 비용을 반영한다. 면허·보험·새벽 배차·노무·회송 조건은 업체 확인 전 미확정이다.',
                      '단순 인원수 기준을 폐기하고 당일 일행별 택시 대수·승객 좌석·확정 견적·취소 조건으로 수단을 선택한다.']}
