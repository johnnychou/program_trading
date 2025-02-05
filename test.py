import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time
import multiprocessing

import candles

TWSE_PERIOD = 30

if __name__ == '__main__':
    Processes = []
    data_queue = multiprocessing.Queue()
    shared_data = multiprocessing.Manager().dict()

    twse_f = candles.CandleFetcher(TWSE_PERIOD, 'TXF', 'twse', data_queue, shared_data)
    twse_p = multiprocessing.Process(target=twse_f.get_candles)
    twse_p.daemon = True
    twse_p.start()
    Processes.append(twse_p)

    candles_twse = []

    try:
        while True:
            print(shared_data)
            print('================================================================================================================================')
            for i in candles_twse:
                print(f"{i}")

            while not data_queue.empty():  # 非阻塞檢查Queue
                period, tmp_list = data_queue.get()
                print(f"received period[{period}] data")
                if period == TWSE_PERIOD:
                    candles_twse = tmp_list

            time.sleep(0.1)
            os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")