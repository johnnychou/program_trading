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
    global Userinput_Market, Userinput_Direction, Userinput_Product, Userinput_OrderAmount

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
    print('==================================')
    return

def show_account_info():
    if Buy_at:
        position = f'Buy: {Buy_at}'
    elif Sell_at:
        position = f'Sell: {Sell_at}'
    print(f'Position: {position}')
    print('==================================')
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

def chk_trade_signal(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    if KD_KEY in df_fubon_1m.columns:
        column = df_fubon_1m[KD_KEY]
        if len(column) >= 3:
            print(column.iloc[-1])
            print(column.iloc[-2])
            print(column.iloc[-3])
            #time.sleep(10)
    return


if __name__ == '__main__':
    user_input_settings()

    Fubon_account = fubon.Fubon_trade(Userinput_Product)
    
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

                sig = chk_trade_signal(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)

            show_user_settings()
            show_account_info()
            show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)

    except KeyboardInterrupt:
        print("All processes stopped.")
    