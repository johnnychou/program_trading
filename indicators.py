import numpy as np

def atr_calculation(candles_list, period, atr_record):
    if len(candles_list) < period:
        return 0

    if not atr_record[-1]:
        candles = candles_list[-period:]
        tr = 0
        for i in len(candles):
            if i == 0:
                tr += candles[0]['high'] - candles[0]['low']
            else:
                tr += max(candles[i]['high'] - candles[i]['low'],
                          np.abs(candles[i]['high'] - candles[i-1]['close']),
                          np.abs(candles[i]['low'] - candles[i-1]['close']))
        atr = round(tr/period, 2)
    else:
        atr = atr_record[-1]
        data = candles_list[-1]
        pre_data = candles_list[-2]
        tr = max(data['high'] - data['low'],
                 np.abs(data['high'] - pre_data['close']),
                 np.abs(data['low'] - pre_data['close']))
        atr = round((((period-1)*atr)+tr)/period, 2)
    
    return atr

def find_peak_from_candles(candles_list, period):
    if len(candles_list) < period:
        return 0
    candles = candles_list[-period:]
    for i in len(candles):
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

def price_ma(candles_list, period):
    if len(candles_list) < period:
        return 0
    p_ma = 0
    candles = candles_list[-period:]
    for i in len(candles):
        p_ma += candles[i]['close']
    p_ma = p_ma / period
    return round(p_ma, 2)

def price_ema(candles_list, period, ema_record):
    if len(candles_list) < period:
        return 0
    else:
        if not ema_record[-1]:
            ema = price_ma(candles_list, period)
        else:
            a = 2/(period+1)
            ema = (candles_list[-1]['close'] - ema_record[-1])*a + ema_record[-1]
    return round(ema, 2)

def bollinger_bands_calculation(candles_list, period):
    if len(candles_list) < period:
        return 0

    std = 0
    ma = price_ma(candles_list, period)
    
    for data in candles_list[-period:]:
        std += (data['close'] - ma)**2

    std = (std/period)**0.5

    # Calculate upper and lower bands
    upper = round(ma + (std * 2), 2)
    lower = round(ma - (std * 2), 2)
    return [upper, ma, lower]


