from Config import Configuration
import mongodb
import pandas as pd
from dateutil import parser
from datetime import timedelta
import numpy as np
import pyti
import CodexFunctions, sys


# cf = functions()
class display_data:
    def __init__(self):
        self.name = "Stock_Data"

    def display_IntraDay_Data(self, company_name, interval_time):
        try:
            collection = ''
            if interval_time == '1sec':
                collection = 'IntraDay1 secs'
            elif interval_time == '1min':
                collection = 'IntraDay1 min'
            elif interval_time == '5min':
                collection = 'IntraDay5 mins'
            elif interval_time == '15min':
                collection = 'IntraDay15 mins'
            elif interval_time == '30min':
                collection = 'IntraDay30 mins'
            elif interval_time == '1hr':
                collection = 'IntraDay1 hour'
            elif interval_time == '4hr':
                collection = 'IntraDay4 hours'


            client = mongodb.MongoClient(mongodb.MongoIP, mongodb.MonngoPort)
            db = client[str(mongodb.MongoStore)]

            coll_names = db.list_collection_names()

            value = mongodb.ReadValue(collection, company_name)['Data']
            collectionP = collection + "Predict"

            if coll_names.__contains__(collectionP):
                valueP = mongodb.ReadValue(collectionP, company_name)['Data']
            df = pd.DataFrame(eval(value))
            dfP = pd.DataFrame(eval(valueP))
            # date_filter = (df['date'].max()).split(' ')[0]
            # dt = parser.parse(date_filter).date()
            df.rename(columns={0: "date", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume"},
                        inplace=True)
            # df.rename(columns={0: "open", 1: "high", 2: "low", 3: "close",
            #                    4: "volume",5:""},inplace=True)
            # df['date'] = pd.to_datetime(df['date'])
            # df['_date'] = [d.date() for d in df['date']]
            # df['_time'] = [t.time() for t in df['date']]
            # df['date'] = df['date'].astype(str)
            # df['_date'] = df['_date'].astype(str)
            # df['_time'] = df['_time'].astype(str)
            # p_df = self.temp(company_name, date_filter)
            # final_df = pd.merge(df, p_df, how='left', left_on='date', right_on='date')
            # final_df = display_data().functionCalling(final_df)
            # final_df = final_df.fillna('')
            df = pd.concat([dfP,df], axis=1)
            return df.to_dict(orient='list')
            # return temp_list
        except Exception as e:
            print(sys.exc_info())
            return str(e)

    def temp(self, company_name, filter_date):
        try:
            collectionname = 'PredictionStore'
            value = mongodb.ReadValue(collectionname, company_name + ' ' + str(filter_date))['Data']
            df = pd.DataFrame(eval(value))
        except:
            df = pd.DataFrame([], columns=['date', 'highP', 'lowP', 'openP', 'closeP'])
        return df

    def display_Daily_Data(self, company_name):
        try:
            collection = 'Daily'
            value = mongodb.ReadValue(collection, company_name)['Data']
            df = pd.DataFrame(eval(value))
            df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close","5. volume": "volume"}, inplace=True)
            df = display_data().functionCalling(df)
            return df.dropna().to_dict(orient='list')
        except Exception as e:
            print(str(e))
            return str(e)

    def display_tsv(self, company_name):
        try:
            collection = 'tsv'
            value = mongodb.ReadValue(collection, company_name)['Data']
            df = pd.DataFrame(eval(value))
            df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close","5. volume": "volume"}, inplace=True)
            df = display_data().functionCalling(df)
            return df.dropna().to_dict(orient='list')
        except Exception as e:
            print(str(e))
            return str(e)

    def display_Weekly_Data(self, company_name):
        try:
            collection = 'Weekly'
            value = mongodb.ReadValue(collection, company_name)['Data']
            df = pd.DataFrame(eval(value))
            df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close","5. volume":"volume"}, inplace=True)
            df = display_data().functionCalling(df)
            return df.dropna().to_dict(orient='list')
        except Exception as e:
            print(str(e))
            return str(e)

    def display_Monthly_Data(self, company_name):
        try:
            collection = 'Monthly'
            value = mongodb.ReadValue(collection, company_name)['Data']
            df = pd.DataFrame(eval(value))
            df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close","5. volume":"volume"}, inplace=True)
            df = display_data().functionCalling(df)
            return df.dropna().to_dict(orient='list')
        except Exception as e:
            print(str(e))
            return str(e)

    def functionCalling(self,df):
        final_df = CodexFunctions.movingAvg(df,)
        # final_df = CodexFunctions.rolling_values(final_df,"close")
        # final_df = CodexFunctions.rolling_Std(final_df)
        # final_df = CodexFunctions.cummulative_Avg(final_df,"close")
        # final_df = CodexFunctions.cummulative_Sum(final_df,"close")
        # final_df = CodexFunctions.cummulative_Product(final_df,"close")
        # final_df = CodexFunctions.variance(final_df,"close")
        # final_df = CodexFunctions.addUpperLower_UpDown(final_df)
        # final_df = CodexFunctions.addUpperLower_signal(final_df)

        final_df = CodexFunctions.returns(final_df,"close")
        final_df["Momentum"] = CodexFunctions.newmomentum(final_df['close'], period=5)
        # final_df["Momentum"] = CodexFunctions.momentum(final_df['close'], period=5)
        final_df["Thrust"] = CodexFunctions.thrust(final_df['Momentum'], period=5)
        final_df["HeavyMomentum"] = CodexFunctions.heavymomentum(final_df, period=5)
        final_df["HeavyThrust"] = CodexFunctions.heavyThrust(final_df["HeavyMomentum"], period=5)
        return final_df.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="all")




