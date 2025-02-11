import sys
import datetime
import time
import requests as r
import functools
import traceback
import winsound

import fubon_neo
from fubon_neo.sdk import FubonSDK, FutOptOrder
from fubon_neo.constant import TimeInForce, FutOptOrderType, FutOptPriceType, FutOptMarketType, CallPut, BSAction
import utils

sys.path.append("C:\\Users\\ChengWei\\Desktop\\my project")
import accinfo as key

class Fubon_api(object):
    def __init__(self):
        self.SDK = None
        self.Account = None
        self.Acc_futures = None
        self.Restfut = None
        self.login_account()
        self._init_data()
        self._set_event()
        self.update_position_holded()
        return
    
    def login_account(self, retrytimes=6):
        try:
            self.SDK = FubonSDK()
            self.Account = self.SDK.login(key.id, key.pwd, key.ca, key.ca_pwd)
        except Exception as error:
            print(f"Exception: {error}")
        
        if self.Account.is_success == True:
            self.Account = self.Account.data
        else:
            print("**Login failed** Retry after 10s...")
            time.sleep(10)
            return self.login_account(retrytimes-1)

        print(f"Login sucess\n{self.Account}")
        time.sleep(1)
        return
    
    def _init_data(self):
        self.SDK.init_realtime()
        self.Acc_futures = self.get_future_account()
        self.Restfut = self.SDK.marketdata.rest_client.futopt
        return
    def get_future_account(self):
        for acc in self.Account:
            if acc.account_type == 'futopt':
                print(f"Future account:\n{acc}")
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

    def update_equity(self):
        try:
            req = self.SDK.futopt_accounting.query_margin_equity(self.Acc_futures)
            equity = req.data[0].today_equity
        except:
            print('Get account equity error')
        
        return equity

    def send_order(self, product, decision, amount=1):
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
            symbol = product,
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
    
    def update_position_holded(self, product):
        Buy_at = []
        Sel_at = []

        positions = self.SDK.futopt_accounting.query_single_position(self.Acc_futures)

        chk_symbol = ''
        if product == 'TX':
            chk_symbol = 'FITX'
        elif product == 'MXF':
            chk_symbol = 'FIMTX'
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

        return Buy_at, Sel_at