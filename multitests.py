
import multiprocessing
import os
import csv
import backtest
import time
import datetime
from constant import *

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
TRADE_FEE = 150
TRADING_MARKET = 'main'
MAX_CONCURRENT = multiprocessing.cpu_count()-3  # 最多同時跑幾個 process
# MAX_CONCURRENT = 1

class TestProcess(multiprocessing.Process):
    def __init__(self, filename, pullpath):
        super(TestProcess, self).__init__()
        self.filename = filename
        self.fullpath = pullpath
        self.backtest = backtest.Backtest(self.fullpath, TRADING_MARKET)

    def run(self):
        print(f'File:{self.filename}, starting test!')
        self.backtest.run_test()

All_Process = []
Month_statistics = {}
Total_profit = 0
Total_income = 0
Total_trade_times = 0
Total_buy_profit = 0
Total_sell_profit = 0
Total_day_profit = 0
Total_night_profit = 0

if __name__ == '__main__':
    files = [f for f in os.listdir(CSV_INPUT_PATH) if f.endswith('.csv')]
    total_files = len(files)
    remaining = list(files)  # 還沒跑的
    running = []             # 正在跑的

    print(f'=== Total Files to Test : {total_files} ===')
    print(f'=== Concurrent Processes: {MAX_CONCURRENT} ===')

    while remaining or running:
        # 啟動新的 process（不超過 MAX_CONCURRENT）
        while remaining and (len(running) < (MAX_CONCURRENT)):
            filename = remaining.pop(0)
            fullpath = os.path.join(CSV_INPUT_PATH, filename)
            p = TestProcess(filename, fullpath)
            running.append((p, filename))
            p.start()
        
        # 檢查已完成的 process
        for p, filename in running[:]:
            if not p.is_alive():
                running.remove((p, filename))
                print(f'{filename} completed. Remaining: {len(remaining)}. Running: {len(running)}')

        time.sleep(0.5)  # 減少 CPU 資源浪費

    print('=== All tests completed ===')

    results = os.listdir(CSV_OUTPUT_PATH)
    for file in results:
        data_date = file.split('_')
        year_month = data_date[1] + data_date[2]
        if year_month not in Month_statistics.keys():
            Month_statistics[year_month] = [0, 0, 0] #income, profit, costs

        with open(CSV_OUTPUT_PATH+'\\'+file, newline='') as profitdata:
            data = csv.reader(profitdata)
            profit = int(next(data)[1])
            income = int(next(data)[1])
            trade_times = int(next(data)[1])
            buy_profit = int(next(data)[1])
            sell_profit = int(next(data)[1])

            Total_profit += profit
            Total_income += income
            Total_trade_times += trade_times
            Total_buy_profit += buy_profit
            Total_sell_profit += sell_profit

            Month_statistics[year_month][0] += income
            Month_statistics[year_month][1] += profit
            Month_statistics[year_month][2] += trade_times*TRADE_FEE

            next(data) # 空行
            next(data) # 欄位名稱

            day_start_time = datetime.datetime.strptime(DAY_MARKET[0], "%H:%M:%S").time()
            day_end_time = datetime.datetime.strptime(DAY_MARKET[1], "%H:%M:%S").time()
            format_code = "%Y-%m-%d %H:%M:%S"

            while True:  # 無限迴圈
                try:
                    trade_details = next(data)
                    data_datetime = datetime.datetime.strptime(trade_details[5], format_code)
                    if day_start_time <= data_datetime.time() <= day_end_time:
                        Total_day_profit += int(trade_details[3])
                    else:
                        Total_night_profit += int(trade_details[3])
                except StopIteration:
                    break
                except Exception as e:
                    print(f"處理行數據時發生錯誤: {e}")
                    break


    
    print('================================================')
    print(f'Total_income: {Total_income}')
    print(f'Total_profit: {Total_profit}')
    print(f'Total_trade_times: {Total_trade_times}, Costs: {Total_trade_times*TRADE_FEE}')
    print(f'Total_buy_profit: {Total_buy_profit}, Total_sell_profit: {Total_sell_profit}')
    print(f'Total_day_profit: {Total_day_profit}, Total_night_profit: {Total_night_profit}')
    for key, value in Month_statistics.items():
        print(f'Month: {key}, Income: {value[0]}, Profit: {value[1]}, Costs: {value[2]}')
