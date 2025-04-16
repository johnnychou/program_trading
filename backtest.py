import multiprocessing
import os
import csv
import fubon
import time
import datetime
import pandas as pd

import twse
import main as m
from conf import *

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
TRADING_MARKET = 'main'

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

if __name__ == '__main__':
    twse_data = twse.TWSE_CSV(CSV_INPUT_DATA, PERIOD_30S)
    twse_30s = pd.DataFrame()
    while True:
        candles_df = twse_data.get_candles()
        if candles_df is None:
            break
        else:
            twse_30s = candles_df

    print(twse_30s)

