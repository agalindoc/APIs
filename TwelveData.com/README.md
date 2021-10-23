## This python code connects to TwelveData API and get the information in two ways:

1. Using the TDClient
2. Using the http_client because some functions are only available through the http client

From a csv file reads the symbols to get the market data/indicators.

It has a control for the limit of number of calls alowable by TwelveData.

Writes the results into a file.
