import os
import sys
import datetime
import time
import requests as r
import functools
import traceback
import winsound
import pandas as pd
import numpy as np
from dotenv import load_dotenv

import fubon_neo
from fubon_neo.sdk import FubonSDK, Mode, FutOptOrder
from fubon_neo.constant import TimeInForce, FutOptOrderType, FutOptPriceType, FutOptMarketType, CallPut, BSAction
import utils
import indicators as i
from conf import *

MONTH_CODE = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L')

class Fubon_trade(object):
    def __init__(self, product):
        self.Account = None
        self.Acc_futures = None
        self.Restfut = None
        self.product = product

        load_dotenv()
        self.userid = os.getenv("USERID")
        self.userpwd = os.getenv("USERPWD")
        self.ca = os.getenv("CA")
        self.capwd = os.getenv("CAPWD")

        if product == 'TXF':
            self.chk_symbol = 'FITX'
        elif product == 'MXF':
            self.chk_symbol = 'FIMTX'
        elif product == 'TMF':
            self.chk_symbol = 'FITM'

        self.SDK = FubonSDK()
        self.login_account()
        self.SDK.init_realtime(Mode.Normal)
        self.Restfut = self.SDK.marketdata.rest_client.futopt
        self.Acc_futures = self.get_future_account()
        self._set_event()

        return

    def login_account(self):
        try:
            self.Account = self.SDK.login(self.userid, self.userpwd, self.ca, self.capwd)
        except Exception as error:
            print(f"Exception: {error}")
        
        if self.Account.is_success == True:
            self.Account = self.Account.data
        else:
            print("**Login failed** Retry after 30s...")
            time.sleep(30)
            return self.login_account()

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
                self.Account = self.SDK.login(self.userid, self.userpwd, self.ca, self.capwd)
                self.login_account()
                print("Reconnect successs")
                print(self.Account)
            except Exception as e:
                print("Reconnect failed")
                print(e)
        print("=====Event=====")

    #成交回報
    @handle_exceptions
    def on_filled(self, code, content):
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
            print('Get account equity error.')
            equity = 0
            initial_margin = 0
            maintenance_margin = 0
        
        return equity, [initial_margin, maintenance_margin]

    def send_order(self, decision, amount=1):
        trade_symbol = self.get_trade_symbol()
        # 1=buy, -1=sell
        if decision == 1:
            buy_or_sell = BSAction.Buy
        elif decision == -1:
            buy_or_sell = BSAction.Sell
        else:
            return

        market_type = utils.get_market_type()
        if market_type == '-1':
            print("Market time error")
            return 1

        if market_type == '0':
            market = FutOptMarketType.Future
        elif market_type == '1':
            market = FutOptMarketType.FutureNight

        order = FutOptOrder(
            buy_sell = buy_or_sell,
            symbol = trade_symbol,
            lot = amount,
            market_type = market,
            price_type = FutOptPriceType.RangeMarket,
            time_in_force = TimeInForce.IOC,
            order_type = FutOptOrderType.Auto,
            user_def = "PythonAPI"
        )

        res = self.SDK.futopt.place_order(self.Acc_futures, order)

        if res.is_success != True:
            print(f'send order error: {res}')
            winsound.Beep(5000,1000)
            time.sleep(30)
            return 0

        winsound.Beep(3000,100)     
        return 0
    
    def get_order_results(self):
        market_type = utils.get_market_type()
        if market_type == '-1':
            print("Market time error")
            return 1

        if market_type == '0':
            market = FutOptMarketType.Future
        elif market_type == '1':
            market = FutOptMarketType.FutureNight
        orderResults = self.SDK.futopt.get_order_results(self.Acc_futures, market)
        filled_price = 0
        #print(orderResults)

        if orderResults.data[-1].symbol == self.chk_symbol:
            filled_price = orderResults.data[-1].filled_money

        if filled_price:
            return filled_price

        return 0
    
    def update_position_holded(self):
        Buy_at = []
        Sel_at = []

        try:
            positions = self.SDK.futopt_accounting.query_single_position(self.Acc_futures)
            # print(positions)

            if positions.data:
                for p in positions.data:
                    if p.symbol == self.chk_symbol:
                        for i in range(p.tradable_lot):
                            if p.buy_sell == BSAction.Buy:
                                Buy_at.append(p.price)
                            elif p.buy_sell == BSAction.Sell:
                                Sel_at.append(p.price)
        except:
            print('Get account positions error.')
            winsound.Beep(5000,1000)

        # print('====================================================')
        # print(Buy_at)
        # print(Sel_at)
        return Buy_at, Sel_at

    def get_trade_symbol(self):
        settlementdate = utils.get_settlementDate_realtime()
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

        self.period = utils.period_to_minute(period)
        if self.period not in (1, 5, 10, 15, 30, 60):
            raise ValueError("Invalid period. It should be 1, 5, 10, 15, 30, or 60.")

        self.key = period
        self.product = product
        load_dotenv()
        self.userid = os.getenv("USERID")
        self.userpwd = os.getenv("USERPWD")
        self.ca = os.getenv("CA")
        self.capwd = os.getenv("CAPWD")
        self.data_queue = data_queue
        self.df = pd.DataFrame()
        return

    def _init_data(self):
        self.Account = None
        self.Acc_futures = None
        self.Restfut = None
        self.indicators = i.indicator_calculator()
        self.SDK = FubonSDK()
        self.login_account()
        self.SDK.init_realtime(Mode.Normal)
        self.Restfut = self.SDK.marketdata.rest_client.futopt
        self.Acc_futures = self.get_future_account()
        self._set_event()
        return

    def get_candles(self):
        candles_list = self.get_candles_list()
        if candles_list:
            self.df = pd.DataFrame(candles_list)
            self.indicators.indicators_calculation_all(self.df)
            self.data_queue.put((self.key, self.df))
        while True:
            utils.sync_time(self.period)
            trade_symbol = self.get_trade_symbol()
            market = utils.get_market_type()

            try:
                if market == '0':
                    data = self.Restfut.intraday.candles(symbol=trade_symbol, timeframe=str(self.period))
                elif market == '1':
                    data = self.Restfut.intraday.candles(symbol=trade_symbol, timeframe=str(self.period), session='afterhours')
                else: # 非交易時間
                    time.sleep(60)
                    continue
            except Exception as e:
                print(f"[ERROR] Fetching candles failed: {e}")
                time.sleep(60)
                continue

            #self.indicators.reset_state_if_needed(market)

            # 檢查最後一筆資料是不是完整candle
            # 富邦api的k線時間跟一般app看的不同，差距一個週期
            last_data_min = int(data['data'][-1]['date'].split('T')[1].split(':')[1])
            localtime = time.localtime()
            a = 60 - localtime.tm_min
            b = 60 - last_data_min
            if np.abs(a-b) < self.period:
                del data['data'][-1]

            candles_list = data['data']
            if candles_list:
                new_row = candles_list[-1]
                new_df = pd.DataFrame([new_row])
                self.df = pd.concat([self.df, new_df], ignore_index=True)
                if len(self.df) > MAX_CANDLE_AMOUNT[self.key]:
                    self.df = self.df.iloc[-MAX_CANDLE_AMOUNT[self.key]:]
                    self.df = self.df.reset_index(drop=True)
                self.indicators.indicators_calculation_all(self.df)
                self.data_queue.put((self.key, self.df))

            time.sleep(self.period*59)

    def get_candles_list(self):
        self._init_data()
        candles_list = []
        trade_symbol = self.get_trade_symbol()
        market = utils.get_market_type()
        try:
            if market == '0':
                    data = self.Restfut.intraday.candles(symbol=trade_symbol, timeframe=str(self.period))
            elif market == '1':
                    data = self.Restfut.intraday.candles(symbol=trade_symbol, timeframe=str(self.period), session='afterhours')
            else:
                return
        except Exception as e:
            print(f"[ERROR] Fetching candles failed: {e}")
            return
        
        # 富邦api的k線時間跟一般app看的不同，差距一個週期
        # 最後一根都會是未完整k線
        last_data_min = int(data['data'][-1]['date'].split('T')[1].split(':')[1])
        localtime = time.localtime()
        a = 60 - localtime.tm_min
        b = 60 - last_data_min
        if np.abs(a-b) < self.period:
            del data['data'][-1]

        candles_list = data['data']

        return candles_list

    def login_account(self):
        try:
            self.Account = self.SDK.login(self.userid, self.userpwd, self.ca, self.capwd)
        except Exception as error:
            print(f"Exception: {error}")
        
        if self.Account.is_success == True:
            self.Account = self.Account.data
        else:
            print("**Login failed** Retry after 30s...")
            time.sleep(30)
            return self.login_account()

        #print(f"===Login sucess===\n{self.Account}")
        #time.sleep(1)
        return

    def get_future_account(self):
        for acc in self.Account:
            if acc.account_type == 'futopt':
                #print(f"Future account:\n{acc}")
                return acc
        return None

    def get_trade_symbol(self):
        settlementdate = utils.get_settlementDate_realtime()
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
                self.Account = self.SDK.login(self.userid, self.userpwd, self.ca, self.capwd)
                self.login_account()
                print("Reconnect successs")
                print(self.Account)
            except Exception as e:
                print("Reconnect failed")
                print(e)
        print("=====Event=====")

    #成交回報
    @handle_exceptions
    def on_filled(self, code, content):
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
