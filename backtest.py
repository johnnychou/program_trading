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
import indicators as i
from conf import *
from constant import *

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
CSV_INPUT_DATA = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered\Daily_2025_04_15.csv'
PT_price = 200

class Backtest():
    def __init__(self, fullpath, trade_market='main'):
        self.fullpath = fullpath
        self.trade_market = trade_market
        self.Buy_at = []
        self.Buy_time = []
        self.Buy_profit = []
        self.Buy_record = []

        self.Sell_at = []
        self.Sell_time = []
        self.Sell_profit = []
        self.Sell_record = []

        self.Trade_times = 0
        self.Last_price = 0
        self.Total_profit = 0
        self.Max_profit_pt = 0
        self.Pre_data_time = 0

        self.candles_1m = twse.CandleCollector(period=timedelta(minutes=1))
        self.candles_5m = twse.CandleCollector(period=timedelta(minutes=5))
        self.candles_15m = twse.CandleCollector(period=timedelta(minutes=15))
        self.candles_30m = twse.CandleCollector(period=timedelta(minutes=30))
        self.df_1m = pd.DataFrame()
        self.df_5m = pd.DataFrame()
        self.df_15m = pd.DataFrame()
        self.df_30m = pd.DataFrame()

    def fake_open_position(self, sig, lastprice, now): # 1=buy, -1=sell
        if self.Buy_at or self.Sell_at:
            return 0
        if sig == 1:
            self.Buy_at.append(lastprice)
            self.Buy_time.append(now)
            self.Trade_times += 1
        elif sig == -1:
            self.Sell_at.append(lastprice)
            self.Sell_time.append(now)
            self.Trade_times += 1
        return

    def fake_close_position(self, sig, lastprice, now): # 1=close_sell_position, -1=close_buy_position
        profit = 0
        if not self.Buy_at and not self.Sell_at:
            return 0
        if (self.Buy_at and sig == 1) or\
            (self.Sell_at and sig == -1):
            return 0

        close_time = now

        if sig == 1:
            while self.Sell_at:
                price = self.Sell_at.pop(0)
                open_time = self.Sell_time.pop(0)
                profit += (price - lastprice)*PT_price
                self.Sell_profit.append(profit)
                self.Sell_record.append([price, lastprice, open_time, close_time, profit])
                self.Total_profit += profit
                self.Trade_times += 1
        elif sig == -1:
            while self.Buy_at:
                price = self.Buy_at.pop(0)
                open_time = self.Buy_time.pop(0)
                profit += (lastprice - price)*PT_price
                self.Buy_profit.append(profit)
                self.Buy_record.append([price, lastprice, open_time, close_time, profit])
                self.Total_profit += profit
                self.Trade_times += 1
        return

    def fake_close_all_position(self,lastprice, now):
        if self.Buy_at:
            self.fake_close_position(-1, lastprice, now)
        if self.Sell_at:
            self.fake_close_position(1, lastprice, now)
        return

    def export_trade_log(self):
        base_filename = os.path.splitext(os.path.basename(self.fullpath))[0]
        output_file = os.path.join(CSV_OUTPUT_PATH, f"{base_filename}_result.csv")

        records = []

        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)

            # 寫入統計資訊
            writer.writerow(['Income', self.Total_profit - self.Trade_times*150])
            writer.writerow(['Total_profit', self.Total_profit])
            writer.writerow(['Trade_times', self.Trade_times, self.Trade_times*150])
            writer.writerow(['Buy_profit', sum(self.Buy_profit) ,self.Buy_profit])
            writer.writerow(['Sell_profit', sum(self.Sell_profit), self.Sell_profit])
            writer.writerow([])  # 空行分隔


        for buy, sell, entry_time, exit_time, profit in self.Buy_record:
            records.append({
                'type': 'Buy',
                'entry': buy,
                'exit': sell,
                'profit': profit,
                'entry_time': entry_time,
                'exit_time': exit_time
            })

        for sell, buy, entry_time, exit_time, profit in self.Sell_record:
            records.append({
                'type': 'Sell',
                'entry': sell,
                'exit': buy,
                'profit': profit,
                'entry_time': entry_time,
                'exit_time': exit_time
            })

        df_record = pd.DataFrame(records)
        if 'entry_time' in df_record.columns:
            df_record = df_record.sort_values(by='entry_time')
        df_record.to_csv(output_file, index=False, encoding='utf-8-sig', mode='a') # mode -> append
        print(f"交易紀錄已儲存到: {output_file}")

    # def detect_kbar_momentum(self, row):
    #     body = abs(row['close'] - row['open'])
    #     upper_shadow = row['high'] - max(row['close'], row['open'])
    #     lower_shadow = min(row['close'], row['open']) - row['low']

    #     if body > upper_shadow * 2 and body > lower_shadow * 2:
    #         if row['close'] > row['open']:
    #             return 'long'
    #         elif row['close'] < row['open']:
    #             return 'short'
    #     return None

    # def get_ema_trend(self, df, period=20):
    #     if len(df) < period + 2:
    #         return None
    #     ema = df['close'].ewm(span=period, adjust=False).mean()
    #     slope = ema.iloc[-1] - ema.iloc[-2]
    #     return 'up' if slope > 0 else 'down'

    def atr_fixed_stop(self, realtime_candle, df):
        if sig := self.chk_stop_loss(realtime_candle, df):
            return sig
        if sig := self.chk_take_profit(realtime_candle, df):
            return sig
        return 0

    def chk_stop_loss(self, realtime_candle, df):
        if 'lastprice' not in realtime_candle:
            return 0
        if ATR_KEY not in df.columns:
            return 0
        if not self.Buy_at and not self.Sell_at:
            return 0

        lastprice = realtime_candle['lastprice']
        last_valid_idx = df[ATR_KEY].last_valid_index()
        atr = df.loc[last_valid_idx, ATR_KEY]

        if self.Buy_at:
            entry_price = self.Buy_at[0]
            close_price = entry_price - atr * 1.5
            if lastprice <= close_price:
                return -1
        elif self.Sell_at:
            entry_price = self.Sell_at[0]
            close_price = entry_price + atr * 1.5
            if lastprice >= close_price:
                return 1
        return 0

    def chk_take_profit(self, realtime_candle, df):
        if 'lastprice' not in realtime_candle:
            return 0
        if ATR_KEY not in df.columns:
            return 0
        if not self.Buy_at and not self.Sell_at:
            return 0

        lastprice = realtime_candle['lastprice']
        last_valid_idx = df[ATR_KEY].last_valid_index()
        atr = df.loc[last_valid_idx, ATR_KEY]

        if self.Buy_at:
            entry_price = self.Buy_at[0]
            close_price = entry_price + atr * 2
            if lastprice >= close_price:
                return -1
        elif self.Sell_at:
            entry_price = self.Sell_at[0]
            close_price = entry_price - atr * 2
            if lastprice <= close_price:
                return 1
        return 0

    def atr_trailing_stop(self, realtime_candle, df):
        if 'lastprice' not in realtime_candle:
            return 0
        if ATR_KEY not in df.columns:
            return 0
        
        lastprice = realtime_candle['lastprice']
        last_valid_idx = df[ATR_KEY].last_valid_index()
        if not last_valid_idx:
            return 0
        else:
            atr = df.loc[last_valid_idx, ATR_KEY]

        if self.Buy_at:
            self.Max_profit_pt = max(lastprice, self.Buy_at[0], self.Max_profit_pt)
            stop_price = self.Max_profit_pt - atr * 1.5
            if lastprice <= stop_price:
                self.Max_profit_pt = 0
                return -1

        elif self.Sell_at:
            if not self.Max_profit_pt:
                self.Max_profit_pt = min(lastprice, self.Sell_at[0])
            else:
                self.Max_profit_pt = min(lastprice, self.Sell_at[0], self.Max_profit_pt)
            stop_price = self.Max_profit_pt + atr * 1.5
            if lastprice >= stop_price:
                self.Max_profit_pt = 0
                return 1

        return 0

    def bband_stop(self, df):
        if BB_KEY not in df.columns:
            return 0

        up_band = df.iloc[-1][BB_KEY][1]
        bot_band = df.iloc[-1][BB_KEY][2]
        pre_up_band = df.iloc[-2][BB_KEY][1]
        pre_bot_band = df.iloc[-2][BB_KEY][2]

        pre_high = df.iloc[-2]['high']
        pre_low = df.iloc[-2]['low']
        close = df.iloc[-1]['close']

        if self.Buy_at:
            if pre_high >= pre_up_band and close < up_band:
                return -1
        if self.Sell_at:
            if pre_low <= pre_bot_band and close > bot_band:
                return 1
        return 0

    def run_test(self):
        twse_data = twse.TWSE_CSV(self.fullpath)
        idicators_1m = i.indicator_calculator()
        idicators_5m = i.indicator_calculator()
        idicators_15m = i.indicator_calculator()
        df_flag = {
            PERIOD_30S: 0,
            PERIOD_1M: 0,
            PERIOD_5M: 0,
            PERIOD_15M: 0,
        }
        
        while True:
            data = twse_data.get_row_from_csv()

            if data:
                if not self.Pre_data_time:
                    self.Pre_data_time = data['time']
                else:
                    self.Pre_data_time = now
                now = data['time']
                self.Last_price = data['lastprice']
                market = data['market']

            candle_1 = self.candles_1m.get_candles(data)
            if candle_1:
                new_row = pd.DataFrame([candle_1])
                self.df_1m = pd.concat([self.df_1m, new_row], ignore_index=True)
                idicators_1m.indicators_calculation_all(self.df_1m)
                candle_1 = 0
                df_flag[PERIOD_1M] = 1

            candle_5 = self.candles_5m.get_candles(data)
            if candle_5:
                new_row = pd.DataFrame([candle_5])
                self.df_5m = pd.concat([self.df_5m, new_row], ignore_index=True)
                idicators_5m.indicators_calculation_all(self.df_5m)
                candle_5 = 0
                df_flag[PERIOD_5M] = 1

            candle_15 = self.candles_15m.get_candles(data)
            if candle_15:
                new_row = pd.DataFrame([candle_15])
                self.df_15m = pd.concat([self.df_15m, new_row], ignore_index=True)
                idicators_15m.indicators_calculation_all(self.df_15m)
                candle_15 = 0
                df_flag[PERIOD_15M] = 1

            # 讓上面k線收完
            if data is None:
                twse_data.csvfile.close()
                break

            if m.before_end_of_market(self.trade_market, now):
                self.fake_close_all_position(self.Last_price, now)
                continue

            if (not m.is_trading_time(self.trade_market, now)) or\
                  (not m.is_trading_time(self.trade_market, self.Pre_data_time)):
                df_flag = {
                    PERIOD_30S: 0,
                    PERIOD_1M: 0,
                    PERIOD_5M: 0,
                    PERIOD_15M: 0,
                }
                continue
            
            if len(self.df_1m) > 3 and len(self.df_5m) > 3:
        
                # get trade type
                trade_type = m.trend_or_consolidation_bb(self.df_1m)

                # check for close position
                if self.Buy_at or self.Sell_at:
                    if trade_type == 'trend':
                        if sig:= self.atr_trailing_stop(data, self.df_5m):
                            self.fake_close_position(sig, self.Last_price, now)
                    else:
                        if sig:= self.atr_fixed_stop(data, self.df_1m):
                            self.fake_close_position(sig, self.Last_price, now)
                        if sig:= self.bband_stop(self.df_1m):
                            self.fake_close_position(sig, self.Last_price, now)

        
                # check for open position
                if not self.Buy_at and not self.Sell_at:
                    if trade_type == 'notrade':
                        pass
                    elif trade_type == 'trend':
                        if df_flag[PERIOD_5M]:
                            if sig := m.trend_strategy(self.df_5m):
                                self.fake_open_position(sig, self.Last_price, now)
                            df_flag[PERIOD_5M] = 0
                    else:
                        if df_flag[PERIOD_1M]:
                            if sig := m.consolidation_strategy_bb(self.df_1m):
                                self.fake_open_position(sig, self.Last_price, now)
                            df_flag[PERIOD_1M] = 0

            idicators_1m.reset_state_if_needed(market)
            idicators_5m.reset_state_if_needed(market)
            idicators_15m.reset_state_if_needed(market)

        print('======================================================')
        print(f'Income: {self.Total_profit-self.Trade_times*150}, Total_profit: {self.Total_profit}')
        print(f'Trade_times: {self.Trade_times}, Costs: {self.Trade_times*150}')
        print(f'Buy_profit: {sum(self.Buy_profit)}')
        print(f'Sell_profit: {sum(self.Sell_profit)}')

        self.export_trade_log()

        print(f'Buy_record:')
        for record in self.Buy_record:
            record[2] = record[2].strftime('%H:%M:%S')
            record[3] = record[3].strftime('%H:%M:%S')
            print(record)
        print(f'Sell_record:')
        for record in self.Sell_record:
            record[2] = record[2].strftime('%H:%M:%S')
            record[3] = record[3].strftime('%H:%M:%S')
            print(record)
        print('======================================================')


if __name__ == '__main__':
    mytest = Backtest(CSV_INPUT_DATA, 'main')
    mytest.run_test()
    print('===========================')
    print(mytest.df_1m.iloc[-10:])
    print('===========================')
    print(mytest.df_5m.iloc[-10:])

