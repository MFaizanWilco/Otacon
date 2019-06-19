import numpy as np
import pandas as pd
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.optimizers import RMSprop
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import math, random

vars = ["open", "high", "low", "close"]

def ScaleDataSet(dataset, scaler = None):
    dataset = dataset.astype('float32')
    if scaler == None:
        scaler = MinMaxScaler(feature_range=(0, 1))
        dataset_tran = scaler.fit_transform(dataset.values)
    else :
        dataset_tran = scaler.transform(dataset.values)
    dataset = pd.DataFrame(dataset_tran, index=dataset.index, columns=dataset.columns)
    return dataset, scaler

def deScaleData(dataset, scaler):
    dataset_tran = scaler.inverse_transform(dataset.values)
    dataset = pd.DataFrame(dataset_tran, index=dataset.index, columns=dataset.columns)
    return dataset

def prepareDataSet(dataframe):
    dataframe['open_y'] = dataframe['open'].shift(-1)
    dataframe['high_y'] = dataframe['high'].shift(-1)
    dataframe['low_y'] = dataframe['low'].shift(-1)
    dataframe['close_y'] = dataframe['close'].shift(-1)
    # dataframe['open_y'] = dataframe['open'].shift(-1)
    dataframe = dataframe.dropna()

    return dataframe

def trainTestSplit(dataset, split = 0.72):
    train_size = int(dataset.shape[0] * split)
    test_size = dataset.shape[0] - train_size
    train, test = dataset.loc[0:train_size], dataset.loc[train_size:dataset.shape[0]]
    return train, test

def splitXY(dataSet, colname):
    global vars

    X, Y = [],[]
    # temp = np.reshape(dataSet[vars].values, (dataSet[colname].shape[0], 1))
    temp = dataSet[vars].values
    # print()
    # print(temp)
    # exit()
    temp_y = np.reshape(dataSet[colname+'_y'].values, (dataSet[colname+'_y'].shape[0], 1))
    for i in range(temp.shape[0]):
        X.append(temp[i, :])
        Y.append([temp_y[i, 0]])
    # print(np.array(X))
    # exit()
    return np.array(X), np.array(Y)


def trainModel(trainSet):
    global vars
    trainedModel = { }
    modeldetails = { }
    model = Sequential()
    model.add(LSTM(16, input_shape=(4, 1)))
    model.add(Dense(1))
    optimizer = RMSprop(lr=0.001, rho=0.900, epsilon=1e-08, decay=0.0)
    model.compile(loss='mean_squared_error', optimizer=optimizer)
    for comp in vars:
        Xtrain, Ytrain = splitXY(trainSet, comp)
        Xtrain = np.reshape(Xtrain, (Xtrain.shape[0], Xtrain.shape[1], 1))
        model.fit(Xtrain, Ytrain, epochs=10, batch_size=1, verbose=0)
        trainedModel[comp] = model
        modeldetails[comp] = getscore(Ytrain, model.predict(Xtrain))
        model.summary()

    return trainedModel, modeldetails

def predict(model, dataset):
    global var
    predictedResults = pd.DataFrame()
    for comp in vars:
        pComp = None
        # temp = np.reshape(dataset[comp].values, (dataset[comp].shape[0], 1))
        temp = dataset[vars].values
        x = []
        for i in range(temp.shape[0]):
            x.append(temp[i, :])
        X = np.array(x)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        pComp = model[comp].predict(X)
        # predictedResults[comp+'P'] = list(pComp[:, 0])
        predictedResults = pd.concat([predictedResults, pd.DataFrame(pComp, columns=[comp+'P'])], axis=1)
    return predictedResults;

def getscore(trainY, predictY):
    Score = math.sqrt(mean_squared_error(trainY, predictY))
    result = str('error: %.2f RMSE' % (Score))
    return result, Score

def getscoreDec(trainY, predictY):
    Score = math.sqrt(mean_squared_error(trainY, predictY))
    return Score


def predictfulDay(model, details, seedvalue, nopredictions = 78):
    mySeed = seedvalue.copy()
    resultSet = pd.DataFrame()
    for i in range(nopredictions):
        result = predict(model, mySeed)
        result = getnoise(result , details)
        resultSet = pd.concat([resultSet, result], axis=0, ignore_index=True)
        mySeed = pd.DataFrame (result.values, columns=mySeed.columns)
    return resultSet

def _noise(error):
    noise = 0
    allu = math.sqrt(error**2)
    noise = random.uniform(-allu, allu)
    return noise

def getnoise(predictions, details):
    global vars
    for var in vars:
        predictions[var+'P'] = predictions[var+'P'] + _noise(details[var][1]) * 2.5
    return predictions


# value = mongodb.ReadValue('IntraDay', 'aapl')['Data']
# df = pd.DataFrame(eval(value),)
# # print(df)
#
# df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close",
#                    "5. volume": "volume"}, inplace=True)
#
# if 'volume' in df.columns:
#     del df['volume']
#
# dataframe = df.reset_index(drop=True)
#
# dates = dataframe['date'].copy()
# del dataframe['date']
#
# seedValue = dataframe.tail(1)
#
# dataframe, scaler = ScaleDataSet(dataframe)
#
# dataframe = prepareDataSet(dataframe)
#
# train, test = trainTestSplit(dataframe)
# model, details = trainModel(train)
#
# presults = predict(model, test)
# presults = deScaleData(presults, scaler)
#
# print(presults)
#
# print('nothing')
#
# seedValue, _ = ScaleDataSet(seedValue, scaler)
# dayPrediction = predictfulDay(model, seedValue)
# dayPrediction = deScaleData(dayPrediction, scaler)
# print(dayPrediction)

# -------------------- DayActPrediction --------------------

#
# testEnd = dataframe.iloc[312:].copy() # sep. last day for testing
# trainStart = dataframe.drop(dataframe.index[312:])
#
# trainStart, scaler = ScaleDataSet(trainStart)
# testEnd, _ = ScaleDataSet(testEnd, scaler)
#
# trainStart = prepareDataSet(trainStart)
#
# model, details = trainModel(trainStart)
#
# presults = predict(model, testEnd)
# presults = deScaleData(presults, scaler)
# ndates = pd.DataFrame(dates[312:], columns=['date'])
# ndates.reset_index(drop=True, inplace=True)
# presults = pd.concat([presults, ndates], axis=1)
#
# print(presults['openP'])
# import matplotlib.pyplot as plt
# plt.plot(presults['openP'])
# plt.ylabel('some numbers')
# plt.show()
