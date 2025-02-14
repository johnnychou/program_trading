import sys
import datetime
import multiprocessing
import fubon

if __name__ == '__main__':
    data_queue = multiprocessing.Queue()
    fubon_1m = fubon.Fubon_api(1, 'MXF', data_queue)
    # print(fubon_1m.get_trade_symbol())
    # fubon_1m.update_position_holded()
    # fubon_1m.chk_inventories()
    # fubon_1m.chk_remainings()
    candles = fubon_1m.get_candles()
    for i in candles:
        print(i)

    

    
