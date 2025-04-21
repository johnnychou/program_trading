import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time
import multiprocessing
import pandas as pd
import winsound

import twse
import fubon
import indicators
import utils
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
Total_profit = 0
Trade_times = 0
Balance = 0
OrderAmount = 0
PT_price = 0
Max_profit_pt = 0
Highest = 0
Lowest = 0

Flag_1m = 0
Flag_5m = 0
Flag_15m = 0
Last_executed_minute = -1

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

def create_twse_process(period, product, data_queue, realtime_candle, processes):
    """
    創建並啟動 TWSE 進程。

    Args:
        period (str): K線週期。
        product (str): 產品代碼。
        data_queue (multiprocessing.Queue): 用於傳輸資料的佇列。
        realtime_candle (multiprocessing.managers.DictProxy): 共享的即時 K 線字典。
        processes (list): 用於儲存已創建進程的列表。
    """
    twse_instance = twse.TWSE(period, product, data_queue, realtime_candle)
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

def chk_peak_value(realtime_candle):
    global Highest, Lowest
    if 'highest' not in realtime_candle or 'lowest' not in realtime_candle:
        return

    if not Highest:
        Highest = realtime_candle['highest']
    if not Lowest:
        Lowest = realtime_candle['lowest']

    if Highest < realtime_candle['highest']:
        Highest = realtime_candle['highest']
        winsound.Beep(1000,50)
    if Lowest > realtime_candle['lowest']:
        Lowest = realtime_candle['lowest']
        winsound.Beep(200,50)
    return

def show_realtime(realtime_candle):
    global Last_price
    level = 0
    if 'lastprice' in realtime_candle:
        Last_price = realtime_candle['lastprice']
    chk_peak_value(realtime_candle)
    if Highest != Lowest:
        level = round((Last_price - Lowest) / (Highest - Lowest) * 100, 2)
    print(f'Lastprice: {Last_price}, Highest: {Highest}, Lowest: {Lowest}, Level: {level}%')
    print('====================================================================')
    print(realtime_candle)
    return

def show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    global Last_price
    if 'lastprice' in realtime_candle:
        Last_price = realtime_candle['lastprice']
    print(f'lastprice: {Last_price}')
    print('==================================')
    print(realtime_candle)
    print('===30s============================')
    print(f"{df_twse_30s.tail(10)}")
    print('===1m=============================')
    print(f"{df_fubon_1m.tail(10)}")
    print('===5m=============================')
    print(f"{df_fubon_5m.tail(10)}")
    print('===15m============================')
    print(f"{df_fubon_15m.tail(10)}")
    return

def show_user_settings():
    print(f'Product: {Userinput_Product}/{OrderAmount},\
            Market: {Userinput_Market},\
            Direction: {Userinput_Direction}')
    print('====================================================================')
    return

def show_account_info():
    position = 'None'
    unrealized = 0
    if Buy_at:
        position = f'Buy: {Buy_at}'
        if Last_price:
            unrealized = (Last_price - Buy_at[0])*PT_price*OrderAmount
    elif Sell_at:
        position = f'Sell: {Sell_at}'
        if Last_price:
            unrealized = (Sell_at[0] - Last_price)*PT_price*OrderAmount

    print(f'Balance: {Balance}, Profit: {Total_profit}, TradeTimes: {Trade_times}')
    print(f'Position: {position}, Unrealized: {unrealized}')
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

def is_trading_time(market, now):
    if market == 'day' and is_market_time(DAY_MARKET, now):
        return True
    elif market == 'night' and is_market_time(NIGHT_MARKET, now):
        return True
    elif market == 'main' and (is_market_time(DAY_MARKET, now) or is_market_time(AMER_MARKET, now)):
        return True
    elif market == 'all' and (is_market_time(DAY_MARKET, now) or is_market_time(NIGHT_MARKET, now)):
        return True
    return False

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

def open_position(sig):
    global Trade_times
    if (Userinput_Direction == 'buy' and sig == -1) or\
         (Userinput_Direction == 'sell' and sig == 1):
        return 0
    if (Buy_at and sig == 1) or\
         (Sell_at and sig == -1):
        return 0
    Fubon_account.send_order(sig, OrderAmount)
    Trade_times += 1
    update_account_info(Fubon_account)
    return
    
def close_position(sig):
    global Total_profit, Trade_times
    if not Buy_at and not Sell_at:
        return 0
    if (Buy_at and sig == 1) or\
         (Sell_at and sig == -1):
        return 0
    Fubon_account.send_order(sig, OrderAmount)

    if sig == 1:
        entry_price = Sell_at[0]
        filled = Fubon_account.get_order_results()
        profit = entry_price - filled
    elif sig == -1:
        entry_price = Buy_at[0]
        filled = Fubon_account.get_order_results()
        profit = filled - entry_price

    Total_profit += profit*PT_price
    Trade_times += 1
    update_account_info(Fubon_account)
    return

def close_all_position():
    if Buy_at:
        close_position(-1)
    if Sell_at:
        close_position(1)
    return

def before_end_of_market(market, now):
    """判斷是否應該在收盤前一分鐘平倉"""
    now_str = now.strftime("%H:%M:%S")
    if market == 'day' and now_str == CLOSE_POSITION_TIME[0]:
        return True
    elif market == 'night' and now_str == CLOSE_POSITION_TIME[1]:
        return True
    elif market == 'main' and now_str in (CLOSE_POSITION_TIME[0], CLOSE_POSITION_TIME[2]) and is_trading_time(market, now):
        return True
    elif market == 'all' and now_str in (CLOSE_POSITION_TIME[0], CLOSE_POSITION_TIME[1]) and is_trading_time(market, now):
        return True
    else:
        return False

def is_data_ready(now, datas):
    """檢查指定週期資料是否已更新"""
    flag = 0
    total_flag = len(datas)
    for data in datas:
        df = data[0]
        period = utils.period_to_minute(data[1])
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

def indicators_calculation(df): # 直接在df新增欄位
    indicators.indicator_ma(df, MA_PERIOD)
    indicators.indicator_ema(df, EMA_PERIOD)
    indicators.indicator_ema(df, EMA2_PERIOD)
    indicators.indicator_atr(df, ATR_PERIOD)
    indicators.indicator_rsi(df, RSI_PERIOD)
    indicators.indicator_kd(df, KD_PERIOD[0], KD_PERIOD[1], KD_PERIOD[2])
    indicators.indicator_macd(df, MACD_PERIOD[0], MACD_PERIOD[1], MACD_PERIOD[2])
    indicators.indicator_bollingsband(df, BB_PERIOD[0], BB_PERIOD[1])
    indicators.indicator_vwap_cumulative(df)
    return

def chk_stop_loss(realtime_candle, df):
    if 'lastprice' not in realtime_candle:
        return
    if ATR_KEY not in df.columns:
        return
    if not (len(Buy_at) + len(Sell_at)):
        return

    lastprice = realtime_candle['lastprice']
    last_valid_idx = df[ATR_KEY].last_valid_index()
    atr = df.loc[last_valid_idx, ATR_KEY]

    if Buy_at:
        entry_price = Buy_at[0]
        close_price = entry_price - atr * 1.5
        if lastprice <= close_price:
            return 1
    elif Sell_at:
        entry_price = Sell_at[0]
        close_price = entry_price + atr * 1.5
        if lastprice >= close_price:
            return 1
    return 0

def chk_take_profit(realtime_candle, df):
    if 'lastprice' not in realtime_candle:
        return
    if ATR_KEY not in df.columns:
        return
    if not (len(Buy_at) + len(Sell_at)):
        return

    lastprice = realtime_candle['lastprice']
    last_valid_idx = df[ATR_KEY].last_valid_index()
    atr = df.loc[last_valid_idx, ATR_KEY]

    if Buy_at:
        entry_price = Buy_at[0]
        close_price = entry_price + atr * 2
        if lastprice >= close_price:
            return 1
    elif Sell_at:
        entry_price = Sell_at[0]
        close_price = entry_price - atr * 2
        if lastprice <= close_price:
            return 1
    return 0

def atr_trailing_stop(realtime_candle, df):
    global Max_profit_pt
    if 'lastprice' not in realtime_candle:
        return 0
    if ATR_KEY not in df.columns:
        return 0
    if not (len(Buy_at) + len(Sell_at)):
        return
    
    lastprice = realtime_candle['lastprice']
    last_valid_idx = df[ATR_KEY].last_valid_index()
    atr = df.loc[last_valid_idx, ATR_KEY]

    if Buy_at:
        Max_profit_pt = max(lastprice, Buy_at[0], Max_profit_pt)
        stop_price = Max_profit_pt - atr * 1.5
        if lastprice <= stop_price:
            close_position(-1)
            Max_profit_pt = 0
            return stop_price

    elif Sell_at:
        if not Max_profit_pt:
            Max_profit_pt = min(lastprice, Sell_at[0])
        else:
            Max_profit_pt = min(lastprice, Sell_at[0], Max_profit_pt)
        stop_price = Max_profit_pt + atr * 1.5
        if lastprice >= stop_price:
            close_position(1)
            Max_profit_pt = 0
            return stop_price

    return 0

def chk_ema_signal(df):
    if len(df) < 2:
        return
    ema_short = df[EMA_KEY].iloc[-1]
    ema_long = df[EMA2_KEY].iloc[-1]
    pre_ema_short = df[EMA_KEY].iloc[-2]
    pre_ema_long = df[EMA2_KEY].iloc[-2]

    if pre_ema_short < pre_ema_long and ema_short >= ema_long:
        return 1 # 做多

    if pre_ema_short > pre_ema_long and ema_short <= ema_long:
        return -1 # 做空

    return 0

def trading_strategy(df):
    position = len(Buy_at) + len(Sell_at)
    signal = 0

    if (df.iloc[-1]['close'] > df.iloc[-2]['high']) and\
         (df.iloc[-1]['close'] > df.iloc[-1][EMA2_KEY]) and\
         (df.iloc[-1]['close'] > df.iloc[-1]['VWAP']) and\
         (df.iloc[-1][RSI_KEY] < 70):
        signal = 1
    elif (df.iloc[-1]['close'] < df.iloc[-2]['low']) and\
         (df.iloc[-1]['close'] < df.iloc[-1][EMA2_KEY]) and\
         (df.iloc[-1]['close'] < df.iloc[-1]['VWAP']) and\
         (df.iloc[-1][RSI_KEY] > 30):
        signal = -1

    if signal:
        if not position:
            open_position(signal)
        else:
            close_position(signal)
            open_position(signal)

    return

if __name__ == '__main__':

    user_input_settings()
    Fubon_account = fubon.Fubon_trade(Userinput_Product)
    update_account_info(Fubon_account)
    
    Processes = []
    data_queue = multiprocessing.Queue()                # shared data queue
    realtime_candle = multiprocessing.Manager().dict()  # shared dict

    create_twse_process(PERIOD_30S, Userinput_Product, data_queue, realtime_candle, Processes)
    create_fubon_process(PERIOD_1M, Userinput_Product, data_queue, Processes)
    create_fubon_process(PERIOD_5M, Userinput_Product, data_queue, Processes)
    create_fubon_process(PERIOD_15M, Userinput_Product, data_queue, Processes)

    df_twse_30s = pd.DataFrame()
    df_fubon_1m = pd.DataFrame()
    df_fubon_5m = pd.DataFrame()
    df_fubon_15m = pd.DataFrame()

    df_flag = {}

    try:
        while True:
            now = datetime.datetime.now()
            if not is_trading_time(Userinput_Market, now):
                print(f"[{now.strftime('%H:%M:%S')}] 不在交易時間...")
                time.sleep(60)
                continue

            if before_end_of_market(Userinput_Market, now):
                print(f"[{now.strftime('%H:%M:%S')}] 時段即將結束，執行平倉操作...")
                #close_all_position()
                time.sleep(60)
                continue

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_df = data_queue.get()
                # print(f"received period[{period}] data")
                # print(f"{tmp_df}")
                indicators_calculation(tmp_df)
                if period == PERIOD_30S:
                    df_twse_30s = tmp_df
                    df_flag[period] = 1
                elif period == PERIOD_1M:
                    df_fubon_1m = tmp_df
                    df_flag[period] = 1
                elif period == PERIOD_5M:
                    df_fubon_5m = tmp_df
                    df_flag[period] = 1
                elif period == PERIOD_15M:
                    df_fubon_15m = tmp_df
                    df_flag[period] = 1

            if now.minute % 15 == 0 and now.minute != Last_executed_minute:
                if is_data_ready(now, [[df_fubon_1m, PERIOD_1M],\
                                      [df_fubon_5m, PERIOD_5M],\
                                      [df_fubon_15m, PERIOD_15M]]):
                    Last_executed_minute = now.minute
                    # print('1,5,15m data is all updated')
                    # show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)
                    # time.sleep(10)
            
            elif now.minute % 5 == 0 and now.minute != Last_executed_minute:
                if is_data_ready(now, [[df_fubon_1m, PERIOD_1M],\
                                      [df_fubon_5m, PERIOD_5M]]):
                    Last_executed_minute = now.minute
                    # print('1,5m data is all updated')
                    # show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)
                    # time.sleep(10)

            show_user_settings()
            show_account_info()
            show_realtime(realtime_candle)

            print(df_fubon_5m.tail(5))

            if len(df_fubon_5m) > 2:
                dfs = df_fubon_5m.tail(5)
                for index, row_series in dfs.iterrows():
                    print(f'EMA_5: {row_series[EMA_KEY]}, EMA_20: {row_series[EMA2_KEY]}')
                print(f'ATR: {dfs.iloc[-1][ATR_KEY]}')


            #show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)

            #chk_stop_loss(realtime_candle, df_fubon_5m)
            #chk_take_profit(realtime_candle, df_fubon_5m)
            if stop_pt := atr_trailing_stop(realtime_candle, df_fubon_5m):
                print(f'ATR trailing stop at: {stop_pt}')

            if Last_executed_minute == now.minute and df_flag[PERIOD_5M]:
                trading_strategy(df_fubon_5m)
                df_flag[PERIOD_5M] = 0

            time.sleep(1)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")
    