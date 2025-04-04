import numpy as np
import pandas as pd

MA_PREFIX = 'ma_'
EMA_PREFIX = 'ema_'
ATR_PREFIX = 'atr_'
KD_PREFIX = 'kd_'
RSI_PREFIX = 'rsi_'
BB_PREFIX = 'bbands_'
MACD_PREFIX = 'macd_'

def indicator_ma(df, period):
    """
    計算 DataFrame 中指定欄位的簡單移動平均線 (SMA)，並優化效能。
    """
    key = MA_PREFIX + str(period)
    df[key] = df['close'].rolling(window=period, min_periods=1).mean().round().astype(int)
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
    if key not in df.columns:  # 首次計算
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        df[key] = tr.rolling(window=period, min_periods=1).mean().round(1).astype(float)
    else:
        tr1 = df['high'].iloc[-1] - df['low'].iloc[-1]
        tr2 = abs(df['high'].iloc[-1] - df['close'].iloc[-2]) if len(df) > 1 else 0
        tr3 = abs(df['low'].iloc[-1] - df['close'].iloc[-2]) if len(df) > 1 else 0
        tr_current = max(tr1, tr2, tr3)

        atr_prev = df[key].iloc[-2]
        atr = (atr_prev * (period - 1) + tr_current) / period if len(df) >= period else tr_current
        df.loc[df.index[-1], key] = atr.round(1)
    return

def indicator_rsi(df, period=10):
    key = RSI_PREFIX + str(period)

    if key not in df.columns:
        delta = df['close'].diff()
        up = delta.where(delta > 0, 0)
        down = -delta.where(delta < 0, 0)

        avg_gain = up.rolling(window=period).mean().astype(float)
        avg_loss = down.rolling(window=period).mean().astype(float)

        rs = avg_gain / avg_loss
        rsi = (100 - (100 / (1 + rs))).fillna(0).astype(float)

        df[key] = rsi.round(1)
    else:
        if len(df) >= period:
            delta = df['close'].diff()
            up = delta.iloc[-1:].where(delta.iloc[-1:] > 0, 0).sum()
            down = -delta.iloc[-1:].where(delta.iloc[-1:] < 0, 0).sum()

            avg_gain_prev = df[key].iloc[-14:].diff().where(df[key].iloc[-14:].diff() > 0, 0).mean() if len(df) > period else 0
            avg_loss_prev = -df[key].iloc[-14:].diff().where(df[key].iloc[-14:].diff() < 0, 0).mean() if len(df) > period else 0

            avg_gain = (avg_gain_prev * (period - 1) + up) / period if period > 1 else up
            avg_loss = (avg_loss_prev * (period - 1) + down) / period if period > 1 else down

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            df.loc[df.index[-1], key] = rsi.round(1)
        else:
            df.loc[df.index[-1], key] = 0
    return

def indicator_kd(df, n=9, k=3, d=3):
    """計算 DataFrame 的 KD 指標。

    Args:
        df (pd.DataFrame): 包含 'high'、'low' 和 'close' 欄位的 DataFrame。
        n (int): 計算 RSV 的週期，預設為 9。
        k (int): 計算 K 值的 SMA 週期，預設為 3。
        d (int): 計算 D 值的 SMA 週期，預設為 3。
    """
    key = KD_PREFIX + str(n)

    if key not in df.columns:  # 首次計算
        k_values = [50] * len(df)
        d_values = [50] * len(df)
        rsv_values = [0] * len(df)

        if len(df) >= n:
            for i in range(n - 1, len(df)):
                low_n = df['low'].iloc[i - n + 1 : i + 1].min()
                high_n = df['high'].iloc[i - n + 1 : i + 1].max()
                if high_n == low_n:
                    rsv = 0
                else:
                    rsv = (df['close'].iloc[i] - low_n) / (high_n - low_n) * 100

                k_values[i] = (1 - (1 / k)) * k_values[i - 1] + (1 / k) * rsv
                d_values[i] = (1 - (1 / d)) * d_values[i - 1] + (1 / d) * k_values[i]
                rsv_values[i] = rsv

        df[key] = list(zip(pd.Series(k_values).round(1), pd.Series(d_values).round(1), pd.Series(rsv_values).round(1)))
    
    else:  # 後續計算
        if len(df) >= n:
            low_n = df['low'].iloc[-n:].min()
            high_n = df['high'].iloc[-n:].max()
            if high_n == low_n:
                rsv = 0
            else:
                rsv = (df['close'].iloc[-1] - low_n) / (high_n - low_n) * 100

            k_prev = df[key].iloc[-2][0]
            d_prev = df[key].iloc[-2][1]

            k_value = (1 - (1 / k)) * k_prev + (1 / k) * rsv
            d_value = (1 - (1 / d)) * d_prev + (1 / d) * k_value

            df.at[df.index[-1], key] = (round(k_value,1), round(d_value,1), round(rsv,1))
        else:
            df.at[df.index[-1], key] = (50, 50, 0)

    return

def indicator_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """
    計算 DataFrame 的移動平均收斂發散指標 (MACD)。

    Args:
        df (pd.DataFrame): 包含 'close' 欄位的 DataFrame。
        fast_period (int): 計算快線 EMA 的週期，預設為 12。
        slow_period (int): 計算慢線 EMA 的週期，預設為 26。
        signal_period (int): 計算 MACD 線 EMA 的週期，預設為 9。
    """
    key = MACD_PREFIX + str(fast_period) + '_' + str(slow_period) + '_' + str(signal_period)

    if key not in df.columns:  # 首次計算
        fast_ema = df['close'].ewm(span=fast_period, adjust=False).mean()
        slow_ema = df['close'].ewm(span=slow_period, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        hist = macd_line - signal_line

        df[key] = list(zip(macd_line.round(1), signal_line.round(1), hist.round(1)))

    else:  # 後續計算
        if len(df) >= slow_period:  # 確保有足夠的資料計算慢線 EMA
            fast_ema = (df['close'].iloc[-1] * (2 / (fast_period + 1)) + df['close'].iloc[-2] * (1 - (2 / (fast_period + 1)))) if len(df) > 1 else df['close'].iloc[-1]
            slow_ema = (df['close'].iloc[-1] * (2 / (slow_period + 1)) + df['close'].iloc[-2] * (1 - (2 / (slow_period + 1)))) if len(df) > 1 else df['close'].iloc[-1]
            macd_line = fast_ema - slow_ema
            signal_line = (macd_line * (2 / (signal_period + 1)) + df[key].iloc[-2][1] * (1 - (2 / (signal_period + 1)))) if len(df) >= signal_period else macd_line
            hist = macd_line - signal_line

            df.at[df.index[-1], key] = (macd_line.round(1), signal_line.round(1), hist.round(1))
        else:
            df.at[df.index[-1], key] = (0, 0, 0)
    return

def indicator_bollingsband(df, period=20, std_dev=2):
    """
    計算 DataFrame 的布林通道 (基于 'close' 欄位)。

    Args:
        df (pd.DataFrame): 包含收盤價 ('close') 的 DataFrame。
        period (int): 計算移動平均線的週期，預設為 20。
        std_dev (int): 標準差的倍數，用於計算上下軌，預設為 2。
    """
    key = BB_PREFIX + str(period)

    mid_band = df['close'].rolling(window=period, min_periods=1).mean().astype(int)
    std = df['close'].rolling(window=period, min_periods=1).std().astype(float)
    upper_band = mid_band + std_dev * std
    lower_band = mid_band - std_dev * std

    df[key] = list(zip(mid_band.round(1), upper_band.round(1), lower_band.round(1)))

    return
