#!/usr/bin/env python2.6

from pysqlite2 import dbapi2 as sqlite
import serial, thread
from datetime import datetime
import sys, traceback
import time
import urllib

try:
	import json
except ImportError: 
	import simplejson as json

webserver_password = 'xxx'
send_hash_url = "https://labitat.dk/member/money/doorputer_new_hash"
get_data_url = "https://labitat.dk/member/money/doorputer_get_dates"

# number of seconds to wait between fetching
# a new version of the user database
web_update_interval = 60

connection = sqlite.connect('/home/doorman/users.db')
cursor = connection.cursor()

def ui(ser):
	cur_mode = "D"
	last_state = "1\n"
	while True:
		button = open('/sys/class/gpio/gpio15/value', 'r')
		btn_state = button.read()
		if btn_state == "0\n" and last_state == "1\n":
			if cur_mode == "D":
				print "Switching to night mode"
				cur_mode = "N"
			else:
				print "Switching to day mode"
				cur_mode = "D"
			ser.write(cur_mode)
		last_state = btn_state
		button.close()
		time.sleep(0.05)

def get_serial():
	return serial.Serial(
		port     = '/dev/ttyS0',
		baudrate = 9600,
		bytesize = 8,
		parity   = 'E',
		stopbits = 2)

s = get_serial()

thread.start_new_thread(ui, (s,))

def update_from_webserver():
	con = sqlite.connect('/home/doorman/users.db')
	cur = con.cursor()

	try:
		params = urllib.urlencode({'key': webserver_password})
		d = urllib.urlopen(get_data_url, params)
		data = d.read()

		members = json.loads(data)

		for member in members:
			cur.execute(
				"SELECT hash, expires FROM hashes "
				"WHERE member = ?", [
					member['login']
				]
			)
			row = cur.fetchone()
			if row:
				if row[0] != member['hash'] or row[1] != member['expiry_date']:
					cur.execute(
						"UPDATE hashes "
						"SET hash = ?, expires = ? "
						"WHERE member = ?", [
							member['hash'],
							member['expiry_date'],
							member['login']
						]
					)
					print "Updated existing row"
			else:
				cur.execute(
					"INSERT INTO hashes (member, hash, expires) "
					"VALUES (?, ?, ?)",	[
						member['login'],
						member['hash'],
						member['expiry_date']
					]
				)
				if cur.rowcount == 0:
					print "Error inserting new row"
					return False
				else:
					print "Inserted new row"

		con.commit()
		return True
	except:
		sys.stderr.write("\n"+str(datetime.now())+"\n")
		traceback.print_exc(file=sys.stderr)
		return False

def periodic_updater():
	while True:
		try:
			update_from_webserver()
			time.sleep(web_update_interval)
		except:
			sys.stderr.write("\n"+str(datetime.now())+"\n")
			traceback.print_exc(file=sys.stderr)

thread.start_new_thread(periodic_updater, ())

def send_to_webserver(hash):
	try:
		params = urllib.urlencode({
				'key':  webserver_password,
				'hash': hash
		})
		d = urllib.urlopen(send_hash_url, params)
		# 202 means that the same unknown hash was
		# received twice before a timeout which allows
		# a website-user to claim the hash as their own
		print "sending to webserver"
		if d.getcode() == 202:
			return True
		else:
			return False
	except:
		sys.stderr.write("\n"+str(datetime.now())+"\n")
		traceback.print_exc(file=sys.stderr)
		return False

while True:
	try:
		data = s.readline()
		data = data[:-1]

		if data[:5] != "ALIVE":
			print str(datetime.now()) + " DEBUG: " + data

		if data[:5] == "HASH+":
			h = data[5:45]
			cursor.execute(
				"SELECT 1 "
				"FROM hashes "
				"WHERE hash = ? AND expires > ?", [
					h,
					datetime.now().strftime('%Y-%m-%d')
				]
			)
			if cursor.fetchone() != None:
				s.write("O")
				print "Opening"
			else:
				if send_to_webserver(h):
					s.write("V")
					print "Validated"
				else:
					s.write("R")
					print "Rejected"
	except:
		# print exception
		sys.stderr.write("\n"+str(datetime.now())+"\n")
		traceback.print_exc(file=sys.stderr)
		# Sometimes we loose the serial connection here.
		# Rather than try to coordinate serial port reopen across
		# all the threads, just exit, and let parent init script
		# restart us.
		sys.exit()

# vim: set ts=4 sw=4 :
