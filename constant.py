import indicators

PRODUCT = 'MXF'
TWSE_PERIOD_30S = '30s'
FUBON_PERIOD_1M = '1m'
FUBON_PERIOD_5M = '5m'
FUBON_PERIOD_15M = '15m'

MA_PERIOD = 10
EMA_PERIOD = 5
EMA2_PERIOD = 20
ATR_PERIOD = 14
RSI_PERIOD = 10
KD_PERIOD = (9, 3, 3)
MACD_PERIOD = (12, 26, 9)
BB_PERIOD = (20, 2)

TRADE_MARKET_SET = ('day', 'night', 'main', 'all')
TRADE_DIRECTION_SET = ('buy', 'sell', 'auto')
TRADE_PRODUCT_SET = ('TXF', 'MXF', 'TMF')

MA_KEY = indicators.MA_PREFIX + str(MA_PERIOD)
EMA_KEY = indicators.EMA_PREFIX + str(EMA_PERIOD)
EMA2_KEY = indicators.EMA_PREFIX + str(EMA2_PERIOD)
ATR_KEY = indicators.ATR_PREFIX + str(ATR_PERIOD)
KD_KEY = indicators.KD_PREFIX + str(KD_PERIOD[0])
RSI_KEY = indicators.RSI_PREFIX + str(RSI_PERIOD)
BB_KEY = indicators.BB_PREFIX + str(BB_PERIOD[0])
MACD_KEY = indicators.MACD_PREFIX + str(MACD_PERIOD[0])
