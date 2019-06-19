from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract as IBcontract
from ibapi.ticktype import TickTypeEnum
from threading import Thread
import queue
import datetime
import time
import schedule
import datetime
from Config import Configuration
import mongodb
import pandas as pd


DEFAULT_HISTORIC_DATA_ID=222

DEFAULT_GET_CONTRACT_ID=43
barSize = ['1 min','5 mins', '15 mins', '30 mins', '1 hour', '4 hours']
## marker for when queue is finished
FINISHED = object()
STARTED = object()
TIME_OUT = object()


class finishableQueue(object):

   def __init__(self, queue_to_finish):

       self._queue = queue_to_finish
       self.status = STARTED

   def get(self, timeout):
       """
       Returns a list of queue elements once timeout is finished, or a FINISHED flag is received in the queue
       :param timeout: how long to wait before giving up
       :return: list of queue elements
       """
       contents_of_queue=[]
       finished=False

       while not finished:
           try:
               current_element = self._queue.get(timeout=timeout)
               if current_element is FINISHED:
                   finished = True
                   self.status = FINISHED
               else:
                   contents_of_queue.append(current_element)
                   ## keep going and try and get more data

           except queue.Empty:
               ## If we hit a time out it's most probable we're not getting a finished element any time soon
               ## give up and return what we havew
               finished = True
               self.status = TIME_OUT


       return contents_of_queue

   def timed_out(self):
       return self.status is TIME_OUT

class TestWrapper(EWrapper):

   def __init__(self):
       self._my_contract_details = {}
       self._my_historic_data_dict = {}

   ## error handling code
   def init_error(self):
       error_queue=queue.Queue()
       self._my_errors = error_queue

   def get_error(self, timeout=5):
       if self.is_error():
           try:
               return self._my_errors.get(timeout=timeout)
           except queue.Empty:
               return None

       return None

   def is_error(self):
       an_error_if=not self._my_errors.empty()
       return an_error_if

   def error(self, id, errorCode, errorString):
       ## Overriden method
       errormsg = "IB error id %d errorcode %d string %s" % (id, errorCode, errorString)
       self._my_errors.put(errormsg)


   ## get contract details code
   def init_contractdetails(self, reqId):
       contract_details_queue = self._my_contract_details[reqId] = queue.Queue()

       return contract_details_queue

   def contractDetails(self, reqId, contractDetails):
       ## overridden method

       if reqId not in self._my_contract_details.keys():
           self.init_contractdetails(reqId)

       self._my_contract_details[reqId].put(contractDetails)

   def contractDetailsEnd(self, reqId):
       ## overriden method
       if reqId not in self._my_contract_details.keys():
           self.init_contractdetails(reqId)

       self._my_contract_details[reqId].put(FINISHED)

   ## Historic data code
   def init_historicprices(self, tickerid):
       historic_data_queue = self._my_historic_data_dict[tickerid] = queue.Queue()

       return historic_data_queue


   def historicalData(self, tickerid , bar):

       ## Overriden method
       ## Note I'm choosing to ignore barCount, WAP and hasGaps but you could use them if you like
       bardata=(bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume)

       historic_data_dict=self._my_historic_data_dict

       ## Add on to the current data
       if tickerid not in historic_data_dict.keys():
           self.init_historicprices(tickerid)

       historic_data_dict[tickerid].put(bardata)

   def historicalDataEnd(self, tickerid, start:str, end:str):
       ## overriden method

       if tickerid not in self._my_historic_data_dict.keys():
           self.init_historicprices(tickerid)

       self._my_historic_data_dict[tickerid].put(FINISHED)

class TestClient(EClient):

   def __init__(self, wrapper):
       ## Set up with a wrapper inside
       EClient.__init__(self, wrapper)


   def resolve_ib_contract(self, ibcontract, reqId=DEFAULT_GET_CONTRACT_ID):

       """
       From a partially formed contract, returns a fully fledged version
       :returns fully resolved IB contract
       """

       ## Make a place to store the data we're going to return
       contract_details_queue = finishableQueue(self.init_contractdetails(reqId))

       print("Getting full contract details from the server... ")

       self.reqContractDetails(reqId, ibcontract)

       ## Run until we get a valid contract(s) or get bored waiting
       MAX_WAIT_SECONDS = 10
       new_contract_details = contract_details_queue.get(timeout = MAX_WAIT_SECONDS)

       while self.wrapper.is_error():
           print(self.get_error())

       if contract_details_queue.timed_out():
           print("Exceeded maximum wait for wrapper to confirm finished - seems to be normal behaviour")

       if len(new_contract_details)==0:
           print("Failed to get additional contract details: returning unresolved contract")
           return ibcontract

       if len(new_contract_details)>1:
           print("got multiple contracts using first one")

       new_contract_details=new_contract_details[0]

       resolved_ibcontract=new_contract_details.contract

       return resolved_ibcontract


   def get_IB_historical_data(self, ibcontract, durationStr="1 Y", barSizeSetting="1 day",
                              tickerid=DEFAULT_HISTORIC_DATA_ID):
       historic_data_queue = finishableQueue(self.init_historicprices(tickerid))

       self.reqHistoricalData(
           tickerid,  # tickerId,
           ibcontract,  # contract,
           datetime.datetime.today().strftime("%Y%m%d %H:%M:%S %Z"),  # endDateTime,
           durationStr,  # durationStr,
           barSizeSetting,  # barSizeSetting,
           "TRADES",  # whatToShow,
           1,  # useRTH,
           1,  # formatDate
           False,  # KeepUpToDate <<==== added for api 9.73.2
           [] ## chartoptions not used
       )



       ## Wait until we get a completed data, an error, or get bored waiting
       MAX_WAIT_SECONDS = 10
       print("Getting historical data from the server... could take %d seconds to complete " % MAX_WAIT_SECONDS)

       historic_data = historic_data_queue.get(timeout = MAX_WAIT_SECONDS)

       while self.wrapper.is_error():
           print(self.get_error())

       if historic_data_queue.timed_out():
           print("Exceeded maximum wait for wrapper to confirm finished - seems to be normal behaviour")

       self.cancelHistoricalData(tickerid)


       return historic_data

class TestApp(TestWrapper, TestClient):
   def __init__(self, ipaddress, portid, clientid):
       TestWrapper.__init__(self)
       TestClient.__init__(self, wrapper=self)

       self.connect(ipaddress, portid, clientid)

       thread = Thread(target = self.run)
       thread.start()

       setattr(self, "_thread", thread)

       self.init_error()

   def tickPrice(self, reqId, tickType, price: float,
                 attrib):
       print("Tick Price. Ticker Id:", reqId, "tickType:", TickTypeEnum.to_str(tickType), "Price:",price, end=' ')

   def tickSize(self, reqId, tickType, size:int):
        print("Tick Size. Ticker Id:", reqId, "tickType:", TickTypeEnum.to_str(tickType), "Size:",size)


def Feed_IntraDay(com, Interval, data):
   collectionname = 'IntraDay'+Interval
   try:
       data = pd.DataFrame(data)
       # data.reset_index(inplace=True)
       mongodb.UpdateValue(collectionname, com, data.to_dict(orient='list'))
   except Exception as e:
       print('Company Ignore due to high service call' + '\nError : ' + str(e))


def streaming():
    app = TestApp("0.0.0.0", 4001, 9)
    contract = IBcontract()
    contract.symbol = 'AAPL'
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.primaryExchange = "NASDAQ"

    app.reqMarketDataType(4)
    req = app.reqMktData(1,contract,"",False,False,[])
    print(req)
    # REALDATA = app.reqMktData(contract, '', False, False)
    # ticker = app.ticker(contract)
    # app.sleep(1)
    # vix_price = ticker.last
    # app.cancelMktData(contract)
    # app.disconnect()


def data_feed():
   app = TestApp("0.0.0.0", 4001, 9)
   for com in Configuration().GetData()['CompanyList']:
       ibcontract = IBcontract()
       ibcontract.secType = "STK"
       ibcontract.lastTradeDateOrContractMonth="201809"
       ibcontract.symbol = com
       ibcontract.exchange = "SMART"
       resolved_ibcontract = app.resolve_ib_contract(ibcontract)
       durationstr = "1 D"
       for bar in barSize:
           historic_data = app.get_IB_historical_data(resolved_ibcontract,durationstr,bar)
           signal = 1
           dataset = pd.DataFrame(historic_data)
           dataset['signal'] = signal
           for index, row in dataset.iterrows():
               if dataset['open'][index] > dataset['close'][index]:
                   signal = 1
               else:
                   signal = 0
               print(signal)
               dataset['signal'][index] = signal
               print(com)
           print(bar)
           Feed_IntraDay(com,bar,dataset)
           print(dataset)


def daily_feeding():
   print("Run-----")
   data_feed()
   while True:
       schedule.run_pending()
       time.sleep(60)     # wait one second

if __name__ == '__main__':
    # schedule.every(1).minutes.do(daily_feeding())
    streaming()
