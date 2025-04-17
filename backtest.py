import multiprocessing
import os
import csv
import fubon
import time
import datetime
import pandas as pd
from datetime import timedelta
from datetime import time

import twse
import main as m
from conf import *

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
CSV_INPUT_DATA = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered\Daily_2025_04_01.csv'
PT_PRICE = 200

Fubon_account = None
Userinput_Market = None
Userinput_Direction = None
Userinput_Product = None
Userinput_OrderAmount = 0
OrderAmount = 0

Buy_at = []
Buy_profit = []
Buy_record = []

Sell_at = []
Sell_profit = []
Sell_record = []

Trade_times = 0
Last_price = 0
Total_profit = 0

candles_1m = twse.CandleCollector(period=timedelta(minutes=1))
candles_5m = twse.CandleCollector(period=timedelta(minutes=5))
candles_15m = twse.CandleCollector(period=timedelta(minutes=15))
df_1m = pd.DataFrame()
df_5m = pd.DataFrame()
df_15m = pd.DataFrame()

def fake_open_position(sig, lastprice, now): # 1=buy, -1=sell
    global Buy_at, Sell_at, Trade_times
    positions = len(Buy_at) + len(Sell_at)
    if positions:
        return
    if sig == 1:
        Buy_at.append((lastprice, now))
        Trade_times += 1
    elif sig == -1:
        Sell_at.append((lastprice, now))
        Trade_times += 1
    return

def fake_close_position(sig, lastprice, now): # 1=close_sell_position, -1=close_buy_position
    global Buy_at, Sell_at, Total_profit, Trade_times
    global Sell_profit, Sell_record, Buy_profit, Buy_record
    positions = len(Buy_at) + len(Sell_at)
    profit = 0
    if not positions:
        return
    if (Buy_at and sig == 1) or (Sell_at and sig == -1):
        return

    close_time = now

    if sig == 1:
        while Sell_at:
            price, open_time = Sell_at.pop(0)
            profit += (price - lastprice)*PT_PRICE
            Sell_profit.append(profit)
            Sell_record.append((price, lastprice, open_time, close_time))
            Total_profit += profit
            Trade_times += 1
    elif sig == -1:
        while Buy_at:
            price, open_time = Buy_at.pop(0)
            profit += (lastprice - price)*PT_PRICE
            Buy_profit.append(profit)
            Buy_record.append((price, lastprice, open_time, close_time))
            Total_profit += profit
            Trade_times += 1
    return

def export_trade_log():
    base_filename = os.path.splitext(os.path.basename(CSV_INPUT_DATA))[0]
    output_file = os.path.join(CSV_OUTPUT_PATH, f"{base_filename}_result.csv")

    records = []

    for buy, sell, entry_time, exit_time in Buy_record:
        records.append({
            'type': 'Buy',
            'entry': buy,
            'exit': sell,
            'profit': (sell - buy) * PT_PRICE,
            'entry_time': entry_time,
            'exit_time': exit_time
        })

    for sell, buy, entry_time, exit_time in Sell_record:
        records.append({
            'type': 'Sell',
            'entry': sell,
            'exit': buy,
            'profit': (sell - buy) * PT_PRICE,
            'entry_time': entry_time,
            'exit_time': exit_time
        })

    df_record = pd.DataFrame(records)
    df_record.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n交易紀錄已儲存到: {output_file}")

def is_day_session(now):
    return time(8, 45) <= now.time() <= time(13, 45)

def detect_kbar_momentum(row):
    body = abs(row['close'] - row['open'])
    upper_shadow = row['high'] - max(row['close'], row['open'])
    lower_shadow = min(row['close'], row['open']) - row['low']

    if body > upper_shadow * 2 and body > lower_shadow * 2:
        if row['close'] > row['open']:
            return 'long'
        elif row['close'] < row['open']:
            return 'short'
    return None

def get_ema_trend(df, period=20):
    if len(df) < period + 2:
        return None
    ema = df['close'].ewm(span=period, adjust=False).mean()
    slope = ema.iloc[-1] - ema.iloc[-2]
    return 'up' if slope > 0 else 'down'

def multi_timeframe_strategy(now):
    global df_1m, df_5m, df_15m
    if not df_1m.empty and not df_5m.empty and not df_15m.empty:
        current_time = df_1m.iloc[-1]['end_time']
        if is_day_session(current_time):
            main_df = df_1m
            confirm_df = df_5m
        else:
            main_df = df_5m
            confirm_df = df_15m

        if len(main_df) < 1 or len(confirm_df) < 2:
            return

        signal = detect_kbar_momentum(main_df.iloc[-1])
        if signal is None:
            return

        confirm_signal = detect_kbar_momentum(confirm_df.iloc[-1])
        confirm_trend = get_ema_trend(confirm_df, period=20)

        # 兩種信號皆出現，或是主信號方向與確認K線的趨勢一致，才進場
        if signal == 'long' and (confirm_signal == 'long' or confirm_trend == 'up'):
            fake_open_position(1, Last_price, now)
        elif signal == 'short' and (confirm_signal == 'short' or confirm_trend == 'down'):
            fake_open_position(-1, Last_price, now)

        # 趨勢反轉時平倉（可自行更換為其他風控條件）
        if signal == 'long' and confirm_trend == 'down':
            fake_close_position(-1, Last_price, now)
        elif signal == 'short' and confirm_trend == 'up':
            fake_close_position(1, Last_price, now)


def run_test(filename):
    global df_1m, df_5m, df_15m, Last_price
    global candles_1m, candles_5m, candles_15m
    twse_data = twse.TWSE_CSV(filename)

    while True:
        data = twse_data.get_row_from_csv()

        if data:
            now = data['time']
            Last_price = data['price']

        candle_1 = candles_1m.get_candles(data)
        if candle_1:
            new_row = pd.DataFrame([candle_1])
            df_1m = pd.concat([df_1m, new_row], ignore_index=True)
            m.indicators_calculation(df_1m)
            multi_timeframe_strategy(now.strftime('%Y/%m/%d %H:%M:%S'))

        candle_5 = candles_5m.get_candles(data)
        if candle_5:
            new_row = pd.DataFrame([candle_5])
            df_5m = pd.concat([df_5m, new_row], ignore_index=True)
            m.indicators_calculation(df_5m)

        candle_15 = candles_15m.get_candles(data)
        if candle_15:
            new_row = pd.DataFrame([candle_15])
            df_15m = pd.concat([df_15m, new_row], ignore_index=True)
            m.indicators_calculation(df_15m)

        if data is None:
            break

    print('===========================')
    print(f'Total_profit: {Total_profit}, Real_profit: {Total_profit-Trade_times*150}')
    print(f'Trade_times: {Trade_times}, Costs: {Trade_times*150}')
    print(f'Buy_profit: {Buy_profit}')
    print(f'Sell_profit: {Sell_profit}')
    print('===========================')
    print(f'Buy_record: {Buy_record}')
    print(f'Sell_record: {Sell_record}')
    export_trade_log()


if __name__ == '__main__':
    run_test(CSV_INPUT_DATA)
