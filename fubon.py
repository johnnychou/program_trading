import os
import sys
import datetime
import time
import requests as r
import functools
import traceback
import winsound
import pandas as pd

import fubon_neo
from fubon_neo.sdk import FubonSDK, Mode, FutOptOrder
from fubon_neo.constant import TimeInForce, FutOptOrderType, FutOptPriceType, FutOptMarketType, CallPut, BSAction
import utils

sys.path.append("C:\\Users\\ChengWei\\Desktop\\my project")
import accinfo as key

CANDLE_MAX_AMOUNT = 30
MONTH_CODE = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L')

class Fubon_trade(object):
    def __init__(self, product):
        self.Account = None
        self.Acc_futures = None
        self.Restfut = None
        self.Trade_symbol = None
        self.product = product

        self.SDK = FubonSDK()
        self.login_account()
        self.SDK.init_realtime(Mode.Normal)
        self.Restfut = self.SDK.marketdata.rest_client.futopt
        self.Acc_futures = self.get_future_account()
        self.Trade_symbol = self.get_trade_symbol()
        self._set_event()
        return

    def login_account(self, retrytimes=6):
        try:
            self.Account = self.SDK.login(key.id, key.pwd, key.ca, key.ca_pwd)
        except Exception as error:
            print(f"Exception: {error}")
        
        if self.Account.is_success == True:
            self.Account = self.Account.data
        else:
            print("**Login failed** Retry after 10s...")
            time.sleep(10)
            return self.login_account(retrytimes-1)

        #print(f"===Login sucess===\n{self.Account}")
        #time.sleep(1)
        return

    def get_future_account(self):
        for acc in self.Account:
            if acc.account_type == 'futopt':
                #print(f"Future account:\n{acc}")
                return acc
        return None

    def _set_event(self):
        self.SDK.set_on_event(self.on_event)
        self.SDK.set_on_futopt_filled(self.on_filled)
        return

    def handle_exceptions(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exp:
                # Extract the full traceback
                tb_lines = traceback.format_exc().splitlines()

                # Find the index of the line related to the original function
                func_line_index = next((i for i, line in enumerate(tb_lines) if func.__name__ in line), -1)

                # Highlight the specific part in the traceback where the exception occurred
                relevant_tb = "\n".join(tb_lines[func_line_index:])  # Include traceback from the function name

                error_text = f"{func.__name__} exception: {exp}\nTraceback (most recent call last):\n{relevant_tb}"
                print(error_text, file=sys.stderr)
        return wrapper

    #斷線重連
    @handle_exceptions
    def on_event(self, code, content):
        print("=====Event=====")
        print(code)
        print(content)
        if code == "300":
            print("Reconnecting...")
            try:
                self.Account = self.SDK.login(key.id, key.pwd, key.ca, key.ca_pwd)
                self.login_account()
                print("Reconnect successs")
                print(self.Account)
            except Exception as e:
                print("Reconnect failed")
                print(e)
        print("=====Event=====")

    #成交回報
    @handle_exceptions
    def on_filled(code, content):
        print("===Filled===")
        print(code)
        print(content)
        # print(content.filled_no)  # 印出成交流水號
        print("===Filled===")

    def update_margin_equity(self):
        try:
            req = self.SDK.futopt_accounting.query_margin_equity(self.Acc_futures)
            # print(req)
            equity = req.data[0].today_equity
            initial_margin = req.data[0].initial_margin
            maintenance_margin = req.data[0].maintenance_margin

        except:
            print('Get account equity error')
        
        return equity, [initial_margin, maintenance_margin]

    def send_order(self, decision, amount=1):
        # 1=buy, -1=sell
        if decision == 1:
            buy_or_sell = BSAction.Buy
        if decision == -1:
            buy_or_sell = BSAction.Sell

        market_type = utils.get_market_type()
        if market_type == '-1':
            print("Market time error")
            return 1

        if market_type == '0':
            market = FutOptMarketType.Future
        if market_type == '1':
            market = FutOptMarketType.FutureNight

        order = FutOptOrder(
            buy_sell = buy_or_sell,
            symbol = self.Trade_symbol,
            lot = amount,
            market_type = market,
            price_type = FutOptPriceType.RangeMarket,
            time_in_force = TimeInForce.IOC,
            order_type = FutOptOrderType.Auto,
            user_def = "PythonAPI"
        )

        res = self.SDK.futopt.place_order(self.Acc_futures, order)

        if res.is_success != True:
            print("Failed to send order. Please check positions.")
            return 1

        winsound.Beep(3000,100)
        return 0
    
    def get_order_results(self):
        orderResults = self.SDK.futopt.get_order_results(self.Acc_futures)
        price = orderResults.data[-1].filled_money
        return price
    
    def update_position_holded(self):
        Buy_at = []
        Sel_at = []

        positions = self.SDK.futopt_accounting.query_single_position(self.Acc_futures)
        # print(positions)
        chk_symbol = ''
        if self.product == 'TXF':
            chk_symbol = 'FITX'
        elif self.product == 'MXF':
            chk_symbol = 'FIMTX'
        elif self.product == 'TMF':
            chk_symbol = 'FITM'
        else:
            print("Product error")

        if positions.data:
            for p in positions.data:
                if p.symbol == chk_symbol:
                    for i in range(p.tradable_lot):
                        if p.buy_sell == BSAction.Buy:
                            Buy_at.append(p.price)
                        elif p.buy_sell == BSAction.Sell:
                            Sel_at.append(p.price)
        # print('====================================================')
        # print(Buy_at)
        # print(Sel_at)
        return Buy_at, Sel_at

    def get_trade_symbol(self):
        settlementdate = utils.get_settlementDate()
        month_code = MONTH_CODE[settlementdate.month-1]
        last_code = str((settlementdate.year)%10)
        symbol = self.product + month_code + last_code

        return symbol

    # def get_trade_symbol(self):
    #     settlementDate = utils.get_settlementDate_realtime()
    #     market = utils.get_market_type()
    #     if market == '0':
    #         future_data = self.Restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX', contractType='I', status='N')
    #     else:
    #         future_data = self.Restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX',session='AFTERHOURS', contractType='I', status='N')
    #     #print(future_data)

    #     if self.product == 'TXF':
    #         keyword = '臺股期貨'
    #     elif self.product == 'MXF':
    #         keyword = '小型臺指'
    #     elif self.product == 'TMF':
    #         keyword = '微型臺指'
    #     else:
    #         print("Product error")
    #         return None

    #     for i in range(len(future_data['data'])):
    #         if (keyword in future_data['data'][i]['name']) and\
    #         (future_data['data'][i]['settlementDate'] == settlementDate.isoformat()):
    #             product_symbol = future_data['data'][i]['symbol']
    #             break
    #     return product_symbol
    
    def chk_inventories(self): #股票庫存
        inventories = self.SDK.accounting.inventories(self.Account[0])
        print(inventories)

    def chk_remainings(self): #帳戶餘額
        balance = self.SDK.accounting.bank_remain(self.Account[0])
        print(f"Account Balance: {balance}")
    
    
class Fubon_data(object):

    def __init__(self, period, product, data_queue): #period->minutes
        if product not in ('TXF', 'MXF', 'TMF'):
            raise ValueError("Invalid product. It should be TXF, MXF, or TMF.")

        self.period = self.period_minute(period)
        if self.period not in (1, 5, 10, 15, 30, 60):
            raise ValueError("Invalid period. It should be 1, 5, 10, 15, 30, or 60.")

        self.key = period
        self.product = product
        self.data_queue = data_queue
        return

    def period_minute(self, period_str):
        value = int(period_str[:-1])  # 提取數值
        unit = period_str[-1]       # 提取單位

        if unit != 'm':
            raise ValueError("Invalid period. It should have [m] at last.")

        return value  # 如果單位不正確，則傳回 None

    def get_candles(self):
        candles_list = self.get_candles_list()
        df = pd.DataFrame(candles_list)
        self.data_queue.put((self.key, df))

        while True:
            utils.sync_time(self.period)
            market = utils.get_market_type()
            if market == '0':
                data = self.Restfut.intraday.candles(symbol=self.Trade_symbol, timeframe=str(self.period))
            else:
                data = self.Restfut.intraday.candles(symbol=self.Trade_symbol, timeframe=str(self.period), session='afterhours')
            candles_list = data['data'][-CANDLE_MAX_AMOUNT:]
            
            #檢查最後一筆資料是不是完整candle
            localtime = time.localtime()
            last_data_min = int(candles_list[-1]['date'].split('T')[1].split(':')[1])
            if last_data_min == localtime.tm_min:
                del candles_list[-1]

            df = pd.DataFrame(candles_list)
            self.data_queue.put((self.key, df))
            time.sleep(self.period*60)

    def get_candles_list(self):
        self._init_data()
        candles_list = []
        market = utils.get_market_type()
        if market == '0':
            data = self.Restfut.intraday.candles(symbol=self.Trade_symbol, timeframe=str(self.period))
        else:
            data = self.Restfut.intraday.candles(symbol=self.Trade_symbol, timeframe=str(self.period), session='afterhours')
        candles_list = data['data'][-CANDLE_MAX_AMOUNT:]

        #檢查最後一筆資料是不是完整candle
        localtime = time.localtime()
        last_data_min = int(candles_list[-1]['date'].split('T')[1].split(':')[1])
        if last_data_min == localtime.tm_min:
            del candles_list[-1]
    
        return candles_list

    def login_account(self, retrytimes=6):
        try:
            self.Account = self.SDK.login(key.id, key.pwd, key.ca, key.ca_pwd)
        except Exception as error:
            print(f"Exception: {error}")
        
        if self.Account.is_success == True:
            self.Account = self.Account.data
        else:
            print("**Login failed** Retry after 10s...")
            time.sleep(10)
            return self.login_account(retrytimes-1)

        #print(f"===Login sucess===\n{self.Account}")
        #time.sleep(1)
        return
    
    def _init_data(self):
        self.Account = None
        self.Acc_futures = None
        self.Restfut = None
        self.Trade_symbol = None
        self.SDK = FubonSDK()
        self.login_account()
        self.SDK.init_realtime(Mode.Normal)
        self.Restfut = self.SDK.marketdata.rest_client.futopt
        self.Acc_futures = self.get_future_account()
        self.Trade_symbol = self.get_trade_symbol()
        self._set_event()
        return

    def get_future_account(self):
        for acc in self.Account:
            if acc.account_type == 'futopt':
                #print(f"Future account:\n{acc}")
                return acc
        return None

    def get_trade_symbol(self):
        settlementdate = utils.get_settlementDate()
        month_code = MONTH_CODE[settlementdate.month-1]
        last_code = str((settlementdate.year)%10)
        symbol = self.product + month_code + last_code

        return symbol

    # def get_trade_symbol(self):
    #     settlementDate = utils.get_settlementDate_realtime()
    #     market = utils.get_market_type()
    #     if market == '0':
    #         future_data = self.Restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX', contractType='I', status='N')
    #     else:
    #         future_data = self.Restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX',session='AFTERHOURS', contractType='I', status='N')
    #     #print(future_data)

    #     if self.product == 'TXF':
    #         keyword = '臺股期貨'
    #     elif self.product == 'MXF':
    #         keyword = '小型臺指'
    #     elif self.product == 'TMF':
    #         keyword = '微型臺指'
    #     else:
    #         print("Product error")
    #         return None

    #     for i in range(len(future_data['data'])):
    #         if (keyword in future_data['data'][i]['name']) and\
    #         (future_data['data'][i]['settlementDate'] == settlementDate.isoformat()):
    #             product_symbol = future_data['data'][i]['symbol']
    #             break
    #     return product_symbol
    
    def _set_event(self):
        self.SDK.set_on_event(self.on_event)
        self.SDK.set_on_futopt_filled(self.on_filled)
        return

    def handle_exceptions(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exp:
                # Extract the full traceback
                tb_lines = traceback.format_exc().splitlines()

                # Find the index of the line related to the original function
                func_line_index = next((i for i, line in enumerate(tb_lines) if func.__name__ in line), -1)

                # Highlight the specific part in the traceback where the exception occurred
                relevant_tb = "\n".join(tb_lines[func_line_index:])  # Include traceback from the function name

                error_text = f"{func.__name__} exception: {exp}\nTraceback (most recent call last):\n{relevant_tb}"
                print(error_text, file=sys.stderr)
        return wrapper

    #斷線重連
    @handle_exceptions
    def on_event(self, code, content):
        print("=====Event=====")
        print(code)
        print(content)
        if code == "300":
            print("Reconnecting...")
            try:
                self.Account = self.SDK.login(key.id, key.pwd, key.ca, key.ca_pwd)
                self.login_account()
                print("Reconnect successs")
                print(self.Account)
            except Exception as e:
                print("Reconnect failed")
                print(e)
        print("=====Event=====")

    #成交回報
    @handle_exceptions
    def on_filled(code, content):
        print("===Filled===")
        print(code)
        print(content)
        # print(content.filled_no)  # 印出成交流水號
        print("===Filled===")
       
    
    def handle_message(self, message):
        print(f'market data message: {message}')

    def subscribe_candles(self):
        market = utils.get_market_type()
        if market == '0':
            afterhours = False
        else:
            afterhours = True

        futopt = self.SDK.marketdata.websocket_client.futopt
        futopt.on('message', self.handle_message)
        futopt.connect()
        futopt.subscribe({ 
            'channel': 'candles', 
            'symbol': self.get_trade_symbol(),
            'afterHours' : afterhours,
        })
