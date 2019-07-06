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

webserver_password = get_password()

SEND_HASH_URL = "https://labitat.dk/member/money/doorputer_new_hash?{}"
GET_DATA_URL  = "https://labitat.dk/member/money/doorputer_get_dates?{}"

# number of seconds to wait between fetching
# a new version of the user database
web_update_interval = 60

connection = sqlite.connect('/home/doorman/users.db')
cursor = connection.cursor()

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

s = serial.Serial(
	port	 = '/dev/ttyUSB0',
	baudrate = 9600,
	bytesize = 8,
	parity   = 'E',
	stopbits = 2
)
threading.Thread(target=ui, args=(s,)).start()

def update_from_webserver():
	con = sqlite.connect('/home/doorman/users.db')
	cur = con.cursor()

	try:
		params = urllib.parse.urlencode({'key': webserver_password})
		members = None
		with urllib.request.urlopen(GET_DATA_URL.format(params)) as d:
			data = d.read().decode('utf-8')
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
		sys.stderr.write("\n{}\n".format(datetime.now()))
		traceback.print_exc(file=sys.stderr)
		return False

def periodic_updater():
	while True:
		try:
			update_from_webserver()
			time.sleep(web_update_interval)
		except:
			sys.stderr.write("\n{}\n".format(datetime.now()))
			traceback.print_exc(file=sys.stderr)

threading.Thread(target=periodic_updater).start()

def send_to_webserver(hash):
	try:
		params = urllib.parse.urlencode({
			'key':  webserver_password,
			'hash': hash
		})
		# 202 means that the same unknown hash was
		# received twice before a timeout which allows
		# a website-user to claim the hash as their own
		print("sending to webserver")
		with urllib.request.urlopen(SEND_HASH_URL.format(params)) as d:
			if d.getcode() == 202:
				return True
			else:
				return False
	except:
		sys.stderr.write("\n{}\n".format(datetime.now()))
		traceback.print_exc(file=sys.stderr)
		return False

while True:
	try:
		data = s.readline()
		data = data[:-1]

		if data[:5] != b"ALIVE":
			print("DEBUG: {}".format(data))

		if data[:5] == b"HASH+":
			h = data[5:45].decode('utf-8')
			cursor.execute(
				"SELECT 1 "
				"FROM hashes "
				"WHERE hash = ? AND expires >= ?", [
					h,
					datetime.now().strftime('%Y-%m-%d')
				]
			)
			if cursor.fetchone() != None:
				s.write(b"O")
				print("Opening")
			else:
				if send_to_webserver(h):
					s.write(b"V")
					print("Validated")
				else:
					s.write(b"R")
					print("Rejected")
	except:
		# print exception
		sys.stderr.write("\n{}\n".format(datetime.now()))
		traceback.print_exc(file=sys.stderr)
		# Sometimes we loose the serial connection here.
		# Rather than try to coordinate serial port reopen across
		# all the threads, just exit, and let parent init script
		# restart us.
		sys.exit()

# vim: set ts=4 sw=4 noet:
