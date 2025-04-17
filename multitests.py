
import multiprocessing
import os
import csv
import backtest
import time

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
TRADING_MARKET = 'day'
MAX_CONCURRENT = 10  # 最多同時跑幾個 process

class TestProcess(multiprocessing.Process):
    def __init__(self, filename, pullpath):
        super(TestProcess, self).__init__()
        self.filename = filename
        self.fullpath = pullpath

    def run(self):
        print(f'File:{self.filename}, starting test!')
        backtest.run_test(self.fullpath, TRADING_MARKET)

All_Process = []

if __name__ == '__main__':
    files = [f for f in os.listdir(CSV_INPUT_PATH) if f.endswith('.csv')]
    total_files = len(files)
    remaining = list(files)  # 還沒跑的
    running = []             # 正在跑的

    print(f'=== Total Files to Test: {total_files} ===')

    while remaining or running:
        # 啟動新的 process（不超過 MAX_CONCURRENT）
        while remaining and len(running) < MAX_CONCURRENT:
            filename = remaining.pop(0)
            fullpath = os.path.join(CSV_INPUT_PATH, filename)
            p = TestProcess(filename, fullpath)
            p.start()
            running.append((p, filename))
        
        # 檢查已完成的 process
        for p, filename in running[:]:
            if not p.is_alive():
                running.remove((p, filename))
                print(f'{filename} completed. Remaining: {len(remaining)}')

        time.sleep(0.5)  # 減少 CPU 資源浪費

    print('=== All tests completed ===')
