import numpy as np
import pandas as pd

MA_PREFIX = 'ma_'
EMA_PREFIX = 'ema_'
ATR_PREFIX = 'atr_'
KD_PREFIX = 'kd_'

def indicator_ma(df, period):
    """
    計算 DataFrame 中指定欄位的簡單移動平均線 (SMA)，並優化效能。
    """
    key = MA_PREFIX + str(period)

    if key not in df.columns:  # 首次計算
        df[key] = df['close'].rolling(window=period).mean().round().fillna(0).astype(int)  # 首次計算時，將 NaN 填 0
    else:  # 後續計算
        if len(df) >= period:
            # 只計算最後一個值
            ma = df['close'].iloc[-period:].mean().round().astype(int)
            df.loc[df.index[-1], key] = ma
        else:
            df.loc[df.index[-1], key] = 0  # 資料不足填 0
    return


def indicator_ema(df, period):
    """
    計算 DataFrame 中指定欄位的指數移動平均線 (EMA)，並優化效能。
    """
    key = EMA_PREFIX + str(period)

    if key not in df.columns:  # 首次計算
        df[key] = df['close'].ewm(span=period, adjust=False).mean().round().fillna(0).astype(int)
    else:  # 後續計算
        if len(df) >= period:
            ema = (df['close'].iloc[-1] * 2 + df[key].iloc[-2] * (period - 1)) / (period + 1)
            df.loc[df.index[-1], key] = int(round(ema))
        else:
            df.loc[df.index[-1], key] = 0
    return

def indicator_atr(df, period=14):
    key = ATR_PREFIX + str(period)
    if key not in df.columns:  # 首次计算
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        df[key] = tr.rolling(window=period).mean().round(1).fillna(0)
    else:
        tr1 = df['high'].iloc[-1] - df['low'].iloc[-1]
        tr2 = abs(df['high'].iloc[-1] - df['close'].iloc[-2]) if len(df) > 1 else 0
        tr3 = abs(df['low'].iloc[-1] - df['close'].iloc[-2]) if len(df) > 1 else 0
        tr_current = max(tr1, tr2, tr3)

        atr_prev = df[key].iloc[-1]
        atr = (atr_prev * (period - 1) + tr_current) / period if len(df) >= period else tr_current
        df.loc[df.index[-1], key] = atr.round(1)
    return

def calculate_kd(df, n=9, k=3, d=3):
    """計算 DataFrame 的 KD 指標。

    Args:
        df (pd.DataFrame): 包含 'high'、'low' 和 'close' 欄位的 DataFrame。
        n (int): 計算 RSV 的週期，預設為 9。
        k (int): 計算 K 值的 SMA 週期，預設為 3。
        d (int): 計算 D 值的 SMA 週期，預設為 3。
    """
    key = KD_PREFIX + str(n)
    # 計算 RSV
    low_list = df['low'].rolling(n, min_periods=n).min()
    high_list = df['high'].rolling(n, min_periods=n).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100

    # 計算 K 值
    k_value = rsv.rolling(k, min_periods=k).mean()

    # 計算 D 值
    d_value = k_value.rolling(d, min_periods=d).mean()

    df[key] = [k_value, d_value, rsv]
    return

def exponential_moving_average(num_list, period, ema_record=[]):
    if len(num_list) < period:
        return 0
    else:
        if not ema_record:
            num_list = num_list[-period:]
            ema = sum(num_list)/len(num_list)
        else:
            a = 2/(period+1)
            ema = (num_list[-1] - ema_record[-1])*a + ema_record[-1]
        ema_record.append(round(ema, 2))
    return ema_record

def bollinger_bands_calculation(candles_list, period):
    if len(candles_list) < period:
        return 0

    std = 0
    ma = candles_sma(candles_list, period)
    
    for data in candles_list[-period:]:
        std += (data['close'] - ma)**2

    std = (std/period)**0.5

    # Calculate upper and lower bands
    upper = round(ma + (std * 2), 2)
    lower = round(ma - (std * 2), 2)
    return [upper, ma, lower]

def rsi_calculation(candles_list, period):
    if len(candles_list) < period:
        return 0
    data = candles_list[-period:]
    up_wave = 0
    dn_wave = 0
    for i in range(len(data)):
        if i == 0:
            continue
        else:
            if data[i]['close'] > data[i-1]['close']:
                up_wave += (data[i]['close'] - data[i-1]['close'])
            elif data[i]['close'] < data[i-1]['close']:
                dn_wave += (data[i-1]['close'] - data[i]['close'])
    up_wave_avg = up_wave/period
    dn_wave_avg = dn_wave/period
    rsi = round((up_wave_avg/(up_wave_avg+dn_wave_avg))*100, 2)
    return rsi

def macd_calculation(candles_list, macd_dif_list, macd_histogram, p1=12, p2=26, p3=9):
    ema_short = indicator_ema(candles_list, p1, ema_short)
    ema_long  = indicator_ema(candles_list, p2, ema_long)
    if ema_short and ema_long:
        dif = round(ema_short-ema_long, 2) #DIF快線
        macd_dif_list.append(dif)
        dea = exponential_moving_average(macd_dif_list, p3, dea) #DEA慢線
        if dea:
            macd_histogram.append(round(dif-dea, 2)) #直方圖
        if len(macd_histogram) > 4:
            macd_histogram = macd_histogram[-4:]
    return macd_dif_list, macd_histogram