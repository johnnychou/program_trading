import sys
import datetime
import multiprocessing
import fubon

if __name__ == '__main__':
    Buy_at = []
    Sell_at = []
    Trade_time_set = []
    Trade_record = []
    fubon_acc = fubon.Fubon_trade('TMF')

    Buy_at, Sell_at = fubon_acc.update_position_holded()
    print(Buy_at)
    print(Sell_at)
    equity, margin = fubon_acc.update_margin_equity()
    print(equity)
    print(margin)
    
    margin = [15350, 0]
    if margin[0]:
        max_lots = equity // (margin[0]*1.2)
        print(f'max_lots: {max_lots}')

    trade_price = fubon_acc.get_order_results()
    print(trade_price)
