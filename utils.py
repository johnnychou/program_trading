import time
import datetime

def get_market_type(): #0=日盤/regular, 1=夜盤/Afterhours -1=非交易時段
    localtime = time.localtime()

    #start from 08:45
    if (8 <= localtime.tm_hour <= 13) and (0 <= localtime.tm_wday <= 4): #台股日盤
        if (localtime.tm_hour == 8) and (localtime.tm_min < 45):
            return '-1'
        if (localtime.tm_hour == 13) and (localtime.tm_min > 45):
            return '-1'
        return '0'

    if ((0 <= localtime.tm_hour < 5) and (1 <= localtime.tm_wday <= 5)) or\
         ((15 <= localtime.tm_hour <= 23) and (0 <= localtime.tm_wday <= 4)): #夜盤
        return '1'

    return '-1' #非交易時段

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
    localtime = time.localtime()
    today=datetime.date.today()
    settlementDate = get_third_wen(today.year, today.month)

    if today >= settlementDate:
        if today == settlementDate:
            if localtime.tm_hour < 14:
                return settlementDate

        if today.month == 12:
            year = today.year+1
            next_month = 1
        else:
            year = today.year
            next_month = today.month+1
        settlementDate = get_third_wen(year, next_month)
    return settlementDate

def get_third_wen(y, m):
    date = (2-datetime.date(y, m, 1).weekday()+7)%7+15
    return datetime.date(y, m, date)