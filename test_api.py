import sys
import datetime
import multiprocessing
import fubon

if __name__ == '__main__':
    data_queue = multiprocessing.Queue()
    fubon_5m = fubon.Fubon_api('5', 'MXF', data_queue)
    print(fubon_5m.get_trade_symbol())
    fubon_5m.update_position_holded()
    fubon_5m.chk_inventories()
    fubon_5m.chk_remainings()
    print(fubon_5m.get_candles())

    
