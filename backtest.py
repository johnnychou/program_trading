import multiprocessing
import os
import csv
import fubon
import time
import datetime
import pandas as pd
from datetime import timedelta

import twse
import main as m
from conf import *

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
TRADING_MARKET = 'day'

CSV_INPUT_DATA = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered\Daily_2025_04_01.csv'

Fubon_account = None
Userinput_Market = None
Userinput_Direction = None
Userinput_Product = None
Userinput_OrderAmount = 0
OrderAmount = 0

Buy_at = []
Sell_at = []
Trade_record = []
Margin = []
Candle_list = []

Last_price = 0
Profit = 0
Balance = 0
OrderAmount = 0
PT_price = 0

candles_1m = twse.CandleCollector(period=timedelta(minutes=1))
df_1m = pd.DataFrame()

if __name__ == '__main__':
    twse_data = twse.TWSE_CSV(CSV_INPUT_DATA)

    while True:
        data = twse_data.get_row_from_csv()
        candle = candles_1m.get_candles(data)
        if candle:
            new_row = pd.DataFrame([candle])
            df_1m = pd.concat([df_1m, new_row], ignore_index=True)
            m.indicators_calculation(df_1m)
        
        if len(df_1m) > 10:
            break

    print(df_1m)

