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

PRODUCT = 'MXF'
TWSE_PERIOD_30S = '30s'
FUBON_PERIOD_1M = '1m'
FUBON_PERIOD_5M = '5m'
FUBON_PERIOD_15M = '15m'

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
    indicators.indicator_ma(df, 10)
    indicators.indicator_ema(df, 5)
    indicators.indicator_ema(df, 20)
    indicators.indicator_atr(df, 14)
    indicators.indicator_rsi(df, 10)
    indicators.indicator_kd(df, 9)
    indicators.indicator_macd(df)
    indicators.indicator_bollingsband(df, 20)
    return df

def show_candles(realtime_candle, df_twse_30s, df_fubon_1m, df_fubon_5m, df_fubon_15m):
    os.system('cls')
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

if __name__ == '__main__':

    Buy_at = []
    Sell_at = []
    Trade_record = []
    
    fubon_acc = fubon.Fubon_trade('TMF')
    Buy_at, Sell_at = fubon_acc.update_position_holded()

    Processes = []
    data_queue = multiprocessing.Queue()                # shared data queue
    realtime_candle = multiprocessing.Manager().dict()  # shared dict

    create_twse_process(TWSE_PERIOD_30S, PRODUCT, 'twse', data_queue, realtime_candle, Processes)
    create_fubon_process(FUBON_PERIOD_1M, PRODUCT, data_queue, Processes)
    create_fubon_process(FUBON_PERIOD_5M, PRODUCT, data_queue, Processes)
    create_fubon_process(FUBON_PERIOD_15M, PRODUCT, data_queue, Processes)

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
            
            #show_candles()

    except KeyboardInterrupt:
        print("All processes stopped.")
    