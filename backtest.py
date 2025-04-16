import multiprocessing
import os
import csv
import fubon
import time
import datetime
import pandas as pd
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

Last_price = 0
Profit = 0
Balance = 0
OrderAmount = 0
PT_price = 0

if __name__ == '__main__':

    m.user_input_settings()

    Processes = []
    data_queue = multiprocessing.Queue()                # shared data queue
    realtime_candle = multiprocessing.Manager().dict()  # shared dict

    m.create_twse_process(PERIOD_30S, Userinput_Product, CSV_INPUT_DATA, data_queue, realtime_candle, Processes)

    df_twse_30s = pd.DataFrame()

    try:
        while True:
            while not data_queue.empty():
                period, tmp_df = data_queue.get()
                tmp_df = m.indicators_calculation(tmp_df)
                if period == PERIOD_30S:
                    df_twse_30s = tmp_df
                    print(df_twse_30s)
                    time.sleep(10)
            #os.system('cls')

    except KeyboardInterrupt:
        print("All processes stopped.")