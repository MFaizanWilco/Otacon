# import schedule
# import time
#
# def job():
#     print("I'm working...")
#
# schedule.every(1).seconds.do(job)
#
#
#
# while True:
#     schedule.run_pending()
#     time.sleep(1)
#
ib = ()

ib.connect('127.0.0.1', 7496, clientId=3)

contract = Contract()

contract.symbol = 'VIX'

contract.secType = "IND"

contract.exchange = "CBOE"

contract.currency = "USD"

ib.reqMktData(contract, '', False, False)

ticker = ib.ticker(contract)

ib.sleep(1)

vix_price = ticker.last

ib.cancelMktData(contract)

ib.disconnect()