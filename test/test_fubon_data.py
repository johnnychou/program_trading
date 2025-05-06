import os
import sys
import datetime
import multiprocessing
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import fubon
import main as m

if __name__ == '__main__':
    # data_queue = []
    # fubon_1m = fubon.Fubon_data('1m', 'TMF', data_queue)
    # candles = fubon_1m.get_candles_list()
    # new_row = candles[-1]
    # print('=====')
    # print(new_row)
    # new_df = pd.DataFrame([new_row])
    # print('=====')
    # print(new_df)
    # print('=====')

    processes = []
    data_queue = multiprocessing.Queue()
    df = pd.DataFrame()

    fubon_instance = fubon.Fubon_data('1m', 'TMF', data_queue)
    process = multiprocessing.Process(target=fubon_instance.get_candles)
    process.daemon = True
    process.start()
    processes.append([process, '1m'])
    while True:
        while not data_queue.empty():  # 非阻塞檢查Queue
            period, tmp_df = data_queue.get()
            if period == '1m':
                df = tmp_df
                print(df)


    

    
