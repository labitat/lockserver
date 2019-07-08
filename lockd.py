#!/usr/bin/python3 -u

import sqlite3 as sqlite
import serial
import threading
from datetime import datetime
import sys, traceback
import time
import urllib.request
import urllib.parse
import json

def get_password():
	with open('/home/doorman/lockserver.password', 'r') as f:
		return f.readline().strip()

WEBSERVER_PASSWORD = get_password()

SEND_HASH_URL = "https://labitat.dk/member/money/doorputer_new_hash?{}"
GET_DATA_URL  = "https://labitat.dk/member/money/doorputer_get_dates?{}"

# number of seconds to wait between fetching
# a new version of the user database
WEB_UPDATE_INTERVAL = 60

def ui(ser):
	cur_mode = b"D"
	last_state = "1\n"
	while True:
		button = open('/sys/class/gpio/gpio2/value', 'r')
		btn_state = button.read()
		if btn_state == "0\n" and last_state == "1\n":
			if cur_mode == b"D":
				print("Switching to night mode")
				cur_mode = b"N"
			else:
				print("Switching to day mode")
				cur_mode = b"D"
			ser.write(cur_mode)
		last_state = btn_state
		button.close()
		time.sleep(0.05)

ser = serial.Serial(
	port     = '/dev/ttyUSB0',
	baudrate = 9600,
	bytesize = 8,
	parity   = 'E',
	stopbits = 2
)
threading.Thread(target=ui, args=(ser,), daemon=True).start()

def update_from_webserver():
	con = sqlite.connect('/home/doorman/users.db')
	cur = con.cursor()
	params = urllib.parse.urlencode({'key': WEBSERVER_PASSWORD})

	try:
		members = None
		with urllib.request.urlopen(GET_DATA_URL.format(params)) as d:
			members = json.loads(d.read().decode('utf-8'))

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
					print("Updated existing row")
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
					print("Error inserting new row")
					return False
				else:
					print("Inserted new row")

		con.commit()
		return True
	except:
		traceback.print_exc(file=sys.stderr)
		return False

def periodic_updater():
	while True:
		update_from_webserver()
		time.sleep(WEB_UPDATE_INTERVAL)

threading.Thread(target=periodic_updater, daemon=True).start()

def send_to_webserver(hash):
	params = urllib.parse.urlencode({
		'key':  WEBSERVER_PASSWORD,
		'hash': hash
	})
	try:
		with urllib.request.urlopen(SEND_HASH_URL.format(params)) as d:
			# 202 means that the same unknown hash was
			# received twice before a timeout which allows
			# a website-user to claim the hash as their own
			return d.getcode() == 202
	except:
		traceback.print_exc(file=sys.stderr)
		return False

con = sqlite.connect('/home/doorman/users.db')
cur = con.cursor()

while True:
	data = ser.readline()
	data = data[:-1]

	if data[:5] != b"ALIVE":
		print("DEBUG: {}".format(data))

	if data[:5] == b"HASH+":
		h = data[5:45].decode('utf-8')
		cur.execute(
			"SELECT 1 "
			"FROM hashes "
			"WHERE hash = ? AND expires >= ?", [
				h,
				datetime.now().strftime('%Y-%m-%d')
			]
		)
		if cur.fetchone() != None:
			ser.write(b"O")
			print("Opening")
		else:
			print("Sending hash to webserver")
			if send_to_webserver(h):
				ser.write(b"V")
				print("Validated")
			else:
				ser.write(b"R")
				print("Rejected")

# vim: set ts=4 sw=4 noet:
