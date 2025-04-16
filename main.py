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
from constant import *
from conf import *

Fubon_account = None
Userinput_Market = None
Userinput_Direction = None
Userinput_Product = None
Userinput_OrderAmount = 0
OrderAmount = 0

Buy_at = []
Sell_at = []
Trade_record = []
Margin = []

Last_price = 0
Profit = 0
Balance = 0
OrderAmount = 0
PT_price = 0

Flag_1m = 0
Flag_5m = 0
Flag_15m = 0

def create_fubon_process(period, product, data_queue, processes):
    """
    創建並啟動 Fubon_data 進程。

    Args:
        period (str): K線週期。
        product (str): 產品代碼。
        data_queue (multiprocessing.Queue): 用於傳輸資料的佇列。
        processes (list): 用於儲存已創建進程的列表。
    """
    fubon_instance = fubon.Fubon_data(period, product, data_queue)
    process = multiprocessing.Process(target=fubon_instance.get_candles)
    process.daemon = True
    process.start()
    processes.append(process)
    return

def create_twse_process(period, product, datasource, data_queue, realtime_candle, processes):
    """
    創建並啟動 TWSE 進程。

    Args:
        period (str): K線週期。
        product (str): 產品代碼。
        datasource (str): 來源為twse或csv。
        data_queue (multiprocessing.Queue): 用於傳輸資料的佇列。
        realtime_candle (multiprocessing.managers.DictProxy): 共享的即時 K 線字典。
        processes (list): 用於儲存已創建進程的列表。
    """
    twse_instance = twse.TWSE(period, product, datasource, data_queue, realtime_candle)
    process = multiprocessing.Process(target=twse_instance.get_candles)
    process.daemon = True
    process.start()
    processes.append(process)
    return

def user_input_settings():
    global Userinput_Market, Userinput_Direction, Userinput_Product, Userinput_OrderAmount, PT_price

    Userinput_Market = input('Trading time day/night/main/all: ').lower()
    while Userinput_Market not in TRADE_MARKET_SET:
        print('Error, please input legal value.')
        Userinput_Market = input('Trading time day/night/main/all: ').lower()

    Userinput_Direction = input('Position choose buy/sell/auto: ').lower()
    while Userinput_Direction not in TRADE_DIRECTION_SET:
        print('Error, please input legal value.')
        Userinput_Direction = input('Position choose buy/sell/auto: ').lower()

    Userinput_Product = input('Product choose TXF/MXF/TMF: ').upper()
    while Userinput_Product not in TRADE_PRODUCT_SET:
        print('Error, please input legal value.')
        Userinput_Product = input('Product choose TXF/MXF/TMF: ').upper()

    if Userinput_Product == 'TXF':
        PT_price = 200
    elif Userinput_Product == 'MXF':
        PT_price = 50
    elif Userinput_Product == 'TMF':
        PT_price = 10

    while True:
        try:
            Userinput_OrderAmount = int(input('Order amount 1~3: '))
            if Userinput_OrderAmount == -1:
                break
            while Userinput_OrderAmount not in range(1, 4):
                print('Error, please input integer 1~3.')
                Userinput_OrderAmount = int(input('Order amount 1~3: '))
            break
        except:
            print('Error, please input integer 1~3.')

    return

def indicators_calculation(df):
    indicators.indicator_ma(df, MA_PERIOD)
    indicators.indicator_ema(df, EMA_PERIOD)
    indicators.indicator_ema(df, EMA2_PERIOD)
    indicators.indicator_atr(df, ATR_PERIOD)
    indicators.indicator_rsi(df, RSI_PERIOD)
    indicators.indicator_kd(df, KD_PERIOD[0], KD_PERIOD[1], KD_PERIOD[2])
    indicators.indicator_macd(df, MACD_PERIOD[0], MACD_PERIOD[1], MACD_PERIOD[2])
    indicators.indicator_bollingsband(df, BB_PERIOD[0], BB_PERIOD[1])
    return df

def show_realtime(realtime_candle):
    global Last_price
    if 'lastprice' in realtime_candle:
        Last_price = realtime_candle['lastprice']
    print(f'lastprice: {Last_price}')
    print('====================================================================')
    print(realtime_candle)
    os.system('cls')
    return

def show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    global Last_price
    if 'lastprice' in realtime_candle:
        Last_price = realtime_candle['lastprice']
    os.system('cls')
    print(f'lastprice: {Last_price}')
    print('==================================')
    print(realtime_candle)
    print('===30s============================')
    print(f"{df_twse_30s[-10:]}")
    print('===1m=============================')
    print(f"{df_fubon_1m[-10:]}")
    print('===5m=============================')
    print(f"{df_fubon_5m[-10:]}")
    print('===15m============================')
    print(f"{df_fubon_15m[-10:]}")    
    return

def show_user_settings():
    print(f'Product: {Userinput_Product}/{OrderAmount},\
            Market: {Userinput_Market},\
            Direction: {Userinput_Direction}')
    print('====================================================================')
    return

def is_market_time(market_hours, now):
    start_str, end_str = market_hours
    start_time = datetime.datetime.strptime(start_str, "%H:%M:%S").time()
    end_time = datetime.datetime.strptime(end_str, "%H:%M:%S").time()
    now_time = now.time()

    if end_time < start_time:  # 處理跨日
        return start_time <= now_time or now_time <= end_time
    else:
        return start_time <= now_time <= end_time

def is_trading_time(now):
    if Userinput_Market == 'day' and is_market_time(DAY_MARKET, now):
        return True
    elif Userinput_Market == 'night' and is_market_time(NIGHT_MARKET, now):
        return True
    elif Userinput_Market == 'main' and (is_market_time(DAY_MARKET, now) or is_market_time(AMER_MARKET, now)):
        return True
    elif Userinput_Market == 'all' and (is_market_time(DAY_MARKET, now) or is_market_time(NIGHT_MARKET, now)):
        return True
    return False

def force_close_position(now):
    """判斷是否應該在收盤前一分鐘平倉"""
    now_str = now.strftime("%H:%M:%S")
    if Userinput_Market == 'day' and now_str == CLOSE_POSITION_TIME[0]:
        return True
    elif Userinput_Market == 'night' and now_str == CLOSE_POSITION_TIME[1]:
        return True
    elif Userinput_Market == 'main' and now_str in (CLOSE_POSITION_TIME[0], CLOSE_POSITION_TIME[2]) and is_trading_time(now):
        return True
    elif Userinput_Market == 'all' and now_str in (CLOSE_POSITION_TIME[0], CLOSE_POSITION_TIME[1]) and is_trading_time(now):
        return True
    else:
        return False

def show_account_info():
    position = ''
    profit = 0
    if Buy_at:
        position = f'Buy: {Buy_at}'
        if Last_price:
            profit = (Last_price - Buy_at[0])*PT_price*OrderAmount
    elif Sell_at:
        position = f'Sell: {Sell_at}'
        if Last_price:
            profit = (Sell_at[0] - Last_price)*PT_price*OrderAmount

    print(f'Position: {position}, Profit: {profit}')
    print('====================================================================')
    return

def get_max_lots():
    max_lots = 0
    if Balance and Margin[0]:
        max_lots = Balance // (Margin[0]*MAX_LOT_RATE)
        #print(f'max_lots: {max_lots}')
    return max_lots

def update_account_info(account):
    global Buy_at, Sell_at, Balance, Margin, OrderAmount
    Buy_at, Sell_at = account.update_position_holded()
    Balance, Margin = account.update_margin_equity()
    if Userinput_OrderAmount == -1:
        OrderAmount = get_max_lots()
    else:
        OrderAmount = Userinput_OrderAmount
    return

def open_position(account, sig):
    if (Userinput_Direction == 'buy' and sig == -1) or\
         (Userinput_Direction == 'sell' and sig == 1):
        return 0
    account.send_order(sig, OrderAmount)
    return
    
def close_position(account, sig):
    if not Buy_at and not Sell_at:
        return 0
    if (Buy_at and sig == 1) or\
         (Sell_at and sig == -1):
        return 0
    account.send_order(sig, OrderAmount)
    return

def close_all_position(account):
    if Buy_at:
        close_position(account, -1)
    if Sell_at:
        close_position(account, 1)
    return

def chk_trade_signal(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    if KD_KEY in df_fubon_1m.columns:
        column = df_fubon_1m[KD_KEY]
        if len(column) >= 3:
            print(column.iloc[-1])
            print(column.iloc[-2])
            print(column.iloc[-3])
            #time.sleep(10)
    return

def multi_timeframe_strategy():
    sig = chk_trade_signal(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)
    return

def is_data_ready(now, datas):
    """檢查指定週期資料是否已更新"""
    flag = 0
    total_flag = len(datas)
    for data in datas:
        df = data[0]
        period = data[1]
        if not df.empty:
            last_data = df.iloc[-1]
            last_data_min = int(last_data['date'].split('T')[1].split(':')[1])
            a = 60 - now.minute
            b = 60 - last_data_min
            if np.abs(a-b) == period:
                flag += 1
    
    if flag == total_flag:
        return True
    else:
        return False

if __name__ == '__main__':

    user_input_settings()
    Fubon_account = fubon.Fubon_trade(Userinput_Product)
    update_account_info(Fubon_account)
    
    Processes = []
    data_queue = multiprocessing.Queue()                # shared data queue
    realtime_candle = multiprocessing.Manager().dict()  # shared dict

    create_twse_process(TWSE_PERIOD_30S, Userinput_Product, 'twse', data_queue, realtime_candle, Processes)
    create_fubon_process(FUBON_PERIOD_1M, Userinput_Product, data_queue, Processes)
    create_fubon_process(FUBON_PERIOD_5M, Userinput_Product, data_queue, Processes)
    create_fubon_process(FUBON_PERIOD_15M, Userinput_Product, data_queue, Processes)

    df_twse_30s = pd.DataFrame()
    df_fubon_1m = pd.DataFrame()
    df_fubon_5m = pd.DataFrame()
    df_fubon_15m = pd.DataFrame()

    try:
        while True:
            now = datetime.datetime.now()
            if not is_trading_time(now):
                print(f"[{now.strftime('%H:%M:%S')}] 不在交易時間...")
                time.sleep(60)
                continue

            if force_close_position(now):
                print(f"[{now.strftime('%H:%M:%S')}] 時段即將結束，執行平倉操作...")
                #close_all_position()
                time.sleep(60)
                continue

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_df = data_queue.get()
                # print(f"received period[{period}] data")
                # print(f"{tmp_df}")
                tmp_df = indicators_calculation(tmp_df)
                if period == TWSE_PERIOD_30S:
                    df_twse_30s = tmp_df
                elif period == FUBON_PERIOD_1M:
                    df_fubon_1m = tmp_df
                elif period == FUBON_PERIOD_5M:
                    df_fubon_5m = tmp_df
                elif period == FUBON_PERIOD_15M:
                    df_fubon_15m = tmp_df


            if now.minute % 15 == 0:
                if is_data_ready(now, [[df_fubon_1m, FUBON_PERIOD_1M],\
                                      [df_fubon_5m, FUBON_PERIOD_5M],\
                                      [df_fubon_15m, FUBON_PERIOD_15M]]):
                    print('1,5,15m data is updated')
                    show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)
                    time.sleep(10)
            
            elif now.minute % 5 == 0:
                if is_data_ready(now, [[df_fubon_1m, FUBON_PERIOD_1M],\
                                      [df_fubon_5m, FUBON_PERIOD_5M]]):
                    print('1,5m data is updated')
                    show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)
                    time.sleep(10)

            #multi_timeframe_strategy()

            show_user_settings()
            show_account_info()
            #show_realtime(realtime_candle)
            show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)

    except KeyboardInterrupt:
        print("All processes stopped.")
    