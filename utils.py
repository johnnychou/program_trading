import time
import datetime


def period_to_minute(period_str):
    value = int(period_str[:-1])  # 提取數值
    unit = period_str[-1]       # 提取單位

    if unit != 'm':
        raise ValueError("Invalid period. It should have [m] at last.")

    return value  # 如果單位不正確，則傳回 None

def sync_time(period): #period->minutes
    if period < 1:
        period = 1

    while True:
        now = datetime.datetime.now()
        while now.second != 0:
            # print(f'time synchronizing... {period - (now.minute % period) - 1}:{60 - now.second}')
            time.sleep(0.1)
            now = datetime.datetime.now()

        if (now.minute % period) == 0:
            break

        time.sleep(1)
    return

def get_market_type():  # 0 = 日盤 / regular, 1 = 夜盤 / afterhours, -1 = 非交易時段
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()  # Monday=0, Sunday=6

    # 台股日盤：週一～週五，08:45 至 13:45
    if (0 <= weekday <= 4) and (8 <= hour <= 13):
        if hour == 8 and minute < 45:
            return '-1'
        if hour == 13 and minute > 45:
            return '-1'
        return '0'

    # 台股夜盤：週一晚到週五晚 (15:00~24:00) 及週二凌晨到週六凌晨 (00:00~05:00)
    if ((0 <= hour < 5 and 1 <= weekday <= 5) or
        (15 <= hour <= 23 and 0 <= weekday <= 4)):
        return '1'

    return '-1'  # 非交易時段

def get_txf_settlementDate():
    today = datetime.date.today()
    settlementDate = get_third_wen(today.year, today.month)
    if today > settlementDate:
        if today.month == 12:
            year = today.year+1
            next_month = 1
        else:
            year = today.year
            next_month = today.month+1
        settlementDate = get_third_wen(year, next_month)
    return settlementDate

def get_expiremonth(date=datetime.date.today()):
    settlementdate = get_settlementDate(date)
    expiremonth = settlementdate.strftime('%Y%m')
    return expiremonth

def get_settlementDate(date=datetime.date.today()):
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

def get_expiremonth_realtime():
    settlementdate = get_settlementDate_realtime()
    expiremonth = settlementdate.strftime('%Y%m')
    return expiremonth

def get_settlementDate_realtime():
    now = datetime.datetime.now()
    today = now.date()
    settlementDate = get_third_wen(today.year, today.month)

    if today >= settlementDate:
        if today == settlementDate:
            if now.hour < 14:
                return settlementDate

        # 若已過本月結算日，則找下個月的
        if today.month == 12:
            year = today.year + 1
            next_month = 1
        else:
            year = today.year
            next_month = today.month + 1
        settlementDate = get_third_wen(year, next_month)

    return settlementDate

def get_third_wen(y, m):
    date = (2-datetime.date(y, m, 1).weekday()+7)%7+15
    return datetime.date(y, m, date)