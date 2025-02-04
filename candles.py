import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time

import utils

#global variables
TWSE_TXF_API = 'https://mis.taifex.com.tw/futures/api/getQuoteList'

class Candles(object):

    def __init__(self, product, period, source):
        self.product = product
        self.data_src = source
        self.period = period

        if source == 'fubon':
            self._init_fubon_sdk()
        elif source == 'twse':
            self.total_vol = 0
            self.pre_vol = 0
            self._init_twse_requirement()
        return
    
    def get_candles(self):
        if self.data_src == 'twse':
            return self._get_candles_from_twse()
        elif self.data_src == 'fubon':
            return self._get_candles_from_fubon()
        elif self.data_src == 'csv':
            return self._get_candles_from_csv()
        else:
            raise Exception("Data source error.")

    def _init_fubon_sdk(self):
        return

    def _init_twse_requirement(self):
        self.expire_month = utils.get_expiremonth()
        return

    def _get_candles_from_twse(self):
        response = None
        market_type = utils.get_market_type()
        if market_type == '-1':
            return None

        txf_payload = {
            "MarketType":market_type, #0=日盤, 1=夜盤
            "SymbolType":"F",
            "KindID":"1",
            "CID":self.product,
            "ExpireMonth":self.expire_month,
            "RowSize":"全部",
            "PageNo":"",
            "SortColumn":"",
            "AscDesc":"A"}

        try:
            response = r.post(url=TWSE_TXF_API, json=txf_payload).json()
        except Exception as error:
            print(f'Exception: {error}')
            # print('================================================')
            # if 'RtCode' in response.keys():
            #     print(f"RtCode: {response['RtCode']}")
            # if 'RtMsg' in response.keys():
            #     print(f"RtMsg: {response['RtMsg']}")
            # if 'RtData' in response.keys():
            #     print(f"RtData: {response['RtData']}")
            return None

        if int(response['RtCode']) == 0:
            txf_data = response['RtData']['QuoteList'][0]
        else:
            return None
        # print(response['RtData']['QuoteList'][0])
        # input()
        return self._data_filter(txf_data)
    
    def _data_filter(self, data):
        if 'CLastPrice' not in data or\
            'CTotalVolume' not in data or\
            'CTime' not in data:
            return None

        if not (data['CLastPrice']):
            return None

        if not data['CTotalVolume']:
            return None

        self.pre_vol = self.total_vol
        self.total_vol = int(data['CTotalVolume'])

        #換日總交易量重計
        if self.pre_vol > self.total_vol:
            self.pre_vol = 0

        vol = self.total_vol - self.pre_vol

        filtered_data = {
            'CLastPrice': float(data['CLastPrice']),
            'CTime': data['CTime'],
            'CVolume': vol
        }
        return filtered_data

    def _get_candles_from_fubon(self):
        return
    
    def _get_candles_from_csv(self):
        return
    
