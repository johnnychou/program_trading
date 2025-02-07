import sys
import datetime
import time
import requests as r

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
        self.login_account()
        self.SDK.init_realtime()
        self.Acc_futures = self._get_future_account()
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

        print(f"Login sucess.\n{self.Account}")
        time.sleep(1)
        return
    
    def _get_future_account(self):
        for acc in self.Account:
            if acc.account_type == 'futopt':
                print(f"Future account:\n{acc}")
                return acc
        return None
    
