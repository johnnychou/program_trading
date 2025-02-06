import sys
import datetime

import requests as r

import fubon_neo
from fubon_neo.sdk import FubonSDK, FutOptOrder
from fubon_neo.constant import TimeInForce, FutOptOrderType, FutOptPriceType, FutOptMarketType, CallPut, BSAction

sys.path.append('C:\\Users\\ChengWei\\Desktop\\my project')
import accinfo as key


def chk_inventories():
    inventories = sdk.accounting.inventories(ACCOUNT.data[0])
    print(inventories)

def chk_profit():
    unrealized_pnl = sdk.accounting.unrealized_gains_and_loses(ACCOUNT.data[0])
    print(unrealized_pnl.data)
    profit = 0
    loss = 0
    for i in range(len(unrealized_pnl.data)):
        profit += unrealized_pnl.data[i].unrealized_profit
        loss += unrealized_pnl.data[i].unrealized_loss
    print(f"Total profit: {profit}\nTotal loss: {loss}")

def chk_remainings():
    balance = sdk.accounting.bank_remain(ACCOUNT.data[0])
    print(f"Account Balance: {balance}")

def get_third_wen(y, m):
    date = (2-datetime.date(y, m, 1).weekday()+7)%7+15
    return datetime.date(y, m, date)

def get_txf_settlementDate():
    today = datetime.date.today()
    settlementDate=get_third_wen(today.year, today.month)
    if today > settlementDate:
        if today.month == 12:
            year = today.year+1
            next_month = 1
        else:
            year = today.year
            next_month = today.month+1
        settlementDate=get_third_wen(year, next_month)
    return settlementDate

def get_txf_symbol():
    settlementDate = get_txf_settlementDate() 
    timesession='AFTERHOURS'
    future_data=restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX',session=timesession, contractType='I', status='N')
    #future_data=restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX', contractType='I', status='N')
    #print(future_data)
    for i in range(len(future_data['data'])):
        if ('臺股期貨' in future_data['data'][i]['name']) and\
        (future_data['data'][i]['settlementDate'] == settlementDate.isoformat()):
            txf_symbol = future_data['data'][i]['symbol']
            break
    return txf_symbol

def get_tmf_symbol():
    settlementDate = get_txf_settlementDate()
    # timesession='AFTERHOURS'
    # future_data=restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX', session=timesession, contractType='I', status='N')
    future_data=restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX', contractType='I', status='N')
    for i in range(len(future_data['data'])):
        if ('微型臺指' in future_data['data'][i]['name']) and\
        (future_data['data'][i]['settlementDate'] == settlementDate.isoformat()):
            tmf_symbol = future_data['data'][i]['symbol']
            break
    return tmf_symbol

def get_mxf_symbol():
    settlementDate = get_txf_settlementDate()
    # timesession='AFTERHOURS'
    # future_data=restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX', session=timesession, contractType='I', status='N')
    future_data=restfut.intraday.tickers(type='FUTURE', exchange='TAIFEX', contractType='I', status='N')
    for i in range(len(future_data['data'])):
        if ('小型臺指' in future_data['data'][i]['name']) and\
        (future_data['data'][i]['settlementDate'] == settlementDate.isoformat()):
            mxf_symbol = future_data['data'][i]['symbol']
            break
    return mxf_symbol

def init_account_balance(account):
    return

def get_future_account():
    for acc in ACCOUNT:
        if acc.account_type == 'futopt':
            return acc
    return None

sdk = FubonSDK()
print("fubon api version: " + fubon_neo.__version__)

ACCOUNT = sdk.login(key.id, key.pwd, key.ca, key.ca_pwd) #若有歸戶，則會回傳多筆帳號資訊

if ACCOUNT.is_success == True:
    ACCOUNT = ACCOUNT.data

print(ACCOUNT)

sdk.init_realtime() # 建立行情連線

acc_future = get_future_account()
print(acc_future)

balance = sdk.futopt_accounting.query_margin_equity(acc_future)
print('=====')
print(balance)
print(balance.data[0].today_equity)

restfut = sdk.marketdata.rest_client.futopt
txf_symbol = get_txf_symbol()
print(f'臺股期貨 TXF Symbol: {txf_symbol}')
mxf_symbol = get_mxf_symbol()
print(f'小型臺指 MXF Symbol: {mxf_symbol}')
tmf_symbol = get_tmf_symbol()
print(f'微型臺指 TMF Symbol: {tmf_symbol}')

# order = FutOptOrder(
#     buy_sell = BSAction.Buy,
#     symbol = tmf_symbol,
#     lot = 1,
#     market_type = FutOptMarketType.FutureNight,
#     price_type = FutOptPriceType.RangeMarket,
#     time_in_force = TimeInForce.IOC,
#     order_type = FutOptOrderType.Auto,
#     user_def = "From Python" # optional field
# )

#sendorder = sdk.futopt.place_order(acc_future, order)
#print(sendorder)

#positions = sdk.futopt_accounting.query_hybrid_position(acc_future)
positions = sdk.futopt_accounting.query_single_position(acc_future)
print(positions)
print(positions.is_success)
print(type(positions.is_success))

if positions.data:
    print(positions.data[0].price)

    for i in positions.data:
        print('=====')
        print(i.buy_sell)
        if i.buy_sell == BSAction.Buy:
            print('buy')
        if i.buy_sell == BSAction.Sell:
            print('sell')
        print(f'price: {i.price}')
        print(type(i.price))
        print(i.symbol)
        print(type(i.symbol))
        print(i.tradable_lot)
        print(type(i.tradable_lot))
else:
    print('There is no position.')

print('=====')
restfutopt = sdk.marketdata.rest_client.futopt  
txfvol = restfutopt.intraday.volumes(symbol=txf_symbol, session='afterhours')
last_data = txfvol['data'][:10]
for data in last_data:
    print(data)

print(datetime.datetime.now())
print(txf_symbol)
#data_d = restfut.intraday.candles(symbol=txf_symbol, timeframe='1')
data_n = restfut.intraday.candles(symbol=txf_symbol, timeframe='1', session='afterhours')
data_n_first = data_n['data'][:5]
data_n_last = data_n['data'][-5:]
for i in data_n_first:
    print(i)
print('==========')
for i in data_n_last:
    print(i)
