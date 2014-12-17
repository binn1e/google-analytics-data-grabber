#!/usr/bin/python
# -*- coding: UTF-8 -*-

""" 
~ ga_api.py - v1.0
~ Grab data from Google Analytics API, present it into nice Excel or Tableau ready csv files.
~   
~ Created by Sabrina Matrullo on 2014-12-02
~ Last update: 2014-15-02
~ 
"""
import sys
import ga_api_auth 
from re import match
from csv import writer
from argparse import ArgumentParser
from apiclient.errors import HttpError
from datetime import datetime, timedelta
from oauth2client.client import AccessTokenRefreshError

# pattern used for dates when querying google analytics api
gaRawDatePattern = '[0-9]{4}[0-9]{2}[0-9]{2}'

def get_first_profile_id(service):
  accounts = service.management().accounts().list().execute()
  if accounts.get('items'):
    firstAccountId = accounts.get('items')[1].get('id')
    webproperties = service.management().webproperties().list(accountId=firstAccountId).execute()
    if webproperties.get('items'):
      firstWebpropertyId = webproperties.get('items')[0].get('id')
      profiles = service.management().profiles().list(
          accountId=firstAccountId,
          webPropertyId=firstWebpropertyId).execute()
      if profiles.get('items'):
        return profiles.get('items')[0].get('id')
  return None

# use the analytics service object to query the core reporting api
def get_results(service, profile_id, start_date, end_date, metrics, dimensions, maxresults):
  dims = ",".join(dimensions)
  mets = ",".join(metrics)
  return service.data().ga().get(
      ids=profile_id,
      start_date=start_date,
      end_date=end_date,
      metrics=mets,
      dimensions=dims, 
      max_results=maxresults).execute()

# nicely csvfy data  
def print_results(results, title):
  with open(title + '.csv', 'wt') as csv_file:
    dataWriter = writer(csv_file, delimiter = ',')
    dataWriter.writerow([title.replace('_', ' ', ).capitalize()])
    output = []
    for row in results.get('rows'):   
      for item in row:
        # making a date excel/whatever ready
        dateMatch = match(gaRawDatePattern, item) 
        if dateMatch != None:
          index = row.index(item)
          date = str(item[0:4]) + '-' + str(item[4:6]) + '-' + str(item[6:8])
          row.pop(index)
          row.insert(index, date)
        else: # not a date
        # if not a number, we need to encode it to utf-8
          numMatch = match("^[0-9]*$", item) 
          if numMatch == None: 
            index = row.index(item)
            row.pop(index)
            row.insert(index, item.encode('utf_8', errors="replace"))
      dataWriter.writerow(row) 

if __name__ == '__main__':

  parser = ArgumentParser(prog = "ga_api", description = "Grab some Google Analytics data.")
  parser.add_argument('-s', type = str, nargs='+', metavar = 'pattern', 
          help = "Include data from given date [Format: [0-9]{4}-[0-9]{2}-[0-9]{2}|today|yesterday|[0-9]+(daysAgo)]") 
  parser.add_argument('-e', type = str, nargs='+', metavar = 'pattern', 
          help = "Include data until given date [Format: [0-9]{4}-[0-9]{2}-[0-9]{2}|today|yesterday|[0-9]+(daysAgo)]") 
  parser.add_argument('-m', type = str, nargs='+', metavar = 'pattern', 
          help = "Desired Google Analytics metrics [Format: ga:metric [ga:metric ...] — please see reference at https://developers.google.com/analytics/devguides/reporting/core/dimsmets") 
  parser.add_argument('-d', type = str, nargs='+', metavar = 'pattern', 
          help = "Desired Google Analytics dimensions [Format: ga:dimension [ga:dimension ...] — please see reference at https://developers.google.com/analytics/devguides/reporting/core/dimsmets") 
  parser.add_argument('-r', type = str, nargs='+', metavar = 'pattern', 
          help = "Max number of rows returned [Format: ^[0-9]*") 
  args = parser.parse_args()

  # service, profile
  service = ga_api_auth.initialize_service()
  profile_id = 'ga:' + str(get_first_profile_id(service))

  # dates 
  now = datetime.now()
  one_year = timedelta(days=365)
  one_day = timedelta(days=1)

  if args.s != None: start_date = args.s[0] 
  else: 
    start_date = now - one_year
    start_date = start_date.strftime('%Y-%m-%d')
  if args.e != None: end_date = args.e[0] 
  else: 
    end_date = now - one_day
    end_date = end_date.strftime('%Y-%m-%d')

  # mets, dims, file title
  dimensions = []
  metrics = []
  title = ""

  if args.m != None: 
    for arg in args.m:
      metrics.append(arg)
    met_title = ",".join(args.m) 
  else: 
    metrics = ['ga:sessions']
    met_title = "sessions"
  if args.d != None:
    for arg in args.d:
      dimensions.append(arg)
    dim_title = ",".join(args.d) 
  else: 
    dimensions = ['ga:channelGrouping']
    dim_title = "channelGrouping"
  title = met_title + " by " + dim_title
  title = title.replace('ga:', '')   
  if title == "": title = 'sessions by channelGrouping' 

  # number of rows returned
  if args.r != None: maxresults = args.r[0]
  else: maxresults = 1000

  if profile_id:
    data = get_results(service, profile_id, start_date, end_date, metrics, dimensions, maxresults)
    print_results(data, title)
