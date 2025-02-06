import os
import csv
import datetime
import zipfile

CSV_INPUT_PATH = os.getcwd()
CSV_OUTPUT_PATH = CSV_INPUT_PATH + '\\twse_data'
def get_expiremonth(date):
    settlementdate = get_settlementDate(date)
    expiremonth = settlementdate.strftime('%Y%m')
    return expiremonth

def get_settlementDate(date):
    settlementDate = get_third_wen(date.year, date.month)

    if date > settlementDate:
        if date.month == 12:
            year = date.year+1
            next_month = 1
        else:
            year = date.year
            next_month = date.month+1
        settlementDate = get_third_wen(year, next_month)
    return settlementDate

def get_third_wen(y, m):
    date = (2-datetime.date(y, m, 1).weekday()+7)%7+15
    return datetime.date(y, m, date)

def get_filtered_twse_data(filename, expiremonth):
    with open(CSV_INPUT_PATH+'\\'+filename, newline='') as csvinput:
        with open(CSV_OUTPUT_PATH+'\\'+filename, 'w', newline='') as csvoutput:
        
            inputs = csv.reader(csvinput)
            output = csv.writer(csvoutput)
            header = next(inputs)
            output.writerow(header)

            for row in inputs:
                if row[1].strip() == 'TX' and row[2].strip() == expiremonth:
                    output.writerow(row)
    return

def extract_files(filename):
    with zipfile.ZipFile(CSV_INPUT_PATH+'\\'+filename, 'r') as zipf:
        zipf.extractall(CSV_INPUT_PATH)

if __name__ == '__main__':
    
    files = os.listdir(CSV_INPUT_PATH)
    for file in files:
        pullpath = os.path.join(CSV_INPUT_PATH ,file)
        if os.path.isfile(pullpath):
            data_type = file.split('.')
            if data_type[1] == 'zip':
                extract_files(file)
                print(f'{file} unzip completed.')
                os.remove(pullpath)

    files = os.listdir(CSV_INPUT_PATH)
    for file in files:
        pullpath = os.path.join(CSV_INPUT_PATH ,file)
        if os.path.isfile(pullpath):
            data_type = file.split('.')
            if data_type[1] == 'csv':
                data_date = data_type[0].split('_')
                data_year = int(data_date[1])
                data_month = int(data_date[2])
                data_day = int(data_date[3])
                expiremonth = get_expiremonth(datetime.date(data_year, data_month, data_day))
                get_filtered_twse_data(file, expiremonth)
                print(f'{file} / {expiremonth} completed.')
                os.remove(pullpath)
