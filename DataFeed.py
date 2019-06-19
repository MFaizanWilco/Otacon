import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import schedule
import time
import sys
from alpha_vantage.timeseries import TimeSeries
from Config import Configuration
import mongodb
import pandas as pd
from dateutil import parser
from datetime import timedelta
import calendar
import stocksLSTM
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


class DataFeed:
    def __init__(self):
        self.name = "DataFeed"
        self.Company = Configuration().GetData()['CompanyList']
        self.CompanyP = Configuration().GetData()['CompanyListP']
        self.APIKEYS = Configuration().GetData()['APIKEYDICT']

    # to get ticket names (data we have) / Company_names
    def Feed_IntraDay(self, collectionname, Interval):
        # collectionname = 'IntraDay'
        for com in self.Company:
            try:
                ts = TimeSeries(key=self.APIKEYS[0], output_format='pandas')
                data, meta_data = ts.get_intraday(com, interval=Interval, outputsize="full")
                data = pd.DataFrame(data)
                data.reset_index(inplace=True)
                mongodb.UpdateValue(collectionname, com, data.to_dict(orient='list'))
                # mongodb.WriteValue(collectionname, com, data.to_dict(orient='list'))
                # print(data)
            except Exception as e:
                print('Company Ignore due to high service call' + '\nError : ' + str(e))

    # def Feed_Daily(self):
    #     collectionname = 'Daily'
    #     for com in self.Company:
    #         try:
    #             ts = TimeSeries(key=self.APIKEYS[5], output_format='pandas')
    #             data, meta_data = ts.get_daily(com, outputsize="full")
    #             data = pd.DataFrame(data)
    #             data.reset_index(inplace=True)
    #             mongodb.UpdateValue(collectionname, com, data.to_dict(orient='list'))
    #             # mongodb.WriteValue(collectionname, com, data.to_dict(orient='list'))
    #             # print(data)
    #         except Exception as e:
    #             print('Company Ignore due to high service call' + '\nError : ' + str(e))
    #
    # def Feed_Weekly(self):
    #     collectionname = 'Weekly'
    #     for com in self.Company:
    #         try:
    #             ts = TimeSeries(key=self.APIKEYS[2], output_format='pandas')
    #             data, meta_data = ts.get_weekly(com)
    #             data = pd.DataFrame(data)
    #             data.reset_index(inplace=True)
    #             mongodb.UpdateValue(collectionname, com, data.to_dict(orient='list'))
    #             # mongodb.WriteValue(collectionname, com, data.to_dict(orient='list'))
    #             # print(data)
    #         except Exception as e:
    #             print('Company Ignore due to high service call' + '\nError : ' + str(e))
    #
    # def Feed_Monthly(self):
    #     collectionname = 'Monthly'
    #     for com in self.Company:
    #         try:
    #             ts = TimeSeries(key=self.APIKEYS[3], output_format='pandas')
    #             data, meta_data = ts.get_monthly(com)
    #             data = pd.DataFrame(data)
    #             data.reset_index(inplace=True)
    #             mongodb.UpdateValue(collectionname, com, data.to_dict(orient='list'))
    #             # mongodb.WriteValue(collectionname, com, data.to_dict(orient='list'))
    #             # print(data)
    #         except Exception as e:
    #             print('Company Ignore due to high service call' + '\nError : ' + str(e))

    def getNextDate(self, currrentDate):
        curDate = parser.parse(currrentDate).date()
        nextDay = curDate + timedelta(days=int(1))
        weekend = ['Saturday', 'Sunday']

        while calendar.day_name[nextDay.weekday()] in weekend:
            nextDay = nextDay + timedelta(days=int(1))
        return nextDay

    def new_dataset(dataset, step_size):
        data_X, data_Y = [], []
        for i in range(len(dataset) - step_size):
            a = dataset[i:(i + step_size), 0]
            data_X.append(a)
            data_Y.append(dataset[i + step_size, 0])
        return np.array(data_X), np.array(data_Y)

    def next_day_prediction(self):
        collectionname = 'IntraDay'
        for com in self.CompanyP:
            value = mongodb.ReadValue(collectionname, com)['Data']
            df = pd.DataFrame(eval(value))
            # print(df)
            next_date = DataFeed().getNextDate((df['date'].max()).split(' ')[0])
            df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close",
                               "5. volume": "volume"}, inplace=True)

            if 'volume' in df.columns:
                del df['volume']
            dataframe = df.reset_index(drop=True)
            dates = dataframe['date'].copy()
            del dataframe['date']
            seedValue = dataframe.tail(1)
            dataframe, scaler = stocksLSTM.ScaleDataSet(dataframe)
            dataframe = stocksLSTM.prepareDataSet(dataframe)
            model, details = stocksLSTM.trainModel(dataframe)
            seedValue, _ = stocksLSTM.ScaleDataSet(seedValue, scaler)
            p_df = stocksLSTM.predictfulDay(model, details, seedValue)
            p_df = stocksLSTM.deScaleData(p_df, scaler)
            rng = pd.date_range(str(next_date) + ' ' + '09:35:00', periods=100, freq='5min')
            ts = pd.Series(rng)
            p_df['date'] = ts
            p_df['date'] = p_df['date'].astype(str)
            # print(p_df)
            mongodb.UpdateValue('FuturePrediction', com, p_df.to_dict(orient='list'))

    def same_day_prediction(self):
        collectionname = 'IntraDay'
        for com in self.CompanyP:
            value = mongodb.ReadValue(collectionname, com)['Data']
            df = pd.DataFrame(eval(value))
            # print(df)
            next_date = DataFeed().getNextDate((df['date'].max()).split(' ')[0])
            df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close",
                               "5. volume": "volume"}, inplace=True)
            if 'volume' in df.columns:
                del df['volume']
            dataframe = df.reset_index(drop=True)
            dates = dataframe['date'].copy()
            del dataframe['date']

            testEnd = dataframe.iloc[312:].copy()
            trainStart = dataframe.drop(dataframe.index[312:])

            trainStart, scaler = stocksLSTM.ScaleDataSet(trainStart)
            testEnd, _ = stocksLSTM.ScaleDataSet(testEnd, scaler)

            # testEnd = testEnd.shift(-1)
            # testEnd = testEnd.dropna()
            # testEnd.reset_index(drop=True, inplace=True)
            trainStart = stocksLSTM.prepareDataSet(trainStart)
            model, details = stocksLSTM.trainModel(trainStart)

            presults = stocksLSTM.predict(model, testEnd)
            presults = stocksLSTM.deScaleData(presults, scaler)
            ndates = pd.DataFrame(dates[312:], columns=['date'])
            # ndates = ndates.shift(-1)
            # ndates = ndates.dropna()
            ndates.reset_index(drop=True, inplace=True)
            presults = pd.concat([presults, ndates], axis=1)

            date_filter = (presults['date'].max()).split(' ')[0]
            mongodb.UpdateValue('PredictionStore', com + ' ' + str(date_filter), presults.to_dict(orient='list'))

    # def newLSTM(self):
    #     collectionname = 'IntraDay'
    #     for com in self.CompanyP:
    #         # value = mongodb.ReadValue(collectionname, com)['Data']
    #         # df = pd.DataFrame(eval(value))
    #         # # print(df)
    #         # next_date = DataFeed().getNextDate((df['date'].max()).split(' ')[0])
    #         # df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close",
    #         #                    "5. volume": "volume"}, inplace=True)
    #         # if 'volume' in df.columns:
    #         #     del df['volume']
    #         # dataframe = df.reset_index(drop=True)
    #         # dates = dataframe['date'].copy()
    #         # del dataframe['date']
    #         #
    #         # OHLC_avg = df.mean(axis=1)
    #         # HLC_avg = df[['high', 'low', 'close']].mean(axis=1)
    #         # close_val = df[['close']]
    #         #
    #         # # PREPARATION OF TIME SERIES DATASE
    #         # OHLC_avg = np.reshape(OHLC_avg.values, (len(OHLC_avg), 1))  # 1664
    #         # scaler = MinMaxScaler(feature_range=(0, 1))
    #         # OHLC_avg = scaler.fit_transform(OHLC_avg)
    #         #
    #         # # TRAIN-TEST SPLIT
    #         # train_OHLC = int(len(OHLC_avg) * 0.75)
    #         # test_OHLC = len(OHLC_avg) - train_OHLC
    #         # train_OHLC, test_OHLC = OHLC_avg[0:train_OHLC, :], OHLC_avg[train_OHLC:len(OHLC_avg), :]
    #         #
    #         # # TIME-SERIES DATASET (FOR TIME T, VALUES FOR TIME T+1)
    #         # trainX, trainY = DataFeed.new_dataset(train_OHLC, 1)
    #         # testX, testY = DataFeed.new_dataset(test_OHLC, 1)
    #         #
    #         # # RESHAPING TRAIN AND TEST DATA
    #         # trainX = np.reshape(trainX, (trainX.shape[0], 1, trainX.shape[1]))
    #         # testX = np.reshape(testX, (testX.shape[0], 1, testX.shape[1]))
    #         # step_size = 1
    #         #
    #         # # LSTM MODEL
    #         # model = Sequential()
    #         # model.add(LSTM(256, input_shape=(1, step_size), return_sequences=True))
    #         # model.add(LSTM(128))
    #         # model.add(Dense(1))
    #         # model.add(Activation('linear'))
    #         #
    #         # # MODEL COMPILING AND TRAINING
    #         # model.compile(loss='mean_squared_error', optimizer='adam',
    #         #               metrics=['accuracy'])  # Try SGD, adam, adagrad and compare!!!
    #         # model.fit(trainX, trainY, epochs=10000, batch_size=1000, verbose=1)
    #         #
    #         # # SAVING THE TRAINED MODEL
    #         # model.save('%s_%s.model' % (ticker, interval))
    #         #
    #         # # LOADING NEWLY SAVED MODEL
    #         # new_model = keras.models.load_model('test_aapl.model')
    #         #
    #         #
    #         # # PREDICTION USING NEWLY SAVED MODEL
    #         # trainPredict = new_model.predict(trainX)
    #         # testPredict = new_model.predict(testX)
    #         #
    #         # val_loss, val_acc = new_model.evaluate(testX, testY)
    #         # print(val_loss, val_acc)
    #         #
    #         # # DE-NORMALIZING FOR PLOTTING
    #         # trainPredict = scaler.inverse_transform(trainPredict)
    #         # trainY = scaler.inverse_transform([trainY])
    #         # testPredict = scaler.inverse_transform(testPredict)
    #         # testY = scaler.inverse_transform([testY])
    #         #
    #         # # TRAINING RMSE
    #         # trainScore = math.sqrt(mean_squared_error(trainY[0], trainPredict[:, 0]))
    #         # print('Train RMSE: %.2f' % (trainScore))
    #         #
    #         # # TEST RMSE
    #         # testScore = math.sqrt(mean_squared_error(testY[0], testPredict[:, 0]))
    #         # print('Test RMSE: %.2f' % (testScore))
    #         #
    #         # # CREATING SIMILAR DATASET TO PLOT TRAINING PREDICTIONS
    #         # trainPredictPlot = np.empty_like(OHLC_avg)
    #         # trainPredictPlot[:, :] = np.nan
    #         # trainPredictPlot[step_size:len(trainPredict) + step_size, :] = trainPredict
    #         #
    #         # print("STARTING TO PRINT TRAINING DATA")
    #         # trainingDataPoints = trainPredictPlot
    #         # testDataset=pd.trainingDataPoints
    #         #
    #         # # CREATING SIMILAR DATASSET TO PLOT TEST PREDICTIONS
    #         # testPredictPlot = np.empty_like(OHLC_avg)
    #         # testPredictPlot[:, :] = np.nan
    #         # testPredictPlot[len(trainPredict) + (step_size * 2):len(OHLC_avg), :] = testPredict
    #         #
    #         # # model.save('aapl_prediction.model')
    #         #
    #         # testingDataPoints = testPredictPlot
    #         #
    #         #
    #         # # DE-NORMALIZING MAIN DATASET
    #         # OHLC_avg = scaler.inverse_transform(OHLC_avg)
    #         #
    #         # OriginalDataPoints = OHLC_avg
    #         #
    #         # FinalDataPoints = pd.DataFrame(data=OriginalDataPoints)
    #         # FinalDataPoints.insert(1, "Training Data", trainingDataPoints)
    #         # FinalDataPoints.rename(columns={0: 'Original Data'}, inplace=True)
    #         # FinalDataPoints.insert(2, "Testing Data", testingDataPoints)
    #         # print("*******************************************PANDAS DATA*******************************************")
    #         # print(FinalDataPoints)
    #         #
    #         # df.reset_index(drop=True)
    #         #
    #         #
    #         # # PREDICT FUTURE VALUES
    #         # last_val = testPredict[-1]
    #         # print(last_val)
    #         # last_val_scaled = last_val / last_val
    #         # print(last_val_scaled)
    #         # next_val = new_model.predict(np.reshape(last_val_scaled, (1, 1, 1)))
    #         # print(next_val)
    #         # print("Last Day Value:", np.asscalar(last_val))
    #         # print("Next Day Value:", np.asscalar(last_val * next_val))
    #         # # print np.append(last_val, next_val)
    #         #
    #         # # # PLOT OF MAIN OHLC VALUES, TRAIN PREDICTIONS AND TEST PREDICTIONS
    #         # # plt.plot(OHLC_avg, 'g', label='original dataset')
    #         # # plt.plot(trainPredictPlot, 'r', label='training set')
    #         # # plt.plot(testPredictPlot, 'b', label='predicted stock price/test set')
    #         # # plt.legend(loc='upper right')
    #         # # plt.xlabel('Time in Days')
    #         # # plt.ylabel('OHLC Value of Apple Stocks')
    #         # # plt.show()
    #         # #
    #         # #

def send_email():
    sender = Configuration().GetData()['EmailID']
    gmail_password = Configuration().GetData()['Password']
    COMMASPACE = ', '
    recipients = ['mfaizan@codexnow.com']

    # Create the enclosing (outer) message
    outer = MIMEMultipart()
    outer['Subject'] = 'DataFeed @ ' + str(datetime.datetime.now().date())
    outer['To'] = COMMASPACE.join(recipients)
    outer['From'] = sender
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'

    msg = MIMEText('Data Feeding Start in Mongodb' + str(datetime.datetime.now()))
    outer.attach(msg)
    composed = outer.as_string()

    # Send the email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(sender, gmail_password)
            s.sendmail(sender, recipients, composed)
            s.close()
            print("Email sent!")
    except:
        print("Unable to send the email. Error: ", sys.exc_info()[0])
        raise

def running_data_feed():
    # send_email()
    DataFeed().Feed_IntraDay("IntraDay1 min", "1min")
    print('----------------------------- IntraDay-1min Done --------------------------------')
    time.sleep(60)
    DataFeed().Feed_IntraDay("IntraDay5 mins", "5min")
    print('----------------------------- IntraDay-5min Done --------------------------------')
    time.sleep(60)
    DataFeed().Feed_IntraDay("IntraDay15 mins", "15min")
    print('----------------------------- IntraDay-15min Done --------------------------------')
    time.sleep(120)
    DataFeed().Feed_IntraDay("IntraDay30 mins", "30min")
    print('----------------------------- IntraDay-30min Done --------------------------------')
    time.sleep(60)
    DataFeed().Feed_IntraDay("IntraDay1 hour", "60min")
    print('----------------------------- IntraDay-60min Done --------------------------------')
    # time.sleep(60)
    # DataFeed().Feed_Daily()
    # print('------------------------------ Daily Done ----------------------------------')
    # time.sleep(60)
    # DataFeed().Feed_Weekly()
    # print('----------------------------- Weekly Done ----------------------------------')
    # time.sleep(60)
    # DataFeed().Feed_Monthly()
    # print('----------------------------- Monthly Done ----------------------------------')
    DataFeed().same_day_prediction()
    DataFeed().next_day_prediction()


def daily_feeding():
    print("Run-----")
    schedule.every().day.at("05:19").do(running_data_feed)
    time.sleep(5)
    schedule.every(5).minutes.do(running_data_feed)
    while True:
        schedule.run_pending()
        time.sleep(60)     # wait one minute

if __name__ == '__main__':
    daily_feeding()
    schedule.every(5).minutes.do(daily_feeding())
