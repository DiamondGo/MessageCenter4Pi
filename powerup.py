#!/bin/env python
from time import sleep
from RPi import GPIO

power_pin = 26

GPIO.setmode(GPIO.BCM)
GPIO.setup(power_pin, GPIO.OUT, initial=0)

GPIO.output(power_pin, 1)
sleep(1.5)
GPIO.output(power_pin, 0)
