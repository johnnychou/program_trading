import os
import sys
import datetime
import multiprocessing
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import fubon

if __name__ == '__main__':
    data_queue = []
    fubon_1m = fubon.Fubon_data('1m', 'TMF', data_queue)
    # print(fubon_1m.get_trade_symbol())
    # fubon_1m.update_position_holded()
    # fubon_1m.chk_inventories()
    # fubon_1m.chk_remainings()

    candles = fubon_1m.get_candles_list()
    new_row = candles[-1]
    print('=====')
    print(new_row)
    new_df = pd.DataFrame([new_row])
    print('=====')
    print(new_df)
    print('=====')
    # for i in candles:
    #     print(i)


    

    
