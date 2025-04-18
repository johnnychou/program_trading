import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time
import multiprocessing
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import twse
import fubon
import indicators

PRODUCT = 'MXF'
TWSE_PERIOD = '30s'
FUBON_PERIOD_1 = '1m'
FUBON_PERIOD_5 = '5m'
FUBON_PERIOD_15 = '15m'


if __name__ == '__main__':
    Processes = []
    data_queue = multiprocessing.Queue()
    realtime_candle = multiprocessing.Manager().dict() #shared dict

    fubon_1m = fubon.Fubon_api(FUBON_PERIOD_1, PRODUCT, data_queue)
    fubon_p1 = multiprocessing.Process(target=fubon_1m.get_candles)
    fubon_p1.daemon = True
    fubon_p1.start()
    Processes.append(fubon_p1)

    df_fubon_1m = pd.DataFrame()


    try:
        while True:
            print(f"{df_fubon_1m}")

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_df = data_queue.get()
                print(f"received period[{period}] data")
                print(f"{tmp_df}")
                time.sleep(1)
                if period == TWSE_PERIOD:
                    df_twse_30s = tmp_df
                elif period == FUBON_PERIOD_1:
                    df_fubon_1m = tmp_df
                elif period == FUBON_PERIOD_5:
                    df_fubon_5m = tmp_df
                elif period == FUBON_PERIOD_15:
                    df_fubon_15m = tmp_df

            time.sleep(1)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")