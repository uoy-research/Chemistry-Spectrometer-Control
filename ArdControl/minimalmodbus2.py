#!/usr/bin/env python3
import minimalmodbus
import time

instrument = minimalmodbus.Instrument('COM6', 10)  # port name, slave address (in decimal)
instrument.serial.baudrate = 9600
instrument.serial.timeout = 3

time.sleep(2)  # wait for the connection to be established
## Read temperature (PV = ProcessValue) ##

while True:
    instrument.write_bit(16, 0)  # Registernumber, number of decimals
    time.sleep(1)
    instrument.write_bit(16, 1)  # Registernumber, number of decimals
    time.sleep(1)
