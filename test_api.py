import sys
import datetime
import multiprocessing
import fubon

if __name__ == '__main__':
    data_queue = multiprocessing.Queue()
    fubon_5m = fubon.Fubon_api(5, 'TXF', data_queue)
    print(fubon_5m.get_trade_symbol())
    input()
    
