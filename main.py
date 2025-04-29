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
            if period_key == PERIOD_30S:
                create_twse_process(period_key, Userinput_Product, data_queue, realtime_candle, processes)
            else:
                create_fubon_process(period_key, Userinput_Product, data_queue, processes)
            print(f'Process (Period: {period_key}) is restarted.')

        winsound.Beep(5000,1000)
        time.sleep(15)

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
    print('====================================================================')
    print(realtime_candle)
    print('====================================================================')
    return

def show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    global Last_price
    if 'lastprice' in realtime_candle:
        Last_price = realtime_candle['lastprice']
    print(f'lastprice: {Last_price}')
    print('==================================')
    print(realtime_candle)
    print('===30s============================')
    print(f"{df_twse_30s.tail(5)}")
    print('===1m=============================')
    print(f"{df_fubon_1m.tail(5)}")
    print('===5m=============================')
    print(f"{df_fubon_5m.tail(5)}")
    print('===15m============================')
    print(f"{df_fubon_15m.tail(5)}")
    return

def show_user_settings():
    print('====================================================================')
    print(f'Product: {Userinput_Product}/{OrderAmount},\
            Market: {Userinput_Market},\
            Direction: {Userinput_Direction}')

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
    print('====================================================================')
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

def open_position(sig):
    global Trade_times
    if (Userinput_Direction == 'buy' and sig == -1) or\
         (Userinput_Direction == 'sell' and sig == 1):
        return 0
    if Buy_at or Sell_at:
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
    return

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
        # --- 核心計算邏輯 ---
        close_dt = datetime.datetime.combine(dummy_date, close_time)
        start_of_last_minute_dt = close_dt - datetime.timedelta(minutes=1)
        start_of_last_minute_time = start_of_last_minute_dt.time()
        # --- 結束核心計算 ---

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
            close_position(-1)
            return 1
    elif Sell_at:
        entry_price = Sell_at[0]
        close_price = entry_price + atr * 1.5
        if lastprice >= close_price:
            close_position(1)
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
            close_position(-1)
            return 1
    elif Sell_at:
        entry_price = Sell_at[0]
        close_price = entry_price - atr * 2
        if lastprice <= close_price:
            close_position(1)
            return 1
    return 0

def atr_trailing_stop(realtime_candle, df):
    global Max_profit_pt
    if not Buy_at and not Sell_at:
        return
    if 'lastprice' not in realtime_candle:
        return 0
    if ATR_KEY not in df.columns:
        return 0
    
    lastprice = realtime_candle['lastprice']
    last_valid_idx = df[ATR_KEY].last_valid_index()
    atr = df.loc[last_valid_idx, ATR_KEY]

    if Buy_at:
        Max_profit_pt = max(lastprice, Buy_at[0], Max_profit_pt)
        stop_price = Max_profit_pt - atr * 1.5
        print(f'Max Profit at: {Max_profit_pt}, {(Max_profit_pt-Buy_at[0])*PT_price}')
        print(f'ATR trailing stop price: {stop_price}')
        if lastprice <= stop_price:
            close_position(-1)
            Max_profit_pt = 0
            print(f'ATR trailing stopped at: {lastprice}')
            return

    elif Sell_at:
        if not Max_profit_pt:
            Max_profit_pt = min(lastprice, Sell_at[0])
        else:
            Max_profit_pt = min(lastprice, Sell_at[0], Max_profit_pt)
        stop_price = Max_profit_pt + atr * 1.5
        print(f'Max Profit at: {Max_profit_pt}, {(Sell_at[0]-Max_profit_pt)*PT_price}')
        print(f'ATR trailing stop price: {stop_price}')
        if lastprice >= stop_price:
            close_position(1)
            Max_profit_pt = 0
            print(f'ATR trailing stopped at: {lastprice}')
            return

    return


def atr_fixed_stop(realtime_candle, df):
    if not Buy_at and not Sell_at:
        return
    chk_stop_loss(realtime_candle, df)
    chk_take_profit(realtime_candle, df)


def trend_or_consolidation_adx(df):
    if ADX_KEY not in df.columns:
        return
    adx = df.iloc[-1][ADX_KEY]
    pre_adx = df.iloc[-2][ADX_KEY]
    if adx and adx > 25 and adx > pre_adx: 
        return 'trend'
    return 'consolidation'

def trend_or_consolidation_bb(df):
    if len(df) < 2:
        return
    if BB_KEY not in df.columns:
        return
    bb_up = df.iloc[-1][BB_KEY][1]
    bb_bot = df.iloc[-1][BB_KEY][2]
    pre_bb_up = df.iloc[-2][BB_KEY][1]
    pre_bb_bot = df.iloc[-2][BB_KEY][2]
    band = bb_up - bb_bot
    pre_band = pre_bb_up - pre_bb_bot
    print(f'band: {round(band, 2)}, pre_band: {round(pre_band, 2)}')
    if band > 60 and band >= (pre_band*0.8):
        return 'trend'
    return 'consolidation'

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
    if pre_k <= pre_d and k > d and rsv > 85:
        return -1
    
    # death cross
    if pre_k >= pre_d and k < d and rsv < 15:
        return 1

    return 0

def consolidation_strategy_bb(df):
    if len(df) < 2:
        return
    if BB_KEY not in df.columns:
        return
    up = df.iloc[-1][BB_KEY][1]
    bot = df.iloc[-1][BB_KEY][2]
    close = df.iloc[-1]['close']

    pre_up = df.iloc[-2][BB_KEY][1]
    pre_bot = df.iloc[-2][BB_KEY][2]
    pre_high = df.iloc[-2]['high']
    pre_low = df.iloc[-2]['low']

    # buy
    if pre_low <= pre_bot and close > bot:
        return 1
    # sell
    elif pre_high >= pre_up and close < up:
        return -1
    return 0

def trend_strategy(df):
    if len(df) < 2:
        return
    if EMA2_KEY not in df.columns:
        return
    if VWAP_KEY not in df.columns:
        return
    if RSI_KEY not in df.columns:
        return
    
    signal = 0

    if (df.iloc[-1]['close'] > df.iloc[-2]['high']) and\
         (df.iloc[-1]['close'] > df.iloc[-1][EMA2_KEY]) and\
         (df.iloc[-1]['close'] > df.iloc[-1][VWAP_KEY]) and\
         (df.iloc[-1][RSI_KEY] < 70):
        signal = 1
    elif (df.iloc[-1]['close'] < df.iloc[-2]['low']) and\
         (df.iloc[-1]['close'] < df.iloc[-1][EMA2_KEY]) and\
         (df.iloc[-1]['close'] < df.iloc[-1][VWAP_KEY]) and\
         (df.iloc[-1][RSI_KEY] > 30):
        signal = -1

    return signal


if __name__ == '__main__':

    user_input_settings()
    Fubon_account = fubon.Fubon_trade(Userinput_Product)
    update_account_info(Fubon_account)
    
    processes = []
    restart_list = []
    data_queue = multiprocessing.Queue()                # shared data queue
    realtime_candle = multiprocessing.Manager().dict()  # shared dict

    create_twse_process(PERIOD_30S, Userinput_Product, data_queue, realtime_candle, processes)
    create_fubon_process(PERIOD_1M, Userinput_Product, data_queue, processes)
    create_fubon_process(PERIOD_5M, Userinput_Product, data_queue, processes)
    create_fubon_process(PERIOD_15M, Userinput_Product, data_queue, processes)

    df_twse_30s = pd.DataFrame()
    df_fubon_1m = pd.DataFrame()
    df_fubon_5m = pd.DataFrame()
    df_fubon_15m = pd.DataFrame()

    df_flag = {
        PERIOD_30S: 0,
        PERIOD_1M: 0,
        PERIOD_5M: 0,
        PERIOD_15M: 0,
    }

    # last_minute_checked = -1

    try:
        while True:
            now = datetime.datetime.now()

            # 隨時檢查processes
            processes = check_process_alive(processes, data_queue, realtime_candle)

            # 每分鐘檢查一次processes
            # if now.minute != last_minute_checked :
            #     processes = check_process_alive(processes, data_queue, realtime_candle)
            #     last_minute_checked = now.minute

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_df = data_queue.get()
                # print(f"received period[{period}] data")
                # print(f"{tmp_df}")
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

            if not is_trading_time(Userinput_Market, now):
                show_account_info()
                show_realtime(realtime_candle)
                print(df_fubon_5m.tail(5))

                print(f"[{now.strftime('%H:%M:%S')}] Not in trading time now...")
                time.sleep(60)
                os.system('cls')
                continue

            if before_end_of_market(Userinput_Market, now):
                print(f"[{now.strftime('%H:%M:%S')}] Closing positions before the end of market...")
                close_all_position()
                time.sleep(60)
                continue

            show_user_settings()
            show_account_info()
            show_realtime(realtime_candle)
            #show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)

            dfs_1 = df_fubon_1m.tail(5)
            print(dfs_1)
            print('====================================================================')
            dfs_5 = df_fubon_5m.tail(5)
            print(dfs_5)
            print('====================================================================')

            if len(df_fubon_1m) > 3 and len(df_fubon_5m) > 3:
               
                # show some key data
                for index, row_series in dfs_1.iterrows():
                    print(f'BB: {row_series[BB_KEY]}, KD: {row_series[KD_KEY]}')
                atr = dfs_1.iloc[-1][ATR_KEY]
                adx = dfs_1.iloc[-1][ADX_KEY]
                print(f'1_min: ATR_{ATR_PERIOD}: {atr}, ADX_{ADX_PERIOD}: {adx}')
                print('====================================================================')

                for index, row_series in dfs_5.iterrows():
                    print(f'EMA_5: {row_series[EMA_KEY]}, EMA_20: {row_series[EMA2_KEY]}, RSI: {row_series[RSI_KEY]}')
                atr_5 = dfs_5.iloc[-1][ATR_KEY]
                adx_5 = dfs_5.iloc[-1][ADX_KEY]
                print(f'5_min: ATR_{ATR_PERIOD}: {atr_5}, ADX_{ADX_PERIOD}: {adx_5}')
                print('====================================================================')
                
                trade_type = trend_or_consolidation_bb(df_fubon_1m)

                print(f'Market type: {trade_type}')

                # check for close position
                if trade_type == 'trend':
                    atr_trailing_stop(realtime_candle, df_fubon_5m)
                else:
                    atr_fixed_stop(realtime_candle, df_fubon_1m)

                # check for open position
                if Last_executed_minute == now.minute and not Buy_at and not Sell_at:
                    if trade_type == 'trend':
                        if df_flag[PERIOD_5M]:
                            if sig := trend_strategy(df_fubon_5m):
                                open_position(sig)
                            df_flag[PERIOD_5M] = 0
                    else:
                        if df_flag[PERIOD_1M]:
                            if sig := consolidation_strategy_bb(df_fubon_1m):
                                open_position(sig)
                            df_flag[PERIOD_1M] = 0
                            

            time.sleep(0.01)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")
    