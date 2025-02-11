import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time

import utils
import fubon

#global variables
TWSE_TXF_API = 'https://mis.taifex.com.tw/futures/api/getQuoteList'
TWSE_DATA_RATE = 0.02
RETRY_TIMES = 10
CANDLE_MAX_AMOUNT = 50

class TWSE(object):
    def __init__(self, period, product, source, data_queue, shared_data=None): # (TXF/MXF/TMF, period->seconds, twse/csv)
        self.period = period
        self.product = product
        self.data_src = source
        self.candles_list = []
        #process控制
        self.data_queue = data_queue #共享data
        self.realtime_candle = shared_data

        if source == 'twse':
            self.total_vol = 0
            self.pre_vol = 0
            self._init_twse_requirement()

        return
    
    def get_candles(self):
        while True:
            candle = None
            if self.data_src == 'twse':
                candle = self._get_candles_from_twse()
            elif self.data_src == 'csv':
                candle = self._get_candles_from_csv()
            else:
                raise Exception("Data source error.")

            if candle:
                self.candles_list.append(candle)
                self.data_queue.put((self.period, self.candles_list))

            if len(self.candles_list) > CANDLE_MAX_AMOUNT:  # 限制長度
                self.candles_list.pop(0)                    # 移除最舊的數據

    def _init_twse_requirement(self):
        self.expire_month = utils.get_expiremonth_realtime()
        return

    def _get_twse_data(self):
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

        if not self.pre_vol and not self.total_vol:
            self.total_vol = int(data['CTotalVolume'])
            self.pre_vol = self.total_vol
        else:
            self.pre_vol = self.total_vol
            self.total_vol = int(data['CTotalVolume'])

        vol = self.total_vol - self.pre_vol
        if vol <= 0:
            return None

        filtered_data = {
            'CLastPrice': int(float(data['CLastPrice'])),
            'CTime': data['CTime'],
            'CVolume': vol,
        }
        return filtered_data

    def _get_candles_from_twse(self):
        during_time=0
        copen=cclose=chigh=clow=cvolume=ctime=last_price=0
        start = time.time()

        while(during_time < self.period):
            latest_data = self._get_twse_data()
            while not latest_data: #retry
                latest_data = self._get_twse_data()
                now = time.time()
                during_time = now - start
                if during_time >= self.period:
                    break
                self.realtime_candle['period'] = round(during_time, 2)
                time.sleep(TWSE_DATA_RATE)

            if latest_data:
                last_price = latest_data['CLastPrice']
                if copen == 0:
                    copen = last_price
                    clow = last_price
                if chigh < last_price:
                    chigh = last_price 
                if clow > last_price:
                    clow = last_price
                cvolume += latest_data['CVolume']
                cclose = last_price
                ctime = latest_data['CTime']

                self.realtime_candle['lastprice'] = last_price
                self.realtime_candle['open'] = copen
                self.realtime_candle['close'] = cclose
                self.realtime_candle['high'] = chigh
                self.realtime_candle['low'] = clow
                self.realtime_candle['volume'] = cvolume
                self.realtime_candle['time'] = ctime
                self.realtime_candle['period'] = round(during_time, 2)

            now = time.time()
            during_time = now - start
            time.sleep(TWSE_DATA_RATE)
        #end of while

        if cvolume <= 0:
            return None

        if (cclose - copen) > 0:
            body = 1
        elif (cclose - copen) < 0:
            body = -1
        else:
            body = 0

        my_candle = {
            'body': body,
            'open': copen,
            'close': cclose,
            'high': chigh,
            'low': clow,
            'volume': cvolume,
            'time': ctime,
            'period': round(during_time, 2),
        }
        return my_candle
    
    def _get_candles_from_csv(self):
        return
    
