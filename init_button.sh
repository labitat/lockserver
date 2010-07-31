#!/bin/sh

modprobe rdc321x_gpio
echo 15 > /sys/class/gpio/export

