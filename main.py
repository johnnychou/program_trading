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

TRADE_MARKET_SET = ('day', 'night', 'main', 'all')
TRADE_DIRECTION_SET = ('buy', 'sell', 'auto')
TRADE_PRODUCT_SET = ('TXF', 'MXF', 'TMF')

TWSE_PERIOD_30S = '30s'
FUBON_PERIOD_1M = '1m'
FUBON_PERIOD_5M = '5m'
FUBON_PERIOD_15M = '15m'

MA_PERIOD = 10
EMA_PERIOD = 5
EMA2_PERIOD = 20
ATR_PERIOD = 14
RSI_PERIOD = 10
KD_PERIOD = (9, 3, 3)
MACD_PERIOD = (12, 26, 9)
BB_PERIOD = (20, 2)

MA_KEY = indicators.MA_PREFIX + str(MA_PERIOD)
EMA_KEY = indicators.EMA_PREFIX + str(EMA_PERIOD)
EMA2_KEY = indicators.EMA_PREFIX + str(EMA2_PERIOD)
ATR_KEY = indicators.ATR_PREFIX + str(ATR_PERIOD)
KD_KEY = indicators.KD_PREFIX + str(KD_PERIOD[0])
RSI_KEY = indicators.RSI_PREFIX + str(RSI_PERIOD)
BB_KEY = indicators.BB_PREFIX + str(BB_PERIOD[0])
MACD_KEY = indicators.MACD_PREFIX + str(MACD_PERIOD[0])

Userinput_Market = None
Userinput_Direction = None
Userinput_Product = None
Userinput_OrderAmount = 0

Last_price = 0
Profit = 0
Trade_record = []

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

def user_input():
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

    return

def chk_trade_signal(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    if KD_KEY in df_fubon_1m.columns:
        column = df_fubon_1m[KD_KEY]
        if len(column) >= 3:
            print(column.iloc[-1])
            print(column.iloc[-2])
            print(column.iloc[-3])
            time.sleep(10)
    return


if __name__ == '__main__':

    user_input()
    fubon_acc = fubon.Fubon_trade(Userinput_Product)

    #postition amount
    while True:
        try:
            Userinput_OrderAmount = int(input('Order amount 1~3: '))
            while Userinput_OrderAmount not in range(1, 4):
                print('Error, please input integer 1~3.')
                Userinput_OrderAmount = int(input('Order amount 1~3: '))
            break
        except:
            print('Error, please input integer 1~3.')


    Buy_at, Sell_at = fubon_acc.update_position_holded()

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

            
            show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m)

    except KeyboardInterrupt:
        print("All processes stopped.")
    