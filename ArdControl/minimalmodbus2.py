#!/usr/bin/env python3
import minimalmodbus
import time

# port name, slave address (in decimal)
instrument = minimalmodbus.Instrument('COM9', 11)
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
                5, 2, 3)  # reading current position
        except:
            pass
        time.sleep(0.5)

    high_word = readings[0]
    low_word = readings[1]
    combined = (high_word << 16) | low_word
    if combined >= 0x80000000:
        combined -= 0x100000000
    print(high_word, low_word)
    print(f"Current position: {combined}")
    input("Press Enter to continue...")

    instrument.write_bit(1, 1)  # writing 1 to toggle command flag
    instrument.write_register(2, ord('c'))  # writing 'i' to command register

    calibrated = False
    while calibrated == False:
        try:
            calibrated = instrument.read_bit(2, 1)  # reading calibration status
            readings = instrument.read_registers(
                5, 2, 3)  # reading current position
            high_word = readings[0]
            low_word = readings[1]
            combined = (high_word << 16) | low_word
            if combined >= 0x80000000:
                combined -= 0x100000000
            print(high_word, low_word)
            print(f"Current position: {combined}")

        except Exception as e:
            print("Not read", e)
            pass
        print(calibrated)
        time.sleep(0.2)

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
        print(targetPos)
        targetPos &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
        high = (targetPos >> 16) & 0xFFFF
        low = targetPos & 0xFFFF
        print([high, low])
        try:
            instrument.write_register(3, high)  # writing target position
            instrument.write_register(4, low)  # writing target position
        except:
            print("Not written")
            pass
        readings = instrument.read_registers(
                3, 2, 3)

        combined = ((readings[0] & 0xFFFF) << 16) | (readings[1] & 0xFFFF)
        combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow

        print(combined)

        try:
            instrument.write_register(2, ord('x'))
        except:
            print("Not written x2")
            pass


def disassemble(combined):
    combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
    high = (combined >> 16) & 0xFFFF
    low = combined & 0xFFFF
    return high, low

def assemble(high, low):
    combined = ((high & 0xFFFF) << 16) | (low & 0xFFFF)
    combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
    return combined