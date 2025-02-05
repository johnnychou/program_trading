import datetime
import math
import os
import numpy as np
import requests as r
import csv
import time

import candles

twse_30s = candles.Candles('TXF', 30, 'twse')

while True:
    candles_30s = twse_30s.get_candles()
    print(candles_30s)
    twse_30s.show_realtime_candle()
    time.sleep(1)