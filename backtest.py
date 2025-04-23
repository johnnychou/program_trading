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
import indicators as i
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
    if Buy_at or Sell_at:
        return 0
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
    profit = 0
    if not Buy_at and not Sell_at:
        return 0
    if (Buy_at and sig == 1) or\
         (Sell_at and sig == -1):
        return 0

    close_time = now

    if sig == 1:
        while Sell_at:
            price, open_time = Sell_at.pop(0)
            profit += (price - lastprice)*PT_PRICE
            Sell_profit.append(profit)
            Sell_record.append([price, lastprice, open_time, close_time, profit])
            Total_profit += profit
            Trade_times += 1
    elif sig == -1:
        while Buy_at:
            price, open_time = Buy_at.pop(0)
            profit += (lastprice - price)*PT_PRICE
            Buy_profit.append(profit)
            Buy_record.append([price, lastprice, open_time, close_time, profit])
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


    for buy, sell, entry_time, exit_time, profit in Buy_record:
        records.append({
            'type': 'Buy',
            'entry': buy,
            'exit': sell,
            'profit': profit,
            'entry_time': entry_time,
            'exit_time': exit_time
        })

    for sell, buy, entry_time, exit_time, profit in Sell_record:
        records.append({
            'type': 'Sell',
            'entry': sell,
            'exit': buy,
            'profit': profit,
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

Max_profit_pt = 0
def atr_trailing_stop(lastprice, now, df):
    global Max_profit_pt
    if ATR_KEY not in df.columns:
        return 0
    if not (len(Buy_at) + len(Sell_at)):
        return
    
    last_valid_idx = df[ATR_KEY].last_valid_index()
    atr = df.loc[last_valid_idx, ATR_KEY]

    if Buy_at:
        Max_profit_pt = max(lastprice, Buy_at[0][0], Max_profit_pt)
        stop_price = Max_profit_pt - atr * 1.5
        if lastprice <= stop_price:
            fake_close_position(-1, lastprice, now)
            Max_profit_pt = 0
            return stop_price

    elif Sell_at:
        if not Max_profit_pt:
            Max_profit_pt = min(lastprice, Sell_at[0][0])
        else:
            Max_profit_pt = min(lastprice, Sell_at[0][0], Max_profit_pt)
        stop_price = Max_profit_pt + atr * 1.5
        if lastprice >= stop_price:
            fake_close_position(1, lastprice, now)
            Max_profit_pt = 0
            return stop_price

    return 0

def run_test(fullpath, trade_market='main'):
    global df_1m, df_5m, df_15m, Last_price
    global candles_1m, candles_5m, candles_15m
    twse_data = twse.TWSE_CSV(fullpath)
    idicators_1m = i.indicator_calculator()
    idicators_5m = i.indicator_calculator()
    idicators_15m = i.indicator_calculator()
    df_flag = {
        PERIOD_30S: 0,
        PERIOD_1M: 0,
        PERIOD_5M: 0,
        PERIOD_15M: 0,
    }
    
    while True:
        data = twse_data.get_row_from_csv()

        if data:
            now = data['time']
            Last_price = data['price']
            market = data['market']

        candle_1 = candles_1m.get_candles(data)
        if candle_1:
            new_row = pd.DataFrame([candle_1])
            df_1m = pd.concat([df_1m, new_row], ignore_index=True)
            idicators_1m.indicators_calculation_all(df_1m)
            candle_1 = 0

        candle_5 = candles_5m.get_candles(data)
        if candle_5:
            new_row = pd.DataFrame([candle_5])
            df_5m = pd.concat([df_5m, new_row], ignore_index=True)
            idicators_5m.indicators_calculation_all(df_5m)
            candle_5 = 0
            df_flag[PERIOD_5M] = 1

        candle_15 = candles_15m.get_candles(data)
        if candle_15:
            new_row = pd.DataFrame([candle_15])
            df_15m = pd.concat([df_15m, new_row], ignore_index=True)
            idicators_15m.indicators_calculation_all(df_15m)
            candle_15 = 0

        if not m.is_trading_time(trade_market, now):
            continue

        if m.before_end_of_market(trade_market, now):
            fake_close_all_position(Last_price, now)
            continue

        atr_trailing_stop(Last_price, now, df_5m)

        if df_flag[PERIOD_5M]:
            sig = m.trading_strategy(df_5m)
            if sig:
                if not Buy_at and not Sell_at:
                    fake_open_position(sig, Last_price, now)
                else:
                    fake_close_position(sig, Last_price, now)
                    fake_open_position(sig, Last_price, now)
            df_flag[PERIOD_5M] = 0

        idicators_1m.reset_state_if_needed(market)
        idicators_5m.reset_state_if_needed(market)
        idicators_15m.reset_state_if_needed(market)

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
