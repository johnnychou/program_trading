import sys
import datetime
import multiprocessing
import fubon

if __name__ == '__main__':
    fubon_acc = fubon.Fubon_trade('TMF')
    Buy_at, Sell_at = fubon_acc.update_position_holded()
    print(Buy_at)
    print(Sell_at)
    