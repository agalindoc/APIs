# coding: utf-8
from requests import Response
import requests
from twelvedata import TDClient
from twelvedata.http_client import DefaultHttpClient
from twelvedata.exceptions import (
    BadRequestError,
    InternalServerError,
    InvalidApiKeyError,
    TwelveDataError,
)
import pandas as pd
import configparser
import time
import math

_cache = {}


API_URL = 'https://api.twelvedata.com'


class CachedHttpClient(DefaultHttpClient, object):
    def get(self, *args, **kwargs):
        global _cache

        h = "{}{}".format(args, kwargs)

        if h in _cache:
            return _cache[h]
        else:
            resp = super(CachedHttpClient, self).get(*args, **kwargs)
            _cache[h] = resp
            return resp


def _init_client(api_key):
    return TDClient(
        api_key,
        http_client=CachedHttpClient(API_URL),
    )

def _get_ts(stock, timeframe, emaperiod, ma1period, ma2period):
    td = _init_client(api_key)   
    return td.time_series(symbol=stock, interval=timeframe, outputsize=2).with_ema(time_period=emaperiod).with_vwap().with_ma(time_period=ma1period, ma_type="SMA", series_type="close").with_ma(time_period=ma2period, ma_type="SMA", series_type="close").as_json()   

def _get_quotes(stock, api_key):
    try:
        response = requests.get("https://api.twelvedata.com/quote?symbol="+stock+"&apikey="+api_key)
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        tmp=False
    return response

def controlWaitTime():
    endTime = time.time()
    waitTime = math.trunc(61-(endTime-startTime))
    if (waitTime > 0):
        #print("API calls limit control, sleep for " + str(waitTime) + " seconds.")
        time.sleep(waitTime)
    starttime = time.time()
    symbolRequests = 0 

# read config file and get parameters
parser = configparser.ConfigParser()
parser.read("config.txt")
api_key     = parser.get("Config", "api_key")
period      = parser.get("Config", "period")
fastmaP     = parser.get("Config", "fastma_period")
slowmaP     = parser.get("Config", "slowma_period")
emaP        = parser.get("Config", "ema_period")
sleepTime   = parser.get("Config", "sleep_time")
write_file  = parser.get("Config", "write_file")
show_all    = parser.get("Config", "show_all")
requests_per_minute = parser.get("Config", "show_all")

# read symbols file
datafile = pd.read_csv("symbols.txt", header=None)
symbolsList = datafile.astype(str).values.flatten().tolist()
#for stock in datafile.iterrows():
#    print(stock)
header = "\nDate\t\t\tsymbol\tclose\t\tvwap\t\tma1\t\tma2\t\tema\t\tstatus\ttrend\t52 week high/low"
csvHeader = "\nDate,symbol,close,vwap,ma1,ma2,ema,tstatus,trend,52 week high,52 week low"
print(header)
if write_file == '1':
    fo = open('twelvedata.csv', 'a')
    fo.write(csvHeader)

symbolRequests = 0
startTime = time.time()
while True:
    for i in range(len(symbolsList)):                      
        symbol = symbolsList[i]
        dataOk = True

        # get the 52 week high/low 
        try:
            quotesResponse = _get_quotes(symbol, api_key)            
            quotes = quotesResponse.json()
            fifty_two_weekH = quotes['fifty_two_week']['high']
            fifty_two_weekL = quotes['fifty_two_week']['low']
            symbolRequests += 1            
        except Exception as e:
            print("Opps! ", format(e), "occurred.")            
            fifty_two_weekH = '-'
            fifty_two_weekL = '-'
            error_string = str(e)
            if error_string.find("You have reached the API calls limit") > -1:
                controlWaitTime()

        try:
            data = _get_ts(symbol, period, fastmaP, slowmaP, emaP)            
            #print(data[0])
            #print(data[1])
            vwap     = data[0]['vwap']
            ma1      = data[0]['ma_1']
            ma2      = data[0]['ma_2']
            ema      = data[0]['ema']
            close    = data[0]['close']
            ma1b4    = data[1]['ma_1']
            ma2b4    = data[1]['ma_2']
            closeb4  = data[1]['close']
            datetime =data[0]['datetime']  
            symbolRequests += 1         
            dataOk = True                      

        except Exception as e:
            print("Opps! ", format(e), "occurred.")               
            vwap    = '-'
            ma1     = '-'
            ma2     = '-'
            ema     = '-'
            close   = '-'
            ma1b4   = '-'
            ma2b4   = '-'
            closeb4 = '-'
            datetime= '-'
            dataOk = False
            error_string = str(e)
            if error_string.find("You have reached the API calls limit") > -1:
                controlWaitTime()
            

        if ma1 > ma2: status = "Bullish" 
        elif ma1 < ma2: status = "Bearish" 
        else: status = "nothing"

        if ma1>ma2 and ma1b4<=ma2b4: trend = "Bullish cross"
        elif ma1<ma2 and ma1b4>=ma2b4: trend = "Bearish cross"
        else: trend = "nothing"

        line = datetime
        line += "\t" + symbol + "\t" + close 
        line += "\t" + vwap + "\t" + ma1 
        line += "\t" + ma2 + "\t" + ema 
        line += "\t" + status + "\t" + trend
        line += "\t" + fifty_two_weekH + "/" +fifty_two_weekL
        
        csvLine = "\n" + datetime
        csvLine += "," + symbol + "," + close 
        csvLine += "," + vwap + "," + ma1 
        csvLine += "," + ma2 + "," + ema 
        csvLine += "," + status + "," + trend
        csvLine += "," + fifty_two_weekH + "," +fifty_two_weekL


        if show_all=='1':
            if dataOk == True:                        
                print(line)
                if write_file == '1': fo.write(csvLine)                            
        else:
            if trend != "nothing":
                if dataOk == True:
                    print(line)
                    if write_file == '1': fo.write(csvLine)                
            else: print('.', end='', flush=True)        
            
        # request per minute control
        if symbolRequests >= int(requests_per_minute):
            controlWaitTime()       

    time.sleep(int(sleepTime))

if write_file == '1': fo.close()
