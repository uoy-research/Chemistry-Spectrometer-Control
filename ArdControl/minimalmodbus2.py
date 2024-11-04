#!/usr/bin/env python3
import minimalmodbus
import time

# port name, slave address (in decimal)
instrument = minimalmodbus.Instrument('COM8', 11)
instrument.serial.baudrate = 9600   # type: ignore
instrument.serial.timeout = 3   # type: ignore

time.sleep(2)  # wait for the connection to be established

while True:
    # instrument.write_bit(16, 0)  # Registernumber, number of decimals
    # time.sleep(1)
    # instrument.write_bit(16, 1)  # Registernumber, number of decimals
    # readings = instrument.read_registers(0, 4, 4)  # reading registers 0 to 4 - pressure gauges
    readings = False
    while readings == False:
        try:
            readings = instrument.read_registers(
                4, 2, 4)  # reading current position
        except:
            pass
        time.sleep(0.5)

    high_word = readings[0]
    low_word = readings[1]
    combined = (high_word << 16) | low_word
    if combined >= 0x80000000:
        combined -= 0x100000000
    print(f"Current position: {combined}")
    input("Press Enter to continue...")

    instrument.write_bit(3, 1)  # writing 1 to toggle init flag
    instrument.write_register(1, ord('i'), 0)  # writing 0 to setpoint register

    calibrated = False
    while calibrated == False:
        calibrated = instrument.read_bit(2, 1)  # reading calibration status
        time.sleep(0.5)

    print("Calibrated?")
    while True:
        target = " "
        while not isinstance(target, int):
            target = input("Enter target position: ")
            if target == "q":
                break
            else:
                try:
                    target = int(target)
                except:
                    print("Invalid input")
                    continue
        targetPos = int(target)
        targetPos &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
        high = (combined >> 16) & 0xFFFF
        low = combined & 0xFFFF
        instrument.write_registers(2, [high, low])  # writing target position
        instrument.write_register(1, ord('x'), 0)


def disassemble(combined):
    combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
    high = (combined >> 16) & 0xFFFF
    low = combined & 0xFFFF
    return high, low
