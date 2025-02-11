import sys
import datetime
import multiprocessing
import fubon

if __name__ == '__main__':
    data_queue = multiprocessing.Queue()
    fubon_1m = fubon.Fubon_api('1', 'MXF', data_queue)
    print(fubon_1m.get_trade_symbol())
    # fubon_5m.update_position_holded()
    # fubon_5m.chk_inventories()
    # fubon_5m.chk_remainings()
    # candles = fubon_5m.get_candles()
    # for i in candles:
    #     print(i)
    fubon_1m.subscribe_candles()
    

    
