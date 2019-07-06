#!/bin/sh

# this script is started by /etc/cron.d/lockserver created by:
# # echo @reboot root /home/doorman/lockserver/start.sh > /etc/cron.d/lockserver

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

LOGFILE=/var/log/lockserver.log
DEBUGFILE=/var/log/lockserver.debug.log

start_lockd(){
	cd /home/doorman/lockserver
	export PYTHONUNBUFFERED=1
	while true ; do
		./lockd.py >> "$LOGFILE" 2>> "$DEBUGFILE"
		echo restarting in 5 sec
		sleep 5
	done
}

start_tmux(){
	/usr/bin/tmux new-session -s lockserver -d "$0 inside-tmux"
}

init(){
	# init button
	echo 2 > /sys/class/gpio/export
	echo 1 > /sys/class/gpio/gpio2/active_low

	touch "$LOGFILE" "$DEBUGFILE"
	chown doorman:doorman "$LOGFILE" "$DEBUGFILE"

	# re-start script as doorman
	su -c '/home/doorman/lockserver/start.sh start-tmux' doorman
}

main(){
	case "$1" in
		inside-tmux)
			start_lockd
			;;
		start-tmux)
			start_tmux
			;;
		*)
			init
			;;
	esac
}

main "$@"
