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
TWSE_PERIOD = '30s'
FUBON_PERIOD_1 = '1m'
FUBON_PERIOD_5 = '5m'
FUBON_PERIOD_15 = '15m'

def indicators_calculation(df):
    indicators.indicator_ma(df, 10)
    indicators.indicator_ema(df, 5)
    indicators.indicator_atr(df, 14)
    indicators.indicator_rsi(df, 10)
    indicators.indicator_kd(df, 9)
    indicators.indicator_macd(df)
    indicators.indicator_bollingsband(df, 20)
    return


if __name__ == '__main__':

    #Fubon_data = fubon.Fubon_trade('TMF')


    Processes = []
    data_queue = multiprocessing.Queue()
    realtime_candle = multiprocessing.Manager().dict() #shared dict

    twse_30s = twse.TWSE(TWSE_PERIOD, PRODUCT, 'twse', data_queue, realtime_candle)
    twse_p = multiprocessing.Process(target=twse_30s.get_candles)
    twse_p.daemon = True
    twse_p.start()
    Processes.append(twse_p)

    fubon_1m = fubon.Fubon_data(FUBON_PERIOD_1, PRODUCT, data_queue)
    fubon_p1 = multiprocessing.Process(target=fubon_1m.get_candles)
    fubon_p1.daemon = True
    fubon_p1.start()
    Processes.append(fubon_p1)

    fubon_5m = fubon.Fubon_data(FUBON_PERIOD_5, PRODUCT, data_queue)
    fubon_p5 = multiprocessing.Process(target=fubon_5m.get_candles)
    fubon_p5.daemon = True
    fubon_p5.start()
    Processes.append(fubon_p5)

    fubon_15m = fubon.Fubon_data(FUBON_PERIOD_15, PRODUCT, data_queue)
    fubon_p15 = multiprocessing.Process(target=fubon_15m.get_candles)
    fubon_p15.daemon = True
    fubon_p15.start()
    Processes.append(fubon_p15)

    df_twse_30s = pd.DataFrame()
    df_fubon_1m = pd.DataFrame()
    df_fubon_5m = pd.DataFrame()
    df_fubon_15m = pd.DataFrame()

    try:
        while True:
            print(realtime_candle)
            print('===30s=============================================================================================================================')
            print(f"{df_twse_30s}")
            print('===1m=============================================================================================================================')
            print(f"{df_fubon_1m}")
            print('===5m=============================================================================================================================')
            print(f"{df_fubon_5m}")
            print('===15m=============================================================================================================================')
            print(f"{df_fubon_15m}")

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_df = data_queue.get()
                # print(f"received period[{period}] data")
                # print(f"{tmp_df}")
                if period == TWSE_PERIOD:
                    df_twse_30s = tmp_df
                elif period == FUBON_PERIOD_1:
                    df_fubon_1m = tmp_df
                elif period == FUBON_PERIOD_5:
                    df_fubon_5m = tmp_df
                elif period == FUBON_PERIOD_15:
                    df_fubon_15m = tmp_df

            time.sleep(0.1)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")