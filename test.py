#!/usr/bin/env python2.6
import thread
import time

def ui():
	cur_mode = "D"
	last_state = "1\n"
	while(True):
		button = open('/sys/class/gpio/gpio15/value', 'r')
	        btn_state = button.readline()
		
        	if btn_state == "0\n" and last_state == "1\n":
			if cur_mode == "D":
				print "Switching to night mode"
				cur_mode = "N"
			else:
				print "Switching to day mode"
				cur_mode = "D"
		last_state = btn_state
		button.close()
		time.sleep(0.05)
	

ui()
