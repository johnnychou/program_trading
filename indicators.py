import numpy as np
import pandas as pd
from constant import *
from conf import *

def indicators_calculation_all(df): # 直接在df新增欄位
    indicator_ma(df, MA_PERIOD)
    indicator_ema(df, EMA_PERIOD)
    indicator_ema(df, EMA2_PERIOD)
    indicator_atr(df, ATR_PERIOD)
    indicator_rsi(df, RSI_PERIOD)
    indicator_kd(df, KD_PERIOD[0], KD_PERIOD[1], KD_PERIOD[2])
    indicator_macd(df, MACD_PERIOD[0], MACD_PERIOD[1], MACD_PERIOD[2])
    indicator_bollingsband(df, BB_PERIOD[0], BB_PERIOD[1])
    indicator_vwap_cumulative(df)
    return

def indicator_ma(df, period):
    """
    計算 DataFrame 中指定欄位的簡單移動平均線 (SMA)。
    """
    key = MA_PREFIX + str(period)
    df[key] = df['close'].rolling(window=period, min_periods=1).mean().round().astype(int)
    return

def indicator_ema(df, period):
    """
    計算 DataFrame 中 'close' 欄位的指數移動平均線 (EMA)，
    處理首次計算與增量更新，風格簡潔。優先嘗試增量更新最後一行。

    Args:
        df (pd.DataFrame): 要計算的 DataFrame (會被原地修改)。
        period (int): EMA 的週期。

    Returns:
        None: DataFrame 直接被修改。
    """
    key = EMA_PREFIX + str(period)
    source_column = 'close' # 在範例中固定為 'close'

    # --- 基本檢查 ---
    if source_column not in df.columns:
        print(f"錯誤：來源欄位 '{source_column}' 不存在。")
        return
    if not isinstance(period, int) or period <= 0:
        print(f"錯誤：週期 '{period}' 必須是正整數。")
        return
    if df.empty:
        if key not in df.columns: df[key] = np.nan # 確保空 DataFrame 也有欄位
        return # 不計算空的 DataFrame

    # --- 判斷是否能進行增量更新 (只更新最後一筆) ---
    can_incrementally_update = False
    if key in df.columns and len(df) > 1:
        try:
            # 檢查倒數第二個 EMA 值是否有效 (非 NaN 或 None)
            prev_ema_value = df[key].iloc[-2]
            if pd.notna(prev_ema_value):
                # 檢查最後一個收盤價是否有效
                if pd.notna(df[source_column].iloc[-1]):
                    # 檢查最後一個 EMA 值是否需要計算 (是 NaN)
                    # 如果最後一個 EMA 值已經存在，我們這裡選擇不重新計算它
                    # 如果你希望即使存在也強制用前值重算最後一筆，移除下面這行檢查
                    if pd.isna(df[key].iloc[-1]):
                        can_incrementally_update = True
        except IndexError:
            # 如果 df 長度剛好是 1 或 0，iloc[-2] 會出錯，len(df) > 1 應避免此情況
            pass
        except Exception as e:
            # 捕捉其他可能的錯誤
            print(f"檢查增量更新條件時發生錯誤: {e}")


    # --- 執行計算 ---
    if can_incrementally_update:
        # --- 增量更新 (僅計算最後一行) ---
        prev_ema = df[key].iloc[-2]
        close_price = df[source_column].iloc[-1]
        multiplier = 2 / (period + 1)
        ema = multiplier * (close_price - prev_ema) + prev_ema
        # 使用 .loc 更新，更安全
        df.loc[df.index[-1], key] = int(round(ema))
        # print(f"對 '{key}' 執行了增量更新。") # 除錯訊息

    else:
        # --- 完整計算 (首次計算、數據太短、前值無效、或最後值已存在) ---
        # 只有在 EMA 欄位不存在，或者存在但最後值為 NaN 且無法增量更新時，才執行完整重算
        recalculate_all = False
        if key not in df.columns:
            recalculate_all = True
            # print(f"欄位 '{key}' 不存在，執行完整計算。") # 除錯訊息
        elif pd.isna(df[key].iloc[-1]): # 如果最後一行是 NaN 且無法增量更新
             recalculate_all = True
             # print(f"'{key}' 最後值為 NaN 且無法增量更新，執行完整計算。") # 除錯訊息
        # else:
             # print(f"'{key}' 已是最新或無法增量更新，不執行完整計算。") # 除錯訊息


        if recalculate_all:
            # print(f"執行 '{key}' 的首次或完整計算。") # 除錯訊息
            df[key] = df[source_column].ewm(span=period, adjust=False, ignore_na=True).mean().round().astype(int)

    # 最後確保欄位存在，即使 DataFrame 為空或沒有進行任何計算
    if key not in df.columns:
        df[key] = np.nan

    return # DataFrame 已被原地修改

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
        # 初次計算：從頭計算 EMA 與 MACD
        fast_ema_series = df['close'].ewm(span=fast_period, adjust=False).mean()
        slow_ema_series = df['close'].ewm(span=slow_period, adjust=False).mean()
        macd_line = fast_ema_series - slow_ema_series
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        hist = macd_line - signal_line

        df[key] = list(zip(
            macd_line.round(1),
            signal_line.round(1),
            hist.round(1)
        ))

        # 儲存最後一筆 EMA 狀態到 Macd_state
        Macd_state['fast_ema'] = fast_ema_series.iloc[-1]
        Macd_state['slow_ema'] = slow_ema_series.iloc[-1]
        Macd_state['signal'] = signal_line.iloc[-1]
        return

    # 後續增量更新
    close_now = df['close'].iloc[-1]

    fast_ema = alpha_fast * close_now + (1 - alpha_fast) * Macd_state['fast_ema']
    slow_ema = alpha_slow * close_now + (1 - alpha_slow) * Macd_state['slow_ema']
    macd_line = fast_ema - slow_ema
    signal_line = alpha_signal * macd_line + (1 - alpha_signal) * Macd_state['signal']
    hist = macd_line - signal_line

    df.at[df.index[-1], key] = (
        round(macd_line, 1),
        round(signal_line, 1),
        round(hist, 1)
    )

    # 更新狀態
    Macd_state['fast_ema'] = fast_ema
    Macd_state['slow_ema'] = slow_ema
    Macd_state['signal'] = signal_line
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

VWAP_state = {
    'cumulative_pv': 0.0,
    'cumulative_volume': 0.0,
}
def indicator_vwap_cumulative(df):
    """
    使用 VWAP_state 儲存累積 PV 與 Volume，只更新 VWAP 欄位。

    Args:
        df (pd.DataFrame): 包含至少 ['high', 'low', 'close', 'volume'] 欄位的 DataFrame。
        VWAP_state (dict): 包含 'cumulative_pv' 與 'cumulative_volume' 的狀態字典。
    """
    global VWAP_state
    required_cols = ['high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_cols):
        print(f"錯誤：DataFrame 缺少必要欄位: {required_cols}")
        return

    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
    tp = (df['high'] + df['low'] + df['close']) / 3
    pv = tp * df['volume']

    if 'VWAP' not in df.columns:
        df['VWAP'] = np.nan

    start_loc = df['VWAP'].last_valid_index()
    if start_loc is None:
        start_iloc = 0
    else:
        start_iloc = df.index.get_loc(start_loc) + 1

    if start_iloc >= len(df):
        return  # 無新資料可更新

    indices = df.iloc[start_iloc:].index
    pv_to_add = pv.iloc[start_iloc:]
    volume_to_add = df['volume'].iloc[start_iloc:]

    cumulative_pv = pv_to_add.cumsum() + VWAP_state['cumulative_pv']
    cumulative_volume = volume_to_add.cumsum() + VWAP_state['cumulative_volume']

    vwap_series = cumulative_pv / cumulative_volume
    df.loc[indices, 'VWAP'] = round(vwap_series)

    VWAP_state['cumulative_pv'] = cumulative_pv.iloc[-1]
    VWAP_state['cumulative_volume'] = cumulative_volume.iloc[-1]

    df['VWAP'] = df['VWAP'].ffill()

    if pd.isna(df.loc[df.index[0], 'VWAP']):
        first_valid_idx = df['volume'][df['volume'] > 0].first_valid_index()
        if first_valid_idx is not None:
            df['VWAP'] = df['VWAP'].fillna(tp[first_valid_idx])
        else:
            df['VWAP'] = df['VWAP'].fillna(0)

    return

def reset_vwap_if_needed(current_market):
    """
    根據市場類型 (日盤、夜盤或非交易時段)，檢查是否需要重置 VWAP_state。
    """
    global VWAP_state

    # 檢查是否處於非交易時段並且需要重置 VWAP_state
    if current_market == '-1':
        return VWAP_state  # 不重置，處於非交易時段

    if 'last_market' not in VWAP_state:
        VWAP_state['last_market'] = current_market
        return VWAP_state

    # 根據市場類型判斷是否需要重置
    if current_market == '0':  # 日盤
        if VWAP_state.get('last_market', '') != '0':  # 如果之前是夜盤或非交易時段
            VWAP_state = reset_vwap_state()
            VWAP_state['last_market'] = '0'
    elif current_market == '1':  # 夜盤
        if VWAP_state.get('last_market', '') != '1':  # 如果之前是日盤或非交易時段
            VWAP_state = reset_vwap_state()
            VWAP_state['last_market'] = '1'

    return VWAP_state

def reset_vwap_state():
    """
    建立新的 VWAP 狀態，通常在換日或盤別切換時使用。
    """
    return {
        'cumulative_pv': 0.0,
        'cumulative_volume': 0.0,
    }