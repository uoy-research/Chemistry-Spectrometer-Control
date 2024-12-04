import threading
import serial
import logging
import time
import csv
import os
import minimalmodbus
import ctypes

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
            # self.instrument.close_port_after_each_call = True
            time.sleep(2)  # Wait for the connection to be established
            self.instrument.write_bit(3, 1)  # writing 1 to toggle init flag
            self.serial_connected = True
            logging.info(f"Connected to Arduino on port {self.port}")
            result = self.instrument.read_bit(3, 1)  # reading init flag
            if result:
                logging.info("Arduino initialized")
            else:
                logging.error("Arduino not initialized")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to Arduino on port {
                          self.port}: {e}")
            self.serial_connected = False
            return False

    def get_current_position(self):
        try:
            readings = self.instrument.read_registers(  # type: ignore
                5, 2, 3)
            self.motor_position = self.assemble(readings[0], readings[1])
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't read motor position: %s", e)
            self.serial_connected = False
            pass
        return self.motor_position

    def calibrate(self):
        try:
            self.instrument.write_register(2, ord('c'))  # type: ignore
            time.sleep(1)
            # writing 'c' to command register
            try:
                # writing 1 to toggle command flag
                self.instrument.write_bit(1, 1)  # type: ignore
                self.serial_connected = True
                logging.info("Calibrating motor, please wait")
            except Exception as e:
                logging.error("Couldn't write to command register: %s", e)
                self.serial_connected = False
        except Exception as e:
            logging.error("Couldn't calibrate motor: %s", e)
            self.serial_connected = False

    def check_calibrated(self):
        try:
            # reading calibration status
            calibrated = self.instrument.read_bit(2, 1)  # type: ignore
            # logging.info(f"Calibrated: {calibrated}")
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't read calibration status: %s", e)
            self.serial_connected = False
            calibrated = False
        return calibrated

    def move_to_position(self, position):
        try:
            if self.check_calibrated():
                high, low = self.disassemble(position)  # type: ignore
                # writing high word
                self.instrument.write_register(3, high)  # type: ignore
                # writing low word
                self.instrument.write_register(4, low)  # type: ignore
                # writing 'x' to command register
                self.instrument.write_register(2, ord('x'))  # type: ignore
                # writing 1 to toggle command flag
                self.instrument.write_bit(1, 1)  # type: ignore
                self.serial_connected = True
            else:
                logging.error("Motor not calibrated")
                self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't move to position: %s", e)
            self.serial_connected = False
            pass

    def stop_motor(self):
        try:
            self.instrument.write_register(2, ord('s'))  # type: ignore
            self.instrument.write_bit(1, 1)  # type: ignore
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't stop motor: %s", e)
            self.serial_connected = False
            pass

    def shutdown(self):
        try:
            if hasattr(self, 'instrument') and self.instrument:
                self.instrument.write_register(2, ord('s'))  # type: ignore
                self.instrument.write_bit(1, 1)  # type: ignore
                self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't stop motor: %s", e)
            self.serial_connected = False
            pass

    def disassemble(self, combined):
        combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
        high = (combined >> 16) & 0xFFFF
        low = combined & 0xFFFF
        return high, low

    def assemble(self, high, low):
        high = ctypes.c_int16(high).value   # Convert high to signed int16
        combined = (high << 16) | (low & 0xFFFF)
        return combined

    def ascent(self):
        try:
            self.instrument.write_register(2, ord('u'))  # type: ignore
            self.instrument.write_bit(1, 1)  # type: ignore
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't move up: %s", e)
            self.serial_connected = False
            pass

    def to_top(self):
        try:
            self.instrument.write_register(2, ord('t'))  # type: ignore
            self.instrument.write_bit(1, 1)  # type: ignore
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't move to top: %s", e)
            self.serial_connected = False
            pass

    def get_top_position(self):
        try:
            readings = self.instrument.read_registers(  # type: ignore
                7, 2, 3)
            top_position = self.assemble(readings[0], readings[1])
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't read top position: %s", e)
            self.serial_connected = False
            pass
        return top_position

    def reset(self):
        try:
            self.instrument.write_register(2, ord('e'))  # type: ignore
            self.instrument.write_bit(1, 1)  # type: ignore
            self.serial_connected = True
        except Exception as e:
            logging.error("Couldn't reset motor: %s", e)
            self.serial_connected = False
            pass
        finally:
            if hasattr(self, 'instrument') and self.instrument:
                self.instrument.serial.close()  # type: ignore
