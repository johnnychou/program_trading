import sys
import datetime
import multiprocessing
import fubon

TRADE_MARKET_SET = ('day', 'night', 'main', 'all')
TRADE_DIRECTION_SET = ('buy', 'sell', 'auto')
TRADE_PRODUCT_SET = ('TXF', 'MXF', 'TMF')

if __name__ == '__main__':
    Buy_at = []
    Sell_at = []
    Trade_time_set = []
    Trade_record = []

    Trading_market_input = input('Trading time day/night/main/all: ').lower()
    while Trading_market_input not in TRADE_MARKET_SET:
        print('Error, please input legal value.')
        Trading_market_input = input('Trading time day/night/main/all: ').lower()

    Direction_input = input('Position choose buy/sell/auto: ').lower()
    while Direction_input not in TRADE_DIRECTION_SET:
        print('Error, please input legal value.')
        Direction_input = input('Position choose buy/sell/auto: ').lower()

    Product_input = input('Product choose TXF/MXF/TMF: ').upper()
    while Product_input not in TRADE_PRODUCT_SET:
        print('Error, please input legal value.')
        Product_input = input('Product choose TXF/MXF/TMF: ').upper()

    #postition amount
    while True:
        try:
            OrderAmount = int(input('Order amount: '))
            while OrderAmount not in range(1, 4):
                print('Error, please input integer 1~3.')
                OrderAmount = int(input('Order amount: '))
            break
        except:
            print('Error, please input integer 1~3.')

    
    fubon_acc = fubon.Fubon_trade(Product_input)

    Buy_at, Sell_at = fubon_acc.update_position_holded()
    print(f'Buy: {Buy_at}')
    print(f'Sell: {Sell_at}')
    equity, margin = fubon_acc.update_margin_equity()
    print(f'equity: {equity}')
    print(f'margin: {margin}')
    
    # margin = [15350, 0]
    # if margin[0]:
    #     max_lots = equity // (margin[0]*1.2)
    #     print(f'max_lots: {max_lots}')

    trade_price = fubon_acc.get_order_results()
    print(f'trade_price: {trade_price}')
