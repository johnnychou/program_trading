import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time
import multiprocessing

import twse
import fubon

PRODUCT = 'MXF'
TWSE_PERIOD = 30
FUBON_PERIOD_1 = 1
FUBON_PERIOD_2 = 5

if __name__ == '__main__':
    Processes = []
    data_queue = multiprocessing.Queue()
    realtime_candle = multiprocessing.Manager().dict() #shared dict

    twse_30s = twse.TWSE(TWSE_PERIOD, PRODUCT, 'twse', data_queue, realtime_candle)
    twse_p = multiprocessing.Process(target=twse_30s.get_candles)
    twse_p.daemon = True
    twse_p.start()
    Processes.append(twse_p)

    fubon_1m = fubon.Fubon_api(FUBON_PERIOD_1, PRODUCT, data_queue)
    fubon_p1 = multiprocessing.Process(target=fubon_1m.get_candles)
    fubon_p1.daemon = True
    fubon_p1.start()
    Processes.append(fubon_p1)

    candles_twse_30s = []
    candles_fubon_1m = []

    try:
        while True:
            print(realtime_candle)
            print('================================================================================================================================')
            for i in candles_twse_30s:
                print(f"{i}")
            print('================================================================================================================================')
            for i in candles_fubon_1m:
                print(f"{i}")

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_list = data_queue.get()
                print(f"received period[{period}] data")
                if period == TWSE_PERIOD:
                    candles_twse_30s = tmp_list
                elif period == FUBON_PERIOD_1:
                    candles_fubon_1m = tmp_list

            time.sleep(0.1)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")