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
FUBON_PERIOD_5 = 5
FUBON_PERIOD_15 = 15

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

    fubon_5m = fubon.Fubon_api(FUBON_PERIOD_5, PRODUCT, data_queue)
    fubon_p5 = multiprocessing.Process(target=fubon_5m.get_candles)
    fubon_p5.daemon = True
    fubon_p5.start()
    Processes.append(fubon_p5)

    fubon_15m = fubon.Fubon_api(FUBON_PERIOD_15, PRODUCT, data_queue)
    fubon_p15 = multiprocessing.Process(target=fubon_15m.get_candles)
    fubon_p15.daemon = True
    fubon_p15.start()
    Processes.append(fubon_p15)

    candles_twse_30s = []
    candles_fubon_1m = []
    candles_fubon_5m = []
    candles_fubon_15m = []

    try:
        while True:
            print(realtime_candle)
            # print('===30s=============================================================================================================================')
            # for i in candles_twse_30s:
            #     print(f"{i}")
            # print('===1m=============================================================================================================================')
            # for i in candles_fubon_1m:
            #     print(f"{i}")
            # print('===5m=============================================================================================================================')
            # for i in candles_fubon_5m:
            #     print(f"{i}")
            # print('===15m=============================================================================================================================')
            # for i in candles_fubon_15m:
            #     print(f"{i}")

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_list = data_queue.get()
                print(f"received period[{period}] data")
                if period == TWSE_PERIOD:
                    candles_twse_30s = tmp_list
                elif period == FUBON_PERIOD_1:
                    candles_fubon_1m = tmp_list
                elif period == FUBON_PERIOD_5:
                    candles_fubon_5m = tmp_list
                elif period == FUBON_PERIOD_15:
                    candles_fubon_15m = tmp_list

            time.sleep(0.1)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")