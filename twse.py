import datetime
from datetime import timedelta
import math
import os
import numpy as np
import requests as r
import csv
import time
import pandas as pd

import utils
import fubon
import indicators as i
import main as m
from conf import *
from constant import *

#global variables
TWSE_TXF_API = 'https://mis.taifex.com.tw/futures/api/getQuoteList'
TWSE_DATA_RATE = 0.02
RETRY_TIMES = 10

class TWSE(object):
    def __init__(self, period, product, data_queue, shared_data=None): # (TXF/MXF/TMF, period->seconds, twse/csv)
        self.key = period
        self.period = self.period_to_seconds(period)
        self.product = product
        self.df = pd.DataFrame()
        #process控制
        self.data_queue = data_queue #共享data
        self.realtime_candle = shared_data

        self.total_vol = 0
        self.pre_vol = 0
        self.highest = 0
        self.lowest = 0

        self._init_twse_requirement()
        self.indicators = i.indicator_calculator()

        return

    def period_to_seconds(self, period_str):
        value = int(period_str[:-1])  # 提取數值
        unit = period_str[-1]       # 提取單位

        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 60 * 60
        return None  # 如果單位不正確，則傳回 None

    def get_candles(self):
        utils.sync_time(self.period/60)
        while True:
            market = utils.get_market_type()
            if market == '-1':
                time.sleep(60)
                continue
            #self.indicators.reset_state_if_needed(market)
            candle = self._get_candles_from_twse()
            if candle:
                new_row = pd.DataFrame([candle])
                self.df = pd.concat([self.df, new_row], ignore_index=True)
                if len(self.df) > MAX_CANDLE_AMOUNT[self.key]:
                    self.df = self.df.iloc[-MAX_CANDLE_AMOUNT[self.key]:]
                    self.df = self.df.reset_index(drop=True)
                self.indicators.indicators_calculation_all(self.df)
                self.data_queue.put((self.key, self.df))

    def _init_twse_requirement(self):
        self.expire_month = utils.get_expiremonth_realtime()
        return

    def _get_twse_data(self):
        response = None
        market = utils.get_market_type()
        if market == '-1':
            return None

        txf_payload = {
            "MarketType":market, #0=日盤, 1=夜盤
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

        self.highest = int(float(data['CHighPrice']))
        self.lowest = int(float(data['CLowPrice']))

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
                self.realtime_candle['cnt'] = round(during_time, 2)
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
                self.realtime_candle['cnt'] = round(during_time, 2)
                self.realtime_candle['highest'] = self.highest
                self.realtime_candle['lowest'] = self.lowest

            now = time.time()
            during_time = now - start
            time.sleep(TWSE_DATA_RATE)
        #end of while

        if cvolume <= 0:
            return None

        my_candle = {
            'open': copen,
            'high': chigh,
            'low': clow,
            'close': cclose,
            'volume': cvolume,
            'time': ctime,
        }
        return my_candle

class TWSE_CSV(object):
    def __init__(self, csvpath):
        self.df = pd.DataFrame()
        self.csvdata = None
        self.csvpath = csvpath
        self.csvfile = open(self.csvpath, newline='')
        self.csvdata = csv.reader(self.csvfile)
        next(self.csvdata) # 跳過第一行

    def get_candles(self):
        candle = self.get_candles_from_csv()
        if candle:
            new_row = pd.DataFrame([candle])
            self.df = pd.concat([self.df, new_row], ignore_index=True)
            return self.df
        else:
            return None

    def get_candles_from_csv(self, data):
        copen=cclose=chigh=clow=cvolume=ctime=last_price=0
        during_time = datetime.timedelta(seconds=0)
        c_period = datetime.timedelta(seconds=self.period)
        start_time = 0

        while(during_time < c_period):
            data = self.get_row_from_csv()
            if not data:
                break

            last_price = data['lastprice']
            if not start_time:
                start_time = data['time']

            if copen == 0:
                copen = last_price
                clow = last_price
            if chigh < last_price:
                chigh = last_price
            if clow > last_price:
                clow = last_price

            cclose = last_price
            cvolume += data['volume']
            ctime = data['time']

            during_time = data['time'] - start_time

        if cvolume <= 0:
            return None

        my_candle = {
            'open': copen,
            'close': cclose,
            'high': chigh,
            'low': clow,
            'volume': cvolume,
            #'period': during_time.total_seconds(),
            'time': ctime,
        }
        return my_candle

    def get_row_from_csv(self):
        try:
            row = next(self.csvdata, 'end')
            if row == 'end':
                return None
        except:
            return None

        row_datatime = self.trans_datetime(int(row[0]), int(row[3]))
        row_market = self.is_day_market(row_datatime)
        data = {
            'lastprice': int(row[4]),
            'volume': int(row[5]),
            'time': row_datatime,
            'market': row_market,
        }
        return data
    
    def is_day_market(self, row_time):
        current_time_tuple = (row_time.hour, row_time.minute)
        start_time_tuple = (8, 45)   # 代表 08:45
        end_time_tuple = (13, 45)  # 代表 13:45

        if start_time_tuple <= current_time_tuple <= end_time_tuple:
            return '0'
        else:
            return '1'


    def period_to_seconds(self, period_str):
        value = int(period_str[:-1])  # 提取數值
        unit = period_str[-1]       # 提取單位

        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 60 * 60
        return None  # 如果單位不正確，則傳回 None

    def trans_datetime(self, mdate, mtime):
        myear = mdate//10000
        mmonth = (mdate//100)%100
        mday = mdate%100

        sec = mtime%100
        min = (mtime//100)%100
        hor = mtime//10000
        #print(myear, mmonth, mday, hor, min, sec)
        return datetime.datetime(myear, mmonth, mday, hor, min, sec)
    

class CandleCollector:
    def __init__(self, period: timedelta):
        self.period = period
        self.buffer = []
        self.start_time = None

    def get_candles(self, data):
        # 如果資料結束，強制產生最後一根K線（即使不滿 period）
        if data is None:
            if self.buffer and self.start_time:
                prices = [item['lastprice'] for item in self.buffer]
                volumes = [item['volume'] for item in self.buffer]
                candle = {
                    'open': prices[0],
                    'high': max(prices),
                    'low': min(prices),
                    'close': prices[-1],
                    'volume': sum(volumes),
                    'start_time': self.start_time,
                    'end_time': self.start_time + self.period
                }
                self.buffer = []
                self.start_time = None
                return candle
            else:
                return None

        current_time = data['time']

        if not self.start_time:
            self.start_time = current_time

        end_time = self.start_time + self.period

        if current_time >= end_time:
            prices = [item['lastprice'] for item in self.buffer]
            volumes = [item['volume'] for item in self.buffer]
            candle = {
                'open': prices[0],
                'high': max(prices),
                'low': min(prices),
                'close': prices[-1],
                'volume': sum(volumes),
                'start_time': self.start_time,
                'end_time': end_time,
            }
            self.buffer = []
            self.buffer.append(data)

            if m.is_trading_time('all', end_time):
                self.start_time = end_time
            else: 
                self.start_time = None

            return candle
        else:
            self.buffer.append(data)
            return None