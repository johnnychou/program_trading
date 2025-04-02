import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time
import multiprocessing
import pandas as pd

import twse
import fubon
import indicators

def create_sample_dataframe(total_minutes=30, initial_price=20000, price_range=50):
    """
    創建一個包含指定分鐘數的 1 分鐘 K 線模擬 DataFrame。

    Args:
        total_minutes (int): 要生成的 K 線總分鐘數。
        initial_price (int): 第一根 K 線的開盤價，預設為 20000。
        price_range (int): 價格波動範圍，控制 high/low 與 open/close 的距離，預設為 50。

    Returns:
        pd.DataFrame: 包含模擬 K 線資料的 DataFrame。
    """

    start_time = pd.to_datetime('2024-01-01 00:00:00')
    time_series = pd.date_range(start=start_time, periods=total_minutes, freq='1min')

    open_prices = np.zeros(total_minutes, dtype=int)
    close_prices = np.zeros(total_minutes, dtype=int)
    high_prices = np.zeros(total_minutes, dtype=int)
    low_prices = np.zeros(total_minutes, dtype=int)

    open_prices[0] = initial_price
    for i in range(total_minutes):
        # 模擬價格波動
        price_change = np.random.randint(-price_range // 2, price_range // 2 + 1)
        close_prices[i] = open_prices[i - 1] + price_change if i > 0 else initial_price + price_change

        # 確保 high 和 low 允許超出 open 和 close
        high_offset = np.random.randint(0, price_range // 5 + 1)  # 限制偏移量
        low_offset = np.random.randint(0, price_range // 5 + 1)

        high_prices[i] = max(open_prices[i], close_prices[i]) + high_offset
        low_prices[i] = min(open_prices[i], close_prices[i]) - low_offset

        if i < total_minutes - 1:
            open_prices[i + 1] = close_prices[i] + np.random.randint(-price_range // 5, price_range // 5 + 1)

    data = {
        'open': open_prices,
        'close': close_prices,
        'high': high_prices,
        'low': low_prices,
        'volume': np.random.randint(1000, 2000, size=total_minutes),
        'time': time_series
    }
    df = pd.DataFrame(data)

    # 計算 body
    df['body'] = np.select(
        [df['close'] > df['open'], df['close'] < df['open'], df['close'] == df['open']],
        [1, -1, 0]
    )

    return df[['body', 'open', 'close', 'high', 'low', 'volume', 'time']]

if __name__ == '__main__':

    test_df = create_sample_dataframe(total_minutes=30)
    indicators.indicator_ma(test_df, 10)
    indicators.indicator_ema(test_df, 5)
    indicators.indicator_atr(test_df, 14)
    indicators.indicator_rsi(test_df, 10)
    indicators.indicator_kd(test_df, 9)
    indicators.indicator_macd(test_df)
    indicators.indicator_bollingsband(test_df)
    print(test_df)

    new_data = create_sample_dataframe(total_minutes=1)
    new_df = pd.DataFrame(new_data)
    test_df = pd.concat([test_df, new_df], ignore_index=True)

    print('================================================')
    print('================================================')
    print(test_df)
    print('================================================')
    print('================================================')

    indicators.indicator_ma(test_df, 10)
    indicators.indicator_ema(test_df, 5)
    indicators.indicator_atr(test_df, 14)
    indicators.indicator_rsi(test_df, 10)
    indicators.indicator_kd(test_df, 9)
    indicators.indicator_macd(test_df)
    indicators.indicator_bollingsband(test_df, 20)
    print(test_df)

    a = 123.45
    print(a.int())

