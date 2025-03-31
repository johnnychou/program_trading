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
    if key not in df.columns:  # 首次計算
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
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        rsv = ((df['close'] - low_n) / (high_n - low_n) * 100).round(1).fillna(50)
        k_values = rsv.rolling(window=k).mean().round(1).fillna(50)
        d_values = k_values.rolling(window=d).mean().round(1).fillna(50)

        df[key] = list(zip(k_values, d_values, rsv))
    else:  # 後續計算
        if len(df) >= n:
            low_n = df['low'].iloc[-n:].min()
            high_n = df['high'].iloc[-n:].max()
            rsv = (df['close'].iloc[-1] - low_n) / (high_n - low_n) * 100

            k_value = df[key].iloc[-k:].apply(lambda x: x[0]).mean()
            d_value = df[key].iloc[-d:].apply(lambda x: x[1]).mean()

            df.loc[df.index[-1], key] = [k_value, d_value, rsv]
        else:
            df.loc[df.index[-1], key] = [50, 50, 0]
    return

def indicator_rsi(df, period=10):
    key = RSI_PREFIX + str(period)

    if key not in df.columns:
        delta = df['close'].diff()
        up = delta.where(delta > 0, 0)
        down = -delta.where(delta < 0, 0)

        avg_gain = up.rolling(window=period).mean().fillna(0)
        avg_loss = down.rolling(window=period).mean().fillna(0)

        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = (100 - (100 / (1 + rs)))

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

            rs = avg_gain / avg_loss.replace(0, 1e-10)
            rsi = 100 - (100 / (1 + rs))

            df.loc[df.index[-1], key] = rsi.round(1)
        else:
            df.loc[df.index[-1], key] = 0
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
            signal_line = (macd_line * (2 / (signal_period + 1)) + df[key].iloc[-1][1] * (1 - (2 / (signal_period + 1)))) if len(df) >= signal_period else macd_line
            hist = macd_line - signal_line

            df.loc[df.index[-1], key] = [macd_line.round(1), signal_line.round(1), hist.round(1)]
        else:
            # 資料不足時的處理
            df.loc[df.index[-1], key] = [0, 0, 0]
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

    if key not in df.columns:
        mid_band = df['close'].rolling(window=period).mean().fillna(0)
        std = df['close'].rolling(window=period).std().fillna(0)
        upper_band = mid_band + std_dev * std
        lower_band = mid_band - std_dev * std

        df[key] = list(zip(mid_band.round(1), upper_band.round(1), lower_band.round(1)))

    else:
        if len(df) >= period:
            mid_band = df['close'].rolling(window=period).mean().iloc[-1]
            std = df['close'].rolling(window=period).std().iloc[-1]
            upper_band = mid_band + std_dev * std
            lower_band = mid_band - std_dev * std

            df.loc[df.index[-1], key] = [mid_band.round(1), upper_band.round(1), lower_band.round(1)]
        else:
            df.loc[df.index[-1], key] = [0, 0, 0]
    return
