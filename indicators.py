
def find_peak_from_candles(candles_list, period):
    if len(candles_list) < period:
        return 0
    candles = candles_list[-period:]
    for i in range(period):
        if i == 0:
            max_p = candles[0]['high']
            min_p = candles[0]['low']
        else:
            if max_p < candles[i]['high']:
                max_p = candles[i]['high']
            if min_p > candles[i]['low']:
                min_p = candles[i]['low']
    return max_p, min_p

def kd_calculation(candles_list, period, kd_record): # 1=buy,-1=sell, 0=wait
    if len(candles_list) < period:
        return 0

    max_price, min_price = find_peak_from_candles(candles_list, period)
    last_price = candles_list[-1]['close']

    if (max_price - min_price) == 0:
        return 0
    
    if kd_record[-1]:
        pre_k = kd_record[-1][0]
        pre_d = kd_record[-1][1]
    else:
        pre_k = 50
        pre_d = 50

    rsv = ((last_price - min_price) / (max_price - min_price)) * 100
    k = 2/3*(pre_k) + 1/3*rsv
    d = 2/3*(pre_d) + 1/3*k

    return [k, d]

