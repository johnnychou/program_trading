import multiprocessing
import os
import csv
import fubon
import time
import datetime
import pandas as pd
from datetime import timedelta

import twse
import main as m
from conf import *
from constant import *

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
CSV_INPUT_DATA = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered\Daily_2025_04_14.csv'
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
candles_30m = twse.CandleCollector(period=timedelta(minutes=30))
df_1m = pd.DataFrame()
df_5m = pd.DataFrame()
df_15m = pd.DataFrame()
df_30m = pd.DataFrame()

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
            Sell_record.append([price, lastprice, open_time, close_time])
            Total_profit += profit
            Trade_times += 1
    elif sig == -1:
        while Buy_at:
            price, open_time = Buy_at.pop(0)
            profit += (lastprice - price)*PT_PRICE
            Buy_profit.append(profit)
            Buy_record.append([price, lastprice, open_time, close_time])
            Total_profit += profit
            Trade_times += 1
    return

def fake_close_all_position(lastprice, now):
    if Buy_at:
        fake_close_position(-1, lastprice, now)
    if Sell_at:
        fake_close_position(1, lastprice, now)
    return

def export_trade_log(fullpath):
    base_filename = os.path.splitext(os.path.basename(fullpath))[0]
    output_file = os.path.join(CSV_OUTPUT_PATH, f"{base_filename}_result.csv")

    records = []

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # 寫入統計資訊
        writer.writerow(['Total_profit', Total_profit])
        writer.writerow(['Real_profit', Total_profit - Trade_times*150])
        writer.writerow(['Trade_times', Trade_times, Trade_times*150])
        writer.writerow(['Buy_profit', sum(Buy_profit) ,Buy_profit])
        writer.writerow(['Sell_profit', sum(Sell_profit), Sell_profit])
        writer.writerow([])  # 空行分隔


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
    if 'entry_time' in df_record.columns:
        df_record = df_record.sort_values(by='entry_time')
    df_record.to_csv(output_file, index=False, encoding='utf-8-sig', mode='a') # mode -> append
    print(f"交易紀錄已儲存到: {output_file}")

def is_day_session(now):
    return datetime.time(8, 45) <= now.time() <= datetime.time(13, 45)

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

def check_atr_trailing_stop(last_price, now):
    position = 0
    if Buy_at:
        position = 1
        entry_price = Buy_at[0][0]
    elif Sell_at:
        position = -1
        entry_price = Sell_at[0][0]
    else:
        return
    
    df = df_1m if is_day_session(now) else df_5m
    if len(df) < 20:
        return

    atr_val = df.iloc[-1][ATR_KEY]
    if atr_val is None:
        return

    stop_distance = atr_val * 1.5  # 可調整倍數

    if position > 0 and last_price < entry_price - stop_distance:
        fake_close_position(-1, last_price, now)
    elif position < 0 and last_price > entry_price + stop_distance:
        fake_close_position(1, last_price, now)

def multi_timeframe_strategy(now, df):
    global df_1m, df_5m, df_15m, Last_price

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

        main_row = main_df.iloc[-1]
        pre_row = main_df.iloc[-2]
        confirm_row = confirm_df.iloc[-1]

        # === 主訊號：RSI 低於30為多訊，高於70為空訊 ===
        rsi_val = main_row[RSI_KEY]
        pre_rsi = pre_row[RSI_KEY]
        signal = None
        if pre_rsi < 30 and rsi_val >= 30:
            signal = 'long'
        elif pre_rsi > 70 and rsi_val <= 70:
            signal = 'short'

        if signal is None:
            return

        # === 確認訊號：雙週期 EMA 趨勢 + 布林通道位置 ===
        ema_short = confirm_row[EMA_KEY]
        ema_long = confirm_row[EMA2_KEY]
        trend = 'up' if ema_short > ema_long else 'down'

        bb_mid, bb_high, bb_low = confirm_row[BB_KEY]

        confirm = False
        if signal == 'long' and trend == 'up' and Last_price < bb_low:
            confirm = True
        elif signal == 'short' and trend == 'down' and Last_price > bb_high:
            confirm = True

        # === 若訊號與確認成立，進場 ===
        if confirm:
            if signal == 'long':
                fake_open_position(1, Last_price, now)
                print(df.iloc[-2:])
            elif signal == 'short':
                fake_open_position(-1, Last_price, now)
                print(df.iloc[-2:])

        # === 跟隨止盈：若反轉則出場 ===
        # 取得持倉
        if Buy_at:
            entry_price, entry_time = Buy_at[-1]
            atr = confirm_row[ATR_KEY]
            stop_price = max(entry_price + atr * 2, Last_price - atr * 1.5)
            if Last_price < stop_price:
                fake_close_position(1, Last_price, now)
                print(df.iloc[-2:])

        if Sell_at:
            entry_price, entry_time = Sell_at[-1]
            atr = confirm_row[ATR_KEY]
            stop_price = min(entry_price - atr * 2, Last_price + atr * 1.5)
            if Last_price > stop_price:
                fake_close_position(-1, Last_price, now)
                print(df.iloc[-2:])


def run_test(fullpath, market='main'):
    global df_1m, df_5m, df_15m, Last_price
    global candles_1m, candles_5m, candles_15m
    twse_data = twse.TWSE_CSV(fullpath)

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

        if not m.is_trading_time(market, now):
            continue

        if m.before_end_of_market(market, now):
            fake_close_all_position(Last_price, now)
            continue

        # 即時 ATR 跟隨止盈
        check_atr_trailing_stop(Last_price, now)

        # === 根據盤別主K線判斷時機呼叫策略 ===
        if market != 'night' and candle_1:
            multi_timeframe_strategy(now, df_1m)
        elif market != 'day' and candle_5:
            multi_timeframe_strategy(now, df_5m)

        # 放最後以讓上面k線收完
        if data is None:
            break

    print('======================================================')
    print(f'Total_profit: {Total_profit}, Real_profit: {Total_profit-Trade_times*150}')
    print(f'Trade_times: {Trade_times}, Costs: {Trade_times*150}')
    print(f'Buy_profit: {sum(Buy_profit)}')
    print(f'Sell_profit: {sum(Sell_profit)}')

    export_trade_log(fullpath)

    print(f'Buy_record:')
    for record in Buy_record:
        record[2] = record[2].strftime('%H:%M:%S')
        record[3] = record[3].strftime('%H:%M:%S')
        print(record)
    print(f'Sell_record:')
    for record in Sell_record:
        record[2] = record[2].strftime('%H:%M:%S')
        record[3] = record[3].strftime('%H:%M:%S')
        print(record)
    print('======================================================')


if __name__ == '__main__':
    run_test(CSV_INPUT_DATA)
    print('===========================')
    print(df_1m)
    print('===========================')
    print(df_5m)
    print('===========================')
    print(df_15m)
