import sys
import datetime
import multiprocessing
import fubon

TRADE_MARKET_SET = ('day', 'night', 'main', 'all')
TRADE_DIRECTION_SET = ('buy', 'sell', 'auto')
TRADE_PRODUCT_SET = ('TXF', 'MXF', 'TMF')
Userinput_Market = None
Userinput_Direction = None
Userinput_Product = None
Userinput_OrderAmount = 0

def get_max_lots(account):
    max_lots = 0
    balance, margin = account.update_margin_equity()
    if margin[0]:
        max_lots = balance // (margin[0]*1.2)
        print(f'max_lots: {max_lots}')
    return max_lots

def show_account_info(account):
    Buy_at, Sel_at = account.update_position_holded()
    Balance, margin = account.update_margin_equity()

    position = 'None'

    if Buy_at:
        position = f'Buy{Buy_at}'
    if Sel_at:
        position = f'Sell{Sel_at}'

    print(f'Product: {Userinput_Product}, Amount: {Userinput_OrderAmount}, Market: {Userinput_Market}, Direction: {Userinput_Direction}')
    print(f'Balance: {Balance}, Position: {position}')
    return

def get_order_result(account):
    trade_price = account.get_order_results()
    print(f'trade_price: {trade_price}')
    return trade_price



if __name__ == '__main__':
    Buy_at = []
    Sell_at = []
    Trade_time_set = []
    Trade_record = []

    Userinput_Market = input('Trading time day/night/main/all: ').lower()
    while Userinput_Market not in TRADE_MARKET_SET:
        print('Error, please input legal value.')
        Userinput_Market = input('Trading time day/night/main/all: ').lower()

    Userinput_Direction = input('Position choose buy/sell/auto: ').lower()
    while Userinput_Direction not in TRADE_DIRECTION_SET:
        print('Error, please input legal value.')
        Userinput_Direction = input('Position choose buy/sell/auto: ').lower()

    Userinput_Product = input('Product choose TXF/MXF/TMF: ').upper()
    while Userinput_Product not in TRADE_PRODUCT_SET:
        print('Error, please input legal value.')
        Userinput_Product = input('Product choose TXF/MXF/TMF: ').upper()

    fubon_acc = fubon.Fubon_trade(Userinput_Product)

    #postition amount
    while True:
        try:
            Userinput_OrderAmount = int(input('Order amount: '))
            if Userinput_OrderAmount == -1:
                Userinput_OrderAmount = get_max_lots(fubon_acc)
                break
            while Userinput_OrderAmount not in range(1, 4):
                print('Error, please input integer 1~3.')
                Userinput_OrderAmount = int(input('Order amount: '))
            break
        except:
            print('Error, please input integer 1~3.')

    show_account_info(fubon_acc)
    price = fubon_acc.get_order_results()
    print(price)





