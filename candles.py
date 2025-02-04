import datetime
import math
import os
import numpy as np
import csv
import time

class Candles(object):
    #global variables

    def __init__(self, period, source):
        self.data_src = source
        self.period = period
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

    def _get_candles_from_twse(self):
        return
    
    def _get_candles_from_fubon(self):
        return
    
    def _get_candles_from_csv(self):
        return