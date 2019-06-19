from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract as IBcontract
from threading import Thread
import queue
import datetime
import time
import schedule
import stocksLSTM
import datetime
from Config import Configuration
import mongodb
import pandas as pd
import calendar
from dateutil import parser
from datetime import timedelta

DEFAULT_HISTORIC_DATA_ID=222

DEFAULT_GET_CONTRACT_ID=43
barSize = ['5 mins', '15 Mins', '30 Mins', '1 H', '4 Hours']

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


    def get_IB_historical_data(self, ibcontract, durationStr="1 Y", barSizeSetting="1 day",tickerid=DEFAULT_HISTORIC_DATA_ID):
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


class DataFeed:
    def __init__(self):
        self.name = "DataFeed"
        self.Company = Configuration().GetData()['CompanyList']
        self.CompanyP = Configuration().GetData()['CompanyListP']
        self.APIKEYS = Configuration().GetData()['APIKEYDICT']

    def strategy(self,dataset):
        dataset = pd.DataFrame(dataset)
        signal = 1
        dataset['signal'] = signal
        for index, row in dataset.iterrows():
            if dataset["open"][index] > dataset["close"][index]:
                signal = 1
            else:
                signal = 0
            print(signal)
            dataset['signal'][index] = signal
        return dataset

    def getdata(self):
        app = TestApp("0.0.0.0", 4001, 10)
        for com in Configuration().GetData()['CompanyList']:
            ibcontract = IBcontract()
            ibcontract.secType = "STK"
            ibcontract.lastTradeDateOrContractMonth = "201809"
            ibcontract.symbol = com
            ibcontract.exchange = "SMART"
            resolved_ibcontract = app.resolve_ib_contract(ibcontract)
            dataset1 = {0: ['20190502  13:30:00', '20190502  16:00:00'], 1: [209.95, 208.65], 2: [212.65, 210.29],
                        3: [208.13, 208.41], 4: [208.63, 209.17], 5: [149612, 100915]}
            durationstr = "3600 S"
            # historic_data = app.get_IB_historical_data(resolved_ibcontract, durationstr, bar)
            df = pd.DataFrame(dataset1)
            df.rename(columns={0:"date",1:"open", 2:"high", 3:"low", 4:"close",5:"volume"}, inplace=True)
            for bar in barSize:
                dataset = self.strategy(df)
                print(com)
                print(bar)
                # MongoStore().Feed_IntraDay(com, bar, dataset)
                print(df)

    def getNextDate(self, currrentDate):
        curDate = parser.parse(currrentDate).date()
        nextDay = curDate + timedelta(days=int(1))
        weekend = ['Saturday', 'Sunday']

        while calendar.day_name[nextDay.weekday()] in weekend:
            nextDay = nextDay + timedelta(days=int(1))
        return nextDay

    # def next_day_prediction(self):
    #     collectionname = 'IntraDay'
    #     for com in self.CompanyP:
    #         value = mongodb.ReadValue(collectionname, com)['Data']
    #         # df = pd.DataFrame(eval(value))
    #         # print(df)
    #         # next_date = DataFeed().getNextDate((df['date'].max()).split(' ')[0])
    #         df = {"date": ['20190502  13:30:00', '20190502  16:00:00'], "open": [209.95, 208.65], "high": [212.65, 210.29],"low": [208.13, 208.41], "close": [208.63, 209.17], "volume": [149612, 100915]}
    #         next_date = DataFeed().getNextDate((df['date'].max()).split(' ')[0])
    #         if 'volume' in df.columns:
    #             del df['volume']
    #         dataframe = df.reset_index(drop=True)
    #         dates = dataframe['date'].copy()
    #         del dataframe['date']
    #         seedValue = dataframe.tail(1)
    #         dataframe, scaler = stocksLSTM.ScaleDataSet(dataframe)
    #         dataframe = stocksLSTM.prepareDataSet(dataframe)
    #         model, details = stocksLSTM.trainModel(dataframe)
    #         seedValue, _ = stocksLSTM.ScaleDataSet(seedValue, scaler)
    #         p_df = stocksLSTM.predictfulDay(model, details, seedValue)
    #         p_df = stocksLSTM.deScaleData(p_df, scaler)
    #         rng = pd.date_range(str(next_date) + ' ' + '09:35:00', periods=100, freq='5min')
    #         ts = pd.Series(rng)
    #         p_df['date'] = ts
    #         p_df['date'] = p_df['date'].astype(str)
    #         # print(p_df)
    #         mongodb.UpdateValue('FuturePrediction', com, p_df.to_dict(orient='list'))

    def same_day_prediction(self):
        collectionname = ['IntraDay5 mins','IntraDay4 hours']
        for col in collectionname:
            for com in self.CompanyP:
                value = mongodb.ReadValue(col, com)['Data']
                df = pd.DataFrame(eval(value))
                # print(df)
                # df = {"date": ['20190502  13:30:00', '20190502  16:00:00'], "open": [209.95, 208.65],
                #       "high": [212.65, 210.29], "low": [208.13, 208.41], "close": [208.63, 209.17],
                #       "volume": [149612, 100915]}
                # next_date = DataFeed().getNextDate((df['date'].max()).split(' ')[0])
                df.rename(columns={0: "date", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume"}, inplace=True)

                if 'volume' in df.columns:
                    del df['volume']

                dataframe = df.reset_index(drop=True)
                dates = dataframe['date'].copy()
                signals = dataframe['signal'].copy()
                del dataframe['date']
                del dataframe['signal']

                dfleng = len(dataframe.index)-1
                testEnd = dataframe.iloc[dfleng:].copy()
                trainStart = dataframe.drop(dataframe.index[dfleng:])

                trainStart, scaler = stocksLSTM.ScaleDataSet(trainStart)
                testEnd, _ = stocksLSTM.ScaleDataSet(testEnd, scaler)

                # testEnd = testEnd.shift(-1)
                # testEnd = testEnd.dropna()
                # testEnd.reset_index(drop=True, inplace=True)
                trainStart = stocksLSTM.prepareDataSet(trainStart)
                model, details = stocksLSTM.trainModel(trainStart)

                presults = stocksLSTM.predict(model, testEnd)
                presults = stocksLSTM.deScaleData(presults, scaler)
                ndates = pd.DataFrame(dates[dfleng:], columns=['date'])
                nsignals = pd.DataFrame(signals[dfleng:], columns=['signal'])

                # ndates = ndates.shift(-1)
                # ndates = ndates.dropna()
                ndates.reset_index(drop=True, inplace=True)
                nsignals.reset_index(drop=True, inplace=True)
                presults = pd.concat([presults, ndates], axis=1)
                presults = pd.concat([presults, nsignals], axis=1)
                print(presults)
                presults = pd.DataFrame(presults)
                presults.rename(
                    columns={"date": "dateP", "open": "openP", "high": "highP", "low": "lowP", "close": "closeP",
                             "signal": "signalP"}, inplace=True)
                presults1 = self.strategy(presults)

                df.reset_index(drop=True, inplace=True)
                presults = pd.concat([presults, df], axis=1)
                print(presults1)
                date_filter = (presults['date'].max()).split(' ')[0]
                # mongodb.UpdateValue(col+"Predict", com + ' ' + str(date_filter), presults1.to_dict(orient='list'))
                mongodb.UpdateValue(col + "Predict", com, presults1.to_dict(orient='list'))

class MongoStore():
    def Feed_IntraDay(self,com, Interval, data):
        collectionname = 'IntraDay' + Interval
        try:
            data = pd.DataFrame(data)
            # data.reset_index(inplace=True)
            mongodb.UpdateValue(collectionname, com, data.to_dict(orient='list'))
        except Exception as e:
            print('Company Ignore due to high service call' + '\nError : ' + str(e))


def daily_feeding():
    print("Run-----")
    # DataFeed().getdata()
    DataFeed().same_day_prediction()
    while True:
        schedule.run_pending()
        time.sleep(60)     # wait one second

if __name__ == '__main__':
    schedule.every(5).minutes.do(daily_feeding())