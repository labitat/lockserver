#!/bin/sh

set -e

[ -h /sys/class/gpio/gpio2 ] || printf '2' > /sys/class/gpio/export
printf 'in' > /sys/class/gpio/gpio2/direction
printf  '1' > /sys/class/gpio/gpio2/active_low
