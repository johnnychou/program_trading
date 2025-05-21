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
KD_reserved = 0
VWAP_trend = 0

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
    processes.append([process, period])
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
    processes.append([process, period])
    return

def check_process_alive(processes, data_queue, realtime_candle):
    restart_list = []
    for p in processes:
        process_obj = p[0]  # 獲取 Process 物件
        period_key = p[1]   # 獲取對應的 period

        if process_obj.is_alive():
            print(f"Process (Period: {period_key}) is alive.")
        else:
            # 如果進程已結束，檢查它的退出碼 (exitcode)
            # exitcode 為 0 通常代表正常結束
            # exitcode 為負值 -N 代表被信號 N 終止 (Unix-like)
            # exitcode 為正值 通常代表程式內部有錯誤退出
            exit_code = process_obj.exitcode
            print(f"Process (Period: {period_key}) is dead. Exit Code: {exit_code}")
            restart_list.append(period_key)

    if restart_list:
        processes = [proc_info for proc_info in processes if proc_info[0].is_alive()]

        for period_key in restart_list:
            if period_key == PERIOD_59S:
                create_twse_process(period_key, Userinput_Product, data_queue, realtime_candle, processes)
            else:
                create_fubon_process(period_key, Userinput_Product, data_queue, processes)
            print(f'Process (Period: {period_key}) is restarted.')

        winsound.Beep(5000,1000)
        time.sleep(10)

    return processes

def restart_all_processes(processes, data_queue, realtime_candle):

    print("Initiating restart of all processes to reinitialize data...")

    # 1. Store all period_keys for recreation later
    # We need these because we're about to terminate the processes holding them.
    all_period_keys = []
    if processes: # Ensure processes list is not empty
        all_period_keys = [p_info[1] for p_info in processes]
        print(f"Identified {len(all_period_keys)} processes to restart: {all_period_keys}")
    else:
        print("No processes currently in the list to restart.")
        return processes # Return the empty list

    # 2. Terminate all existing processes
    print("**Terminating all current processes...**")
    for p_info in processes:
        process_obj = p_info[0]
        period_key = p_info[1]
        if process_obj.is_alive():
            try:
                print(f"   Terminating process (Period: {period_key})...")
                process_obj.terminate()
                process_obj.join(timeout=5) # Wait for the process to end (max 5 seconds)
                if process_obj.is_alive():
                    print(f"   Warning: Process (Period: {period_key}) did not terminate after 5 seconds.")
                else:
                    print(f"   Process (Period: {period_key}) terminated. Exit code: {process_obj.exitcode}")
            except Exception as e:
                print(f"   Error terminating process (Period: {period_key}): {e}")
        else:
            # If already dead, still good to call join to clean up zombie process if any
            process_obj.join(timeout=1) # Short timeout for already dead processes
            print(f"   ℹProcess (Period: {period_key}) was already dead. Exit code: {process_obj.exitcode}")

    # 3. Clear the old processes list (in-place)
    # The create functions will append new process objects to this list.
    processes.clear()
    print("Cleared the old processes list.")

    # 4. Recreate all processes using the stored period_keys
    print("Recreating all processes...")
    for period_key in all_period_keys:
        print(f"   Attempting to create new process for (Period: {period_key}).")
        if period_key == PERIOD_59S:
            create_twse_process(period_key, Userinput_Product, data_queue, realtime_candle, processes)
        else:
            create_fubon_process(period_key, Userinput_Product, data_queue, processes)
        print(f'   Process (Period: {period_key}) has been recreated.')

    print(f"All {len(all_period_keys)} processes have been requested to restart.")

    winsound.Beep(2000,200)
    time.sleep(5) # Give a moment for processes to initialize

    return processes

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
    print('==============================================================================')
    print(realtime_candle)
    print('==============================================================================')
    return

def show_candles(realtime_candle, df_twse, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    global Last_price
    if 'lastprice' in realtime_candle:
        Last_price = realtime_candle['lastprice']
    print(f'lastprice: {Last_price}')
    print('==================================')
    print(realtime_candle)
    print('===30s============================')
    print(f"{df_twse.tail(5)}")
    print('===1m=============================')
    print(f"{df_fubon_1m.tail(5)}")
    print('===5m=============================')
    print(f"{df_fubon_5m.tail(5)}")
    print('===15m============================')
    print(f"{df_fubon_15m.tail(5)}")
    return

def show_user_settings():
    print('==============================================================================')
    if VWAP_trend == 1:
        trend = 'buy only'
    elif VWAP_trend == -1:
        trend = 'sell only'
    else: 
        trend = 'none'

    print(f'Product: {Userinput_Product}/{OrderAmount},\
            Market: {Userinput_Market},\
            Direction: {Userinput_Direction}: {trend}')
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
    print('==============================================================================')
    print(f'Balance: {Balance}, Profit: {Total_profit}, TradeTimes: {Trade_times}')
    print(f'Position: {position}, Unrealized: {unrealized}')
    print('==============================================================================')
    return

def is_market_time(market_hours, now):
    start_str, end_str = market_hours
    start_time = datetime.datetime.strptime(start_str, "%H:%M:%S").time()
    end_time = datetime.datetime.strptime(end_str, "%H:%M:%S").time()
    now_time = now.time()

    if end_time < start_time:  # 處理跨日
        return start_time <= now_time or now_time < end_time
    else:
        return start_time <= now_time < end_time

def is_trading_time(market, now):
    if market == 'day' and is_market_time(DAY_MARKET, now):
        return True
    elif market == 'night' and is_market_time(NIGHT_MARKET, now):
        return True
    elif market == 'main' and ((is_market_time(DAY_MARKET, now) or is_market_time(AMER_MARKET, now))):
        return True
    elif market == 'all' and ((is_market_time(DAY_MARKET, now) or is_market_time(NIGHT_MARKET, now))):
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
    #time.sleep(5)
    return

def direct_trading(sig):
    if not Buy_at and not Sell_at:
        open_position(sig)
    else:
        close_position(sig)
        open_position(sig)
    return

def open_position(sig):
    global Trade_times
    if Buy_at or Sell_at:
        return 0
    if (Userinput_Direction == 'buy' and sig == -1) or\
         (Userinput_Direction == 'sell' and sig == 1):
        return 0
    if (Userinput_Direction == 'auto'):
        if VWAP_trend != 0 and VWAP_trend != sig:
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
        if not filled:
            filled = Last_price
        profit = entry_price - filled
    elif sig == -1:
        entry_price = Buy_at[0]
        filled = Fubon_account.get_order_results()
        if not filled:
            filled = Last_price
        profit = filled - entry_price

    Total_profit += profit*PT_price
    Trade_times += 1
    update_account_info(Fubon_account)
    return 1

def close_all_position():
    if Buy_at:
        close_position(-1)
    if Sell_at:
        close_position(1)
    return

def before_end_of_market(market, now):
    """判斷是否應該在收盤前一分鐘平倉"""
    close_position_times = []
    if market == 'day':
        close_position_times = [datetime.datetime.strptime(DAY_MARKET[1], "%H:%M:%S").time()]
    elif market == 'night':
        close_position_times = [datetime.datetime.strptime(NIGHT_MARKET[1], "%H:%M:%S").time()]
    elif market == 'main':
        close_position_times = [datetime.datetime.strptime(DAY_MARKET[1], "%H:%M:%S").time(),
                                datetime.datetime.strptime(AMER_MARKET[1], "%H:%M:%S").time()]
    elif market == 'all':
        close_position_times = [datetime.datetime.strptime(DAY_MARKET[1], "%H:%M:%S").time(),
                                datetime.datetime.strptime(NIGHT_MARKET[1], "%H:%M:%S").time()]
    now_time = now.time()
    dummy_date = now.date() # 用於 timedelta 計算

    for close_time in close_position_times:
        close_dt = datetime.datetime.combine(dummy_date, close_time)
        start_of_last_minute_dt = close_dt - datetime.timedelta(minutes=1)
        start_of_last_minute_time = start_of_last_minute_dt.time()

        # 判斷區間 (處理跨午夜)
        in_interval = False
        if start_of_last_minute_time > close_time: # 區間跨午夜
            in_interval = (now_time >= start_of_last_minute_time) or (now_time < close_time)
        else: # 標準區間
            in_interval = start_of_last_minute_time <= now_time < close_time

        # 只要任何一個時間點符合條件，就立刻返回 True
        if in_interval:
            return True

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

def chk_max_stop_loss(realtime_candle):
    if not Buy_at and not Sell_at:
        return 0
    if 'lastprice' not in realtime_candle:
        return 0

    lastprice = realtime_candle['lastprice']

    if Buy_at:
        entry_price = Buy_at[0]
        close_price = entry_price - MAX_LOSS_PT
        print(f'Position will stop loss at {close_price}')
        if lastprice <= close_price:
            close_position(-1)
            return
        
    elif Sell_at:
        entry_price = Sell_at[0]
        close_price = entry_price + MAX_LOSS_PT
        print(f'Position will stop loss at {close_price}')
        if lastprice >= close_price:
            close_position(1)
            return
        
    return

def atr_fixed_stop(realtime_candle, df):
    if sig := chk_stop_loss(realtime_candle, df):
        return sig
    if sig := chk_take_profit(realtime_candle, df):
        return sig
    return 0

def chk_stop_loss(realtime_candle, df):
    if 'lastprice' not in realtime_candle:
        return 0
    if ATR_KEY not in df.columns:
        return 0
    if not Buy_at and not Sell_at:
        return 0

    lastprice = realtime_candle['lastprice']
    last_valid_idx = df[ATR_KEY].last_valid_index()
    atr = df.loc[last_valid_idx, ATR_KEY]
    atr = max(atr, MIN_ATR) # prevent atr too small

    if Buy_at:
        entry_price = Buy_at[0]
        close_price = int(entry_price - min(atr*1.5, MAX_LOSS_PT))
        print(f'Position will stop loss at {close_price}')
        if lastprice <= close_price:
            return -1
    elif Sell_at:
        entry_price = Sell_at[0]
        close_price = int(entry_price + min(atr*1.5, MAX_LOSS_PT))
        print(f'Position will stop loss at {close_price}')
        if lastprice >= close_price:
            return 1
    return 0

def chk_take_profit(realtime_candle, df):
    if 'lastprice' not in realtime_candle:
        return 0
    if ATR_KEY not in df.columns:
        return 0
    if not Buy_at and not Sell_at:
        return 0

    lastprice = realtime_candle['lastprice']
    last_valid_idx = df[ATR_KEY].last_valid_index()
    atr = df.loc[last_valid_idx, ATR_KEY]
    atr = max(atr, MIN_ATR) # prevent atr too small

    if Buy_at:
        entry_price = Buy_at[0]
        close_price = int(entry_price + min(atr*2, MAX_LOSS_PT))
        print(f'Position will take profit at {close_price}')
        if lastprice >= close_price:
            return -1
    elif Sell_at:
        entry_price = Sell_at[0]
        close_price = int(entry_price - min(atr*2, MAX_LOSS_PT))
        print(f'Position will take profit at {close_price}')
        if lastprice <= close_price:
            return 1
    return 0

def atr_trailing_stop(realtime_candle, df):
    global Max_profit_pt
    if 'lastprice' not in realtime_candle:
        return 0
    if ATR_KEY not in df.columns:
        return 0
    
    lastprice = realtime_candle['lastprice']
    last_valid_idx = df[ATR_KEY].last_valid_index()
    if not last_valid_idx:
        return 0

    atr = df.loc[last_valid_idx, ATR_KEY]
    atr = max(atr, MIN_ATR)
    atr_gap = min(atr*1.5, MAX_LOSS_PT)
    print(f'ATR: {atr}, gap: {atr_gap}')

    if Buy_at:
        Max_profit_pt = max(lastprice, Buy_at[0], Max_profit_pt)
        stop_price = Max_profit_pt - atr_gap
        print(f'Max Profit at: {Max_profit_pt}, {(Max_profit_pt-Buy_at[0])*PT_price}')
        print(f'ATR trailing will stop at: {stop_price}')
        if lastprice <= stop_price:
            Max_profit_pt = 0
            return -1

    elif Sell_at:
        if not Max_profit_pt:
            Max_profit_pt = min(lastprice, Sell_at[0])
        else:
            Max_profit_pt = min(lastprice, Sell_at[0], Max_profit_pt)
        stop_price = Max_profit_pt + atr_gap
        print(f'Max Profit at: {Max_profit_pt}, {(Sell_at[0]-Max_profit_pt)*PT_price}')
        print(f'ATR trailing will stop at: {stop_price}')
        if lastprice >= stop_price:
            Max_profit_pt = 0
            return 1

    return 0

def bband_stop(df):
    if BB_KEY not in df.columns:
        return 0
    if len(df) < 2:
        return 0

    up_band = df.iloc[-1][BB_KEY][1]
    bot_band = df.iloc[-1][BB_KEY][2]
    pre_up_band = df.iloc[-2][BB_KEY][1]
    pre_bot_band = df.iloc[-2][BB_KEY][2]

    pre_high = df.iloc[-2]['high']
    pre_low = df.iloc[-2]['low']
    close = df.iloc[-1]['close']

    if Buy_at:
        if pre_high >= pre_up_band and close < up_band and close <= pre_low:
            return -1
    if Sell_at:
        if pre_low <= pre_bot_band and close > bot_band and close >= pre_high:
            return 1
    return 0

def trend_or_consolidation_adx(df):
    if ADX_KEY not in df.columns:
        return
    adx = df.iloc[-1][ADX_KEY]
    if adx > 30:
        return 'trend'
    elif adx < 20:
        return 'notrade'
    return 'consolidation'

def trend_or_consolidation_bb(df):
    if len(df) < 3:
        return
    if BB_KEY not in df.columns:
        return
    if ATR_KEY not in df.columns:
        return
    
    up_band_1 = df.iloc[-1][BB_KEY][1]
    bot_band_1 = df.iloc[-1][BB_KEY][2]
    up_band_2 = df.iloc[-2][BB_KEY][1]
    bot_band_2 = df.iloc[-2][BB_KEY][2]
    up_band_3 = df.iloc[-3][BB_KEY][1]
    bot_band_3 = df.iloc[-3][BB_KEY][2]

    band_1 = up_band_1 - bot_band_1
    band_2 = up_band_2 - bot_band_2
    band_3 = up_band_3 - bot_band_3

    if band_1 > 60 and band_1 > band_2 > band_3:
        return 'trend'
    elif band_1 < 30:
        return 'notrade'
    return 'consolidation'

def is_sideways_market(df, angle_threshold=SIDEWAY_MARKET_ANGLE):
    if len(df) < MA_PERIOD:
        return False

    x = np.arange(MA_PERIOD)
    y = df[MA_KEY].tail(MA_PERIOD).values
    slope = np.polyfit(x, y, 1)[0]
    angle = abs(np.degrees(np.arctan(slope)))
    print(f'MA slope: {slope:.2f}, Angle: {angle:.2f}, Threshold: {angle_threshold}')
    return angle < angle_threshold

def kd_relation(df):
    if len(df) < 1:
        return 0
    k = df.iloc[-1][KD_KEY][0]
    d = df.iloc[-1][KD_KEY][1]

    if k > d:
        return 1
    elif k < d:
        return -1
    return 0

def get_min_diff(d):
    diff = np.abs(d-50)
    min_diff = (50-diff)/10
    return round(min_diff*KD_MIN_DIFF_RATIO, 2)

def kd_relation_strict(df):
    if len(df) < KD_PERIOD[0]:
        return 0
    k = df.iloc[-1][KD_KEY][0]
    d = df.iloc[-1][KD_KEY][1]
    rsv = df.iloc[-1][KD_KEY][2]
    pre_k = df.iloc[-2][KD_KEY][0]
    pre_d = df.iloc[-2][KD_KEY][1]
    wave = price_range(df, KD_PERIOD[0])
    positions = len(Buy_at) + len(Sell_at)

    diff = np.abs(k - d)
    kd_min_diff = max(get_min_diff(d), KD_MIN_DIFF_FIXED)

    if k > d and diff > kd_min_diff:
        if not positions:
            if VWAP_trend == 1:
                return 1
            return 0
        elif Sell_at:
            if k < 10: # 極高檔獲利了結
                return 1
            elif k < 25: # 防鈍化平倉
                return 0
            return 1   # 平空倉

    elif k < d and diff > kd_min_diff:
        if not positions:
            if VWAP_trend == -1:
                return -1
            return 0
        elif Buy_at:
            if k > 90: # 極高檔獲利了結
                return -1
            elif k > 75: # 防鈍化平倉
                return 0
            return -1  # 平多倉

    return 0

def kd_cross_signal(df):
    if len(df) < KD_PERIOD[0]:
        return 0
    
    global KD_reserved

    k = df.iloc[-1][KD_KEY][0]
    d = df.iloc[-1][KD_KEY][1]
    pre_k = df.iloc[-2][KD_KEY][0]
    pre_d = df.iloc[-2][KD_KEY][1]

    diff = np.abs(k - d)

    # golden cross
    if pre_k <= pre_d and k > d:
        if k > 80:
            return 0
        if diff < 2:
            KD_reserved = 1
            return 0
        return 1
    
    # death cross
    if pre_k >= pre_d and k < d:
        if k < 20:
            return 0
        if diff < 2:
            KD_reserved = -1
            return 0
        return -1
    
    if KD_reserved == 1:
        if k > d and diff >= 2:
            KD_reserved = 0
            if k > 80:
                return 0
            return 1
        
    elif KD_reserved == -1:
        if k < d and diff >= 2:
            KD_reserved = 0
            if k < 20:
                return 0
            return -1
    
    return 0

def bb_bandwidth(df):
    if len(df) < 2:
        return
    if BB_KEY not in df.columns:
        return
    
    up_band = df.iloc[-1][BB_KEY][1]
    bot_band = df.iloc[-1][BB_KEY][2]

    return (up_band - bot_band)

def vwap_trend(df, window=VWAP_TREND_WINDOW, threshold=20, min_rate=0.95):
    if len(df) < window:
        return
    global VWAP_trend
    min_count = int(window * min_rate)
    recent = df.tail(window)
    above_vwap = (recent['close'] >= recent['vwap'] + threshold).sum()
    below_vwap = (recent['close'] <= recent['vwap'] - threshold).sum()

    if above_vwap >= min_count:
        VWAP_trend = 1
    elif below_vwap >= min_count:
        VWAP_trend = -1
    else:
        VWAP_trend = 0
    return

def consolidation_strategy_kd(df):
    if len(df) < 2:
        return
    if KD_KEY not in df.columns:
        return
    k = df.iloc[-1][KD_KEY][0]
    d = df.iloc[-1][KD_KEY][1]
    rsv = df.iloc[-1][KD_KEY][2]
    
    pre_k = df.iloc[-2][KD_KEY][0]
    pre_d = df.iloc[-2][KD_KEY][1]

    # golden cross
    if pre_k <= pre_d and k > d and rsv < 30:
        return 1
    
    # death cross
    if pre_k >= pre_d and k < d and rsv > 70:
        return -1

    return 0

def consolidation_strategy_kd_r(df):
    if len(df) < 2:
        return
    if KD_KEY not in df.columns:
        return
    k = df.iloc[-1][KD_KEY][0]
    d = df.iloc[-1][KD_KEY][1]
    rsv = df.iloc[-1][KD_KEY][2]
    
    pre_k = df.iloc[-2][KD_KEY][0]
    pre_d = df.iloc[-2][KD_KEY][1]

    # golden cross
    if pre_k <= pre_d and k > d and rsv > 80:
        return -1
    
    # death cross
    if pre_k >= pre_d and k < d and rsv < 20:
        return 1

    return 0

def consolidation_strategy_bb(df):
    if len(df) < 2:
        return
    if BB_KEY not in df.columns:
        return
    if KD_KEY not in df.columns:
        return
    
    up_band = df.iloc[-1][BB_KEY][1]
    bot_band = df.iloc[-1][BB_KEY][2]
    pre_up_band = df.iloc[-2][BB_KEY][1]
    pre_bot_band = df.iloc[-2][BB_KEY][2]

    pre_high = df.iloc[-2]['high']
    pre_low = df.iloc[-2]['low']
    pre_close = df.iloc[-2]['close']
    close = df.iloc[-1]['close']

    rsv = df.iloc[-1][KD_KEY][2]

    # buy
    if not Buy_at and not Sell_at:
        if pre_low < pre_bot_band:
            if close > bot_band and close > pre_close and rsv < 30:
                open_position(1)
        # sell
        elif pre_high > pre_up_band:
            if close < up_band and close < pre_close and rsv > 70:
                open_position(-1)

    return 0

def trend_strategy(df):
    if len(df) < 2:
        return
    if EMA2_KEY not in df.columns:
        return
    if VWAP_KEY not in df.columns:
        return
    if KD_KEY not in df.columns:
        return
    if RSI_KEY not in df.columns:
        return

    signal = 0

    # buy
    if (df.iloc[-1]['close'] >= df.iloc[-2]['high']) and\
         (df.iloc[-1]['close'] > df.iloc[-1][EMA2_KEY]) and\
         (df.iloc[-1]['close'] > df.iloc[-1][VWAP_KEY]) and\
         (df.iloc[-1][KD_KEY][0] > df.iloc[-1][KD_KEY][1]) and\
         df.iloc[-1][RSI_KEY] < 70:
        signal = 1
    # sell
    elif (df.iloc[-1]['close'] <= df.iloc[-2]['low']) and\
         (df.iloc[-1]['close'] < df.iloc[-1][EMA2_KEY]) and\
         (df.iloc[-1]['close'] < df.iloc[-1][VWAP_KEY]) and\
         (df.iloc[-1][KD_KEY][0] < df.iloc[-1][KD_KEY][1]) and\
         df.iloc[-1][RSI_KEY] > 30:
        signal = -1

    return signal

def strategy_1(realtime_candle, df_fubon_1m, df_fubon_5m, df_flag, now):
    if len(df_fubon_1m) < 2 or len(df_fubon_5m) < 2:
        return
    # show some key data
    # for index, row_series in dfs_1.iterrows():
    #     print(f'BB: {row_series[BB_KEY]}, KD: {row_series[KD_KEY]}')
    # atr = dfs_1.iloc[-1][ATR_KEY]
    # adx = dfs_1.iloc[-1][ADX_KEY]
    # print(f'1_min: ATR_{ATR_PERIOD}: {atr}, ADX_{ADX_PERIOD}: {adx}')
    # print('==============================================================================')
    # # show some key data
    # for index, row_series in dfs_5.iterrows():
    #     print(f'EMA_5: {row_series[EMA_KEY]}, EMA_20: {row_series[EMA2_KEY]}, RSI: {row_series[RSI_KEY]}')
    # atr_5 = dfs_5.iloc[-1][ATR_KEY]
    # adx_5 = dfs_5.iloc[-1][ADX_KEY]
    # print(f'5_min: ATR_{ATR_PERIOD}: {atr_5}, ADX_{ADX_PERIOD}: {adx_5}')
    # print('==============================================================================')
    
    
    if is_market_time(DAY_HIGH_TIME, now) or\
            is_market_time(NIGHT_HIGH_TIME, now):
        
        print(f'High trade-rate time.')

        if Buy_at or Sell_at:
            if sig:= atr_trailing_stop(realtime_candle, df_fubon_1m):
                close_position(sig)
            elif df_flag[PERIOD_59S]:
                sig = kd_cross_signal(df_fubon_1m)
                if (Buy_at and sig == -1) or\
                        (Sell_at and sig == 1):
                    close_position(sig)
                else:
                    df_flag[PERIOD_59S] = 0

        if not Buy_at and not Sell_at and Last_executed_minute == now.minute:
            if df_flag[PERIOD_59S]:
                sig = kd_relation(df_fubon_1m)
                if len(df_fubon_5m) >= KD_PERIOD[0]:
                    trend = kd_relation(df_fubon_5m)
                else:
                    trend = sig

                if sig == trend:
                    open_position(sig)
                df_flag[PERIOD_59S] = 0

    else:
        # get trade type
        trade_type = trend_or_consolidation_bb(df_fubon_1m)

        print(f'Market type: {trade_type}')

        # check for close position
        if Buy_at or Sell_at:
            if trade_type == 'trend':
                if sig:= atr_trailing_stop(realtime_candle, df_fubon_5m):
                    close_position(sig)
            else:
                if sig:= atr_fixed_stop(realtime_candle, df_fubon_1m):
                    close_position(sig)
                elif sig:= bband_stop(df_fubon_1m):
                    close_position(sig)

        # check for open position
        if not Buy_at and not Sell_at and Last_executed_minute == now.minute:
            if trade_type == 'notrade':
                pass
            elif trade_type == 'trend':
                if df_flag[PERIOD_5M]:
                    if sig := trend_strategy(df_fubon_5m):
                        open_position(sig)
                    df_flag[PERIOD_5M] = 0
            else:
                if df_flag[PERIOD_1M]:
                    if sig := consolidation_strategy_bb(df_fubon_1m):
                        open_position(sig)
                    df_flag[PERIOD_1M] = 0

def multi_kd_strategy(df_1m, df_5m, df_15m, now):
    if len(df_1m) < KD_PERIOD[0]:
        return

    if is_market_time(DAY_MARKET, now) or\
         is_market_time(AMER_MARKET, now):
        
        sig = kd_relation_strict(df_1m) # 單看1分鐘

        if not Buy_at and not Sell_at:
            if sig:
                open_position(sig)
        else:
            if Buy_at and sig == -1:
                close_position(-1)
                if sig == VWAP_trend:
                    open_position(-1)
            elif Sell_at and sig == 1:
                close_position(1)
                if sig == VWAP_trend:
                    open_position(1)

    else: # 1, 5分鐘雙重確認

        trend_1 = kd_relation_strict(df_1m)
        trend_5 = kd_relation_strict(df_5m)
        #trend_2 = kd_relation_strict(df_15m)

        score = trend_1 + trend_5 + VWAP_trend

        if not Buy_at and not Sell_at:
            if np.abs(score) >= 2:    # 1, 1, 0
                if score > 0:
                    open_position(1)
                else:
                    open_position(-1)
        else:
            if Buy_at and score <= -1: # -1, -1, 1
                close_position(-1)
                if score == -3:
                    open_position(-1)
            elif Sell_at and score >= 1: # 1, 1, -1
                close_position(1)
                if score == 3:
                    open_position(1)

def candle_shadow_signal(df):
    if len(df) < 1:
        return 0
    
    MIN_BODY = 4         # body最小點數
    MIN_CANDLE = 10      # 整根K線高低
    SHADOW_RATIO = 1.8     # 影線長度需至少為實體的倍數
    DOMINANCE_RATIO = 1.8  # 主導影線需為對側影線的倍數

    open = df.iloc[-1]['open']
    close = df.iloc[-1]['close']
    high = df.iloc[-1]['high']
    low = df.iloc[-1]['low']

    candle_length = high - low
    body_length = abs(open-close)
    upper_shadow = high - max(open, close)
    lower_shadow = min(open, close) - low

    shadow_threshold = body_length * SHADOW_RATIO
    shadow_reverse = 0

    if body_length >= MIN_BODY:
        if (upper_shadow >= shadow_threshold) and (lower_shadow < shadow_threshold):
        # 僅上影線顯著（下影線不顯著）→ 判斷為壓力
            shadow_reverse = -1
            return -1
        elif (lower_shadow >= shadow_threshold) and (upper_shadow < shadow_threshold):
            # 僅下影線顯著（上影線不顯著）→ 判斷為支撐
            shadow_reverse = 1
            return 1
        elif (upper_shadow >= shadow_threshold) and (lower_shadow >= shadow_threshold):
            # 雙邊影線皆滿足，需判斷是否有主導性
            if upper_shadow >= (lower_shadow * DOMINANCE_RATIO):
                shadow_reverse = -1
                return -1
            elif lower_shadow >= (upper_shadow * DOMINANCE_RATIO):
                shadow_reverse = 1
                return 1

    if (not shadow_reverse) and (candle_length >= MIN_CANDLE): #較次要
        if (upper_shadow / candle_length) > 0.7:
            shadow_reverse = -1
        elif (lower_shadow / candle_length) > 0.7:
            shadow_reverse = 1

    return shadow_reverse

def current_close_ratio(df, window=CLOSE_RATIO_WINDOW):
    if len(df) < window:
        return 50
    highest = df['high'].tail(window).max()
    lowest = df['low'].tail(window).min()
    last_close = df.iloc[-1]['close']
    if (highest == lowest):
        ratio = 50
    else:
        ratio = round((last_close - lowest)/(highest - lowest)*100, 2)
    return ratio

def price_range(df, window=CLOSE_RATIO_WINDOW):
    # if len(df) < window:
    #     return 0
    highest = df['high'].tail(window).max()
    lowest = df['low'].tail(window).min()
    width = highest - lowest
    return width

if __name__ == '__main__':

    user_input_settings()
    Fubon_account = fubon.Fubon_trade(Userinput_Product)
    update_account_info(Fubon_account)
    
    processes = []
    restart_list = []
    data_queue = multiprocessing.Queue()                # shared data queue
    realtime_candle = multiprocessing.Manager().dict()  # shared dict

    create_twse_process(PERIOD_59S, Userinput_Product, data_queue, realtime_candle, processes)
    create_fubon_process(PERIOD_1M, Userinput_Product, data_queue, processes)
    create_fubon_process(PERIOD_5M, Userinput_Product, data_queue, processes)
    create_fubon_process(PERIOD_15M, Userinput_Product, data_queue, processes)

    df_twse = pd.DataFrame()
    df_fubon_1m = pd.DataFrame()
    df_fubon_5m = pd.DataFrame()
    df_fubon_15m = pd.DataFrame()

    df_flag = {
        PERIOD_59S: 0,
        PERIOD_1M: 0,
        PERIOD_5M: 0,
        PERIOD_15M: 0,
    }

    # last_minute_checked = -1
    close_ratio = 50
    shadow_sig = 0
    restart_processes_flag = 0

    try:
        while True:
            now = datetime.datetime.now()

            # 隨時檢查processes
            processes = check_process_alive(processes, data_queue, realtime_candle)

            # 檢查 data queue 有無新資料
            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_df = data_queue.get()
                # print(f"received period[{period}] data")
                # print(f"{tmp_df}")
                if period == PERIOD_59S:
                    df_twse = tmp_df
                    df_flag[period] = 1
                elif period == PERIOD_1M:
                    df_fubon_1m = tmp_df
                    df_flag[period] = 1
                    update_account_info(Fubon_account)
                    vwap_trend(df_fubon_1m)
                    close_ratio = current_close_ratio(df_fubon_1m)
                    shadow_sig = candle_shadow_signal(df_fubon_1m)
                elif period == PERIOD_5M:
                    df_fubon_5m = tmp_df
                    df_flag[period] = 1
                elif period == PERIOD_15M:
                    df_fubon_15m = tmp_df
                    df_flag[period] = 1

            # show some data
            show_user_settings()
            show_account_info()
            show_realtime(realtime_candle)

            # 在交易時段結束前1分鐘平倉
            if before_end_of_market(Userinput_Market, now):
                print(f"[{now.strftime('%H:%M:%S')}] Closing positions before the end of market...")
                close_all_position()
                time.sleep(60)
                continue

            # 檢查是否在使用者想要的交易時間
            if not is_trading_time(Userinput_Market, now):
                restart_processes_flag = 1

                print(df_twse.tail(5))
                print('==============================================================================')
                print(df_fubon_5m.tail(5))
                print('==============================================================================')
                print(f"[{now.strftime('%H:%M:%S')}] Not in trading time now...")

                time.sleep(60)
                os.system('cls')
                continue

            # 重啟processes以重置所有資料，避免舊資料影響計算
            if restart_processes_flag:
                restart_processes_flag = 0
                processes = restart_all_processes(processes, data_queue, realtime_candle)
                continue


            # 等同分鐘資料都到齊才設置 Last_executed_minute flag
            if now.minute % 15 == 0 and now.minute != Last_executed_minute:
                if is_data_ready(now, [[df_fubon_1m, PERIOD_1M],\
                                      [df_fubon_5m, PERIOD_5M],\
                                      [df_fubon_15m, PERIOD_15M]]):
                    Last_executed_minute = now.minute
                    # print('1,5,15m data is all updated')
                    # show_candles(realtime_candle, df_twse, df_fubon_1m, df_fubon_5m, df_fubon_15m)
                    # time.sleep(10)
            
            elif now.minute % 5 == 0 and now.minute != Last_executed_minute:
                if is_data_ready(now, [[df_fubon_1m, PERIOD_1M],\
                                      [df_fubon_5m, PERIOD_5M]]):
                    Last_executed_minute = now.minute
                    # print('1,5m data is all updated')
                    # show_candles(realtime_candle, df_twse, df_fubon_1m, df_fubon_5m, df_fubon_15m)
                    # time.sleep(10)

            # show some df key data

            # dfs = df_twse.tail(5)
            # print(dfs)
            # print('==============================================================================')
            dfs_1 = df_fubon_1m.tail(15)
            if KD_KEY in dfs_1.columns:
                print(dfs_1)
                print(f'1m trend: {kd_relation(dfs_1)}')
                print(f'1m atr: {dfs_1.iloc[-1][ATR_KEY]}, adx: {dfs_1.iloc[-1][ADX_KEY]}')
                print(f'{dfs_1[KD_KEY]}')
                print('==============================================================================')
            # dfs_5 = df_fubon_5m.tail(3)
            # if KD_KEY in dfs_5.columns:
            #     print(dfs_5)
            #     print(f'5m trend: {kd_relation(dfs_5)}')
            #     print(f'5m atr: {dfs_5.iloc[-1][ATR_KEY]}, adx: {dfs_5.iloc[-1][ADX_KEY]}')
            #     print(f'{dfs_5[KD_KEY]}')
            #     print('==============================================================================')

            ### 策略區段開始 ###

            # check for max stop loss
            chk_max_stop_loss(realtime_candle)

            traded = 0

            if shadow_sig: # sig comes every 1 minute
                if shadow_sig == 1:
                    direct_trading(1)
                    traded = 1
                elif shadow_sig == -1:
                    direct_trading(-1)
                    traded = 1

                shadow_sig = 0

                if traded:
                    df_flag[PERIOD_1M] = 0
                    df_flag[PERIOD_5M] = 0

            if not traded:
                if is_sideways_market(df_fubon_1m) and df_flag[PERIOD_1M]:
                    df_flag[PERIOD_1M] = 0
                    df_flag[PERIOD_5M] = 0
                    if Buy_at and close_ratio >= 90:
                        close_position(-1)
                    elif Sell_at and close_ratio <= 10:
                        close_position(1)

                elif df_flag[PERIOD_5M] and Last_executed_minute == now.minute:
                    multi_kd_strategy(df_fubon_1m, df_fubon_5m, df_fubon_15m, now)
                    df_flag[PERIOD_1M] = 0
                    df_flag[PERIOD_5M] = 0

                elif df_flag[PERIOD_1M]:
                    multi_kd_strategy(df_fubon_1m, df_fubon_5m, df_fubon_15m, now)
                    df_flag[PERIOD_1M] = 0

            print(f'VWAP trend: {VWAP_trend}')
            print(f'Close price ratio in {CLOSE_RATIO_WINDOW}m: {close_ratio}%')
            ### 策略區段結束 ###

            # adx_trend = np.nan
            # if ADX_KEY in dfs_1.columns:
            #     adx_trend = dfs_1.iloc[-1][ADX_KEY]

            # # check for close positiion
            # if Buy_at or Sell_at:
            #     if adx_trend and adx_trend < 25:
            #         if sig:= atr_fixed_stop(realtime_candle, df_fubon_1m):
            #             close_position(sig)
            #         elif sig:= bband_stop(df_fubon_1m):
            #             close_position(sig)
            #         else:
            #             sig = kd_cross_signal(df_fubon_1m)
            #             if Buy_at and sig == -1:
            #                 close_position(-1)
            #             elif Sell_at and sig == 1:
            #                 close_position(1)
            #     else:
            #         if sig:= atr_trailing_stop(realtime_candle, df_fubon_5m):
            #             close_position(sig)


            # if np.isnan(adx_trend) or adx_trend > 25:

            #     if df_flag[PERIOD_5M] and Last_executed_minute == now.minute:
            #         multi_kd_strategy(df_fubon_1m, df_fubon_5m, df_fubon_15m, now)
            #         df_flag[PERIOD_1M] = 0
            #         df_flag[PERIOD_5M] = 0
            #     elif df_flag[PERIOD_1M]:
            #         multi_kd_strategy(df_fubon_1m, df_fubon_5m, df_fubon_15m, now)
            #         df_flag[PERIOD_1M] = 0
            
            # else:
            #     if len(df_fubon_1m) > 2:
            #         consolidation_strategy_bb(df_fubon_1m)
            #         print(f'upband: {df_fubon_1m.iloc[-1][BB_KEY][1]}, lowband: {df_fubon_1m.iloc[-1][BB_KEY][2]}')

            time.sleep(0.01)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")
    