
import multiprocessing
import os
import csv
import backtest

CSV_INPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\twse_data\filtered'
CSV_OUTPUT_PATH = r'C:\Users\ChengWei\Desktop\program trading\testing result'
TRADING_MARKET = 'day'

class TestProcess(multiprocessing.Process):
    def __init__(self, filename, pullpath):
        super(TestProcess, self).__init__()
        self.filename = filename
        self.fullpath = pullpath

    def run(self):
        print(f'File:{self.filename}, starting test!')
        backtest.run_test(self.fullpath)

All_Process = []

if __name__ == '__main__':
    total_amount = 0
    files = os.listdir(CSV_INPUT_PATH)
    for file in files:
        if file.endswith('.csv'):
            total_amount += 1
            pullpath = os.path.join(CSV_INPUT_PATH, file)
            p = TestProcess(file, pullpath)
            All_Process.append(p)
            p.start()
            input()

    print(f'=== Tested Days: {total_amount} ===')

    while True:
        for proc in All_Process:
            #print(f'{proc.filename} is processing.')
            if not proc.is_alive():
                total_amount -= 1
                print(f'{proc.filename} is completed. Remaining: {total_amount}')
                All_Process.remove(proc)
        if total_amount == 0:
            break
    