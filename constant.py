from conf import *

TRADE_MARKET_SET = ('day', 'night', 'main', 'all')
TRADE_DIRECTION_SET = ('buy', 'sell', 'auto')
TRADE_PRODUCT_SET = ('TXF', 'MXF', 'TMF')

MA_PREFIX = 'ma_'
EMA_PREFIX = 'ema_'
ATR_PREFIX = 'atr_'
KD_PREFIX = 'kd_'
RSI_PREFIX = 'rsi_'
BB_PREFIX = 'bbands_'
MACD_PREFIX = 'macd_'

MA_KEY = MA_PREFIX + str(MA_PERIOD)
EMA_KEY = EMA_PREFIX + str(EMA_PERIOD)
EMA2_KEY = EMA_PREFIX + str(EMA2_PERIOD)
ATR_KEY = ATR_PREFIX + str(ATR_PERIOD)
KD_KEY = KD_PREFIX + str(KD_PERIOD[0])
RSI_KEY = RSI_PREFIX + str(RSI_PERIOD)
BB_KEY = BB_PREFIX + str(BB_PERIOD[0])
MACD_KEY = MACD_PREFIX + str(MACD_PERIOD[0])

DAY_MARKET = ('08:45:00', '13:45:00')
NIGHT_MARKET = ('15:00:00', '05:00:00')
AMER_MARKET = ('21:30:00', '04:00:00')