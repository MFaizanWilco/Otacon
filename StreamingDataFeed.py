# IMPORTING IMPORTANT LIBRARIES
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import keras
from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.layers import LSTM
from pymongo import MongoClient
import json
import os
import urllib.request, json
import datetime as dt
import time
import schedule

api_key = '7RTIYBPQOBBZ5WR0'
Ticker = ['aal', 'msft', 'aapl', 'hpq']


def Populate_Data(ticker,interval):
    url_string = "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=%s&outputsize=full&interval=%s&apikey=%s" %(ticker, interval, api_key)
    print(url_string)
    print("**********************POPULATING DATA OF %s FOR THE INTERVAL %s**********************"%(ticker,interval))
    # Save data to this file
    # file_to_save = 'stock_market_data_%s.csv' % ticker
    myjsonfile = urllib.request.urlopen(url_string).read().decode()
    # print(myjsonfile)
    mng_client = MongoClient("34.222.163.101",28000)
    mng_db = mng_client['LstmPrediction'] #Replace mongo db name
    collection_name = 'IntraDay_%s'%(interval.replace('min','')) #Replace mongo db collection name
    db_cm = mng_db[collection_name]
    #db_cm.remove()
    data = json.loads(myjsonfile)

    db_cm.insert(data, check_keys= False)
    mng_client.close()

def Get_Interval(case):
    if case == 0:
        interval = '5min'
    elif case == 1:
        interval = '15min'
    elif case == 2:
        interval = '30min'
    elif case == 3:
        interval = '60min'
    return interval



def Get_Data():
    for case in range(4):
        Interval = Get_Interval(case)
        for company_name in range(len(Ticker)):
            Populate_Data(Ticker[company_name], Interval)
            time.sleep(10)
    time.sleep(10)

if __name__ == '__main__':
    Get_Data()
    # schedule.every(1).minutes.do(Get_Data)

    while 1:
        schedule.run_pending()
        time.sleep(1)