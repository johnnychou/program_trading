import numpy as np
import pandas as pd
from constant import *

def indicator_ma(df, period):
    """
    計算 DataFrame 中指定欄位的簡單移動平均線 (SMA)。
    """
    key = MA_PREFIX + str(period)
    df[key] = df['close'].rolling(window=period, min_periods=1).mean().round().astype(int)
    return

def indicator_ema(df, period):
    """
    計算 DataFrame 中指定欄位的指數移動平均線 (EMA)，並優化效能。
    """
    key = EMA_PREFIX + str(period)

    if key not in df.columns:
        df[key] = None

    if len(df) > period:
        prev_ema = df[key].iloc[-2]
        close_price = df['close'].iloc[-1]
        multiplier = 2 / (period + 1)
        ema = multiplier * (close_price - prev_ema) + prev_ema
        df.loc[df.index[-1], key] = int(round(ema))
    else:
        df[key] = df['close'].ewm(span=period, adjust=False).mean().round().astype(int)
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

    if key not in df.columns or len(df) < period:
        # 初始化 RSI 全量計算
        delta = df['close'].diff()
        up = delta.where(delta > 0, 0)
        down = -delta.where(delta < 0, 0)

        avg_gain = up.rolling(window=period).mean()
        avg_loss = down.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        df[key] = rsi.fillna(0).round(1)
    else:
        # 增量計算（更新最後一筆 RSI）
        delta = df['close'].diff()
        up = delta.iloc[-1] if delta.iloc[-1] > 0 else 0
        down = -delta.iloc[-1] if delta.iloc[-1] < 0 else 0

        # 使用上一筆 gain/loss 的平均
        prev_avg_gain = df['close'].diff().where(lambda x: x > 0, 0).iloc[-(period+1):-1].mean()
        prev_avg_loss = -df['close'].diff().where(lambda x: x < 0, 0).iloc[-(period+1):-1].mean()

        avg_gain = (prev_avg_gain * (period - 1) + up) / period
        avg_loss = (prev_avg_loss * (period - 1) + down) / period

        rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
        rsi = 100 - (100 / (1 + rs)) if avg_loss != 0 else 100.0

        df.loc[df.index[-1], key] = round(rsi, 1)
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

Macd_state = {}
def indicator_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """
    計算 DataFrame 的移動平均收斂發散指標 (MACD)。

    Args:
        df (pd.DataFrame): 包含 'close' 欄位的 DataFrame。
        fast_period (int): 計算快線 EMA 的週期，預設為 12。
        slow_period (int): 計算慢線 EMA 的週期，預設為 26。
        signal_period (int): 計算 MACD 線 EMA 的週期，預設為 9。
    """
    global Macd_state
    key = MACD_PREFIX + str(fast_period)

    alpha_fast = 2 / (fast_period + 1)
    alpha_slow = 2 / (slow_period + 1)
    alpha_signal = 2 / (signal_period + 1)

    if key not in df.columns:
        df[key] = None

    if len(df) < slow_period:
        df.at[df.index[-1], key] = (0, 0, 0)
        return

    close_now = df['close'].iloc[-1]

    # 初始化：沒狀態就用全量計算一次最後一筆的 EMA，並儲存在 state 中
    if 'fast_ema' not in Macd_state or 'slow_ema' not in Macd_state or 'signal' not in Macd_state:
        fast_ema_series = df['close'].ewm(span=fast_period, adjust=False).mean()
        slow_ema_series = df['close'].ewm(span=slow_period, adjust=False).mean()
        macd_line = fast_ema_series - slow_ema_series
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        hist = macd_line - signal_line

        Macd_state['fast_ema'] = fast_ema_series.iloc[-1]
        Macd_state['slow_ema'] = slow_ema_series.iloc[-1]
        Macd_state['signal'] = signal_line.iloc[-1]

        df.at[df.index[-1], key] = (
            round(macd_line.iloc[-1], 1),
            round(signal_line.iloc[-1], 1),
            round(hist.iloc[-1], 1)
        )
        return

    # 增量更新
    fast_ema = alpha_fast * close_now + (1 - alpha_fast) * Macd_state['fast_ema']
    slow_ema = alpha_slow * close_now + (1 - alpha_slow) * Macd_state['slow_ema']
    macd_line = fast_ema - slow_ema
    signal_line = alpha_signal * macd_line + (1 - alpha_signal) * Macd_state['signal']
    hist = macd_line - signal_line

    # 更新狀態
    Macd_state['fast_ema'] = fast_ema
    Macd_state['slow_ema'] = slow_ema
    Macd_state['signal'] = signal_line

    # 寫入結果欄位
    df.at[df.index[-1], key] = (
        round(macd_line, 1),
        round(signal_line, 1),
        round(hist, 1)
    )
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

    if key not in df.columns: # 初次計算
        mid_band = df['close'].rolling(window=period, min_periods=1).mean().astype(int)
        std = df['close'].rolling(window=period, min_periods=1).std().astype(float)
        upper_band = mid_band + std_dev * std
        lower_band = mid_band - std_dev * std
        df[key] = list(zip(mid_band.round(1), upper_band.round(1), lower_band.round(1)))
    else: # 後續計算
        recent_close = df['close'].iloc[-period:]
        mid = recent_close.mean()
        std = recent_close.std()
        upper = mid + std_dev * std
        lower = mid - std_dev * std

        df.at[df.index[-1], key] = (
            round(mid, 1),
            round(upper, 1),
            round(lower, 1)
        )
    return
