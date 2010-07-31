#!/usr/bin/env python2.6
from pysqlite2 import dbapi2 as sqlite
import serial, thread
from datetime import datetime
import time
import urllib
#import json


def go():

	params = urllib.urlencode({'key': 'cykelmug'})
	d = urllib.urlopen("https://labitat.dk/member/money/doorputer_get_dates", params)
	print d.getcode()
#	data = d.read()

#	print data


go()
