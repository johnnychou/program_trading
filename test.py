import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time
from multiprocessing import Process, Queue

import candles

if __name__ == '__main__':
    fetchers = []
    data_queue = Queue()

    twse_30s = candles.CandleFetcher(3, 'TXF', 'twse', data_queue)
    twse = Process(target=twse_30s.get_candles)
    twse.daemon = True
    twse.start()
    fetchers.append(twse)

    candles_30s = []

    try:
        while True:
            while not data_queue.empty():  # 非阻塞檢查Queue
                os.system('cls')
                period, tmp_list = data_queue.get()
                print(f"received period[{period}] data")
                if period == 3:
                    candles_30s = tmp_list
                    for i in candles_30s:
                        print(f"{i}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("All processes stopped.")