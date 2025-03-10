import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time
import multiprocessing

import twse
import fubon
import indicators

if __name__ == '__main__':
    data_queue = multiprocessing.Queue()
    fubon_1m = fubon.Fubon_api(1, 'MXF', data_queue)
    candles = fubon_1m.get_candles_list()
    ema = []
    atr = []
    kd  = []
    for i in range(10):
        print(candles[-(10-i)])
    print(f'sma: {indicators.candles_sma(candles, 10)}')
    print(f'ema: {indicators.candles_ema(candles, 10, ema)}')
    print(f'atr: {indicators.atr_calculation(candles, 14, atr)}')
    print(f'bband: {indicators.bollinger_bands_calculation(candles, 20)}')
    print(f'kd: {indicators.kd_calculation(candles, 9)}')
    print(f'rsi: {indicators.rsi_calculation(candles, 10)}')
