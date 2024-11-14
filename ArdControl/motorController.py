import threading
import serial
import logging
import time
import csv
import os
import minimalmodbus

# 25,600 microsteps per millimeter


class MotorController:
    def __init__(self, port):
        self.port = port
        self.baudrate = 9600
        # self.arduino = None
        self.shutdown_flag = False
        self.serial_connected = False
        self.heartbeat_thread = None
        self.reading_thread = None
        self.motor_position = 0
        self.target_position = 0
        self.commands_dict = {
            "HEARTBEAT": 'y',  # Heartbeat response
            "START": 'S',    # Start the Arduino
            "STOP": 's',     # Stop the Arduino
            "DOWN": 'd',     # Move down
            "UP": 'u',       # Move up
            "GOTOPOS": 'p',  # Go to position
            "GETPOS": 'g',   # Get current position
            "GETSTATUS": 't',  # Get status
            "CALIBRATE": 'c',  # Calibrate
        }

    def start(self):
        logging.info("Starting motor controller...")
        if self.connect_arduino():
            logging.info("Motor controller started")
        else:
            logging.error("Failed to start motor controller")
            self.serial_connected = False
            self.instrument = None

    def connect_arduino(self):
        try:
            self.instrument = minimalmodbus.Instrument(f"COM{self.port}", 11)
            self.instrument.serial.baudrate = self.baudrate    # type: ignore
            self.instrument.serial.timeout = 3   # type: ignore
            self.instrument.write_bit(3, 1)  # writing 1 to toggle init flag
            self.serial_connected = True
            logging.info(f"Connected to Arduino on port {self.port}")
        except serial.SerialException as e:
            logging.error(f"Failed to connect to Arduino on port {
                          self.port}: {e}")
            self.serial_connected = False

    def get_current_position(self):
        try:
            readings = self.instrument.read_registers(  # type: ignore
                5, 2, 3)
            self.motor_position = self.assemble(readings[0], readings[1])
        except Exception as e:
            logging.error("Couldn't read motor position", e)
            self.serial_connected = False
            pass
        return self.motor_position

    def calibrate(self):
        # writing 'c' to command register
        self.instrument.write_register(2, ord('c'))  # type: ignore
        self.instrument.write_bit(1, 1)  # writing 1 to toggle command flag # type: ignore
        self.serial_connected = True

    def check_calibrated(self):
        try:
            # reading calibration status
            calibrated = self.instrument.read_bit(2, 1)  # type: ignore
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't read calibration status", e)
            self.serial_connected = False
            calibrated = False
        return calibrated

    def move_to_position(self, position):
        try:
            if self.check_calibrated():
                high, low = self.disassemble(position)  # type: ignore
                # writing high word
                self.instrument.write_register(5, high, 3)  # type: ignore
                # writing low word
                self.instrument.write_register(6, low, 3)  # type: ignore
                # writing 'x' to command register
                self.instrument.write_register(2, ord('x'))  # type: ignore
                # writing 1 to toggle command flag
                self.instrument.write_bit(1, 1)  # type: ignore
                self.serial_connected = True
            else:
                logging.error("Motor not calibrated")
                self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't move to position", e)
            self.serial_connected = False
            pass

    def stop_motor(self):
        try:
            self.instrument.write_register(2, ord('s'))  # type: ignore
            self.instrument.write_bit(1, 1)  # type: ignore
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't stop motor", e)
            self.serial_connected = False
            pass

    def shutdown(self):
        try:
            self.instrument.write_register(2, ord('e'))  # type: ignore
            self.instrument.write_bit(1, 1)  # type: ignore
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't stop motor", e)
            self.serial_connected = False
            pass

    def disassemble(self, combined):
        combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
        high = (combined >> 16) & 0xFFFF
        low = combined & 0xFFFF
        return high, low

    def assemble(self, high, low):
        combined = ((high & 0xFFFF) << 16) | (low & 0xFFFF)
        combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
        return combined
