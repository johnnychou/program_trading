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
    for i in range(10):
        print(candles[-(10-i)])
    