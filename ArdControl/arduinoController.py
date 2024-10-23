#!/usr/bin/env python3
import minimalmodbus
import threading
import serial
import logging
import time
import csv
import os

# +--------------------------+---------+-----------------------------------------+
# |         Coil/reg         | Address |                 Purpose                 |
# +--------------------------+---------+-----------------------------------------+
# | Valve coils              | 0-7     | 8 digital valve states (only 5 in use)  |
# | Pressure Gauge Registers | 0-3     | Input registers for the pressure gauges |
# | ,                        | ,       | Must be read with func code 4           |
# | ,                        | ,       | Values not converted to bar             |
# | TTL Coil                 | 16      | Used to enable/disable TTL control      |
# | Reset Coil               | 17      | Used to reset the system from GUI       |
# | depressurise Coil        | 18      | Used to depressurise system from GUI    |
# +--------------------------+---------+-----------------------------------------+


class ArduinoController:
    def __init__(self, port, verbose, mode):
        self.port = port    # Port number to connect to arduino
        self.baudrate = 9600    # Baudrate for serial connection
        self.verbose = verbose  # Verbose mode
        # Mode of operation (0 = manual, 1 = sequence, 2 = TTL)
        self.mode = mode
        self.arduino = None  # Container for arduino object
        # Container for valve states
        self.valve_states = [0, 0, 0, 0, 0, 0, 0, 0]
        self.readings = [0, 0, 0, 0]  # Container for pressure readings
        self.serial_connected = False   # Flag to indicate serial connection
        self.new_reading = False  # Flag to indicate new pressure reading

        self.valveAddr = [0, 1, 2, 3, 4, 5, 6, 7]
        self.pressureAddr = [0, 1, 2, 3]
        self.ttlAddr = 16
        self.resetAddr = 1
        self.depressuriseAddr = 0

        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        if mode == 0:
            logging.info("Manual mode enabled")
        elif mode == 1:
            logging.info("Magritek mode enabled")
        elif mode == 2:
            logging.info("TTL mode enabled")
        else:
            logging.error("Invalid mode, defaulting to manual mode")
            self.mode = 0

    def start(self):
        logging.info("Starting server...")
        self.connect_arduino()
        if self.serial_connected:
            logging.info("Arduino started")
            if self.mode == 2:
                # type: ignore # Enable TTL control
                self.arduino.write_bit(self.ttlAddr, 1)  # type: ignore
            else:
                # type: ignore # Disable TTL control
                self.arduino.write_bit(self.ttlAddr, 0)  # type: ignore
        else:
            logging.error("Failed to connect to Arduino. Server not started.")
            self.arduino = None
            self.serial_connected = False

    def connect_arduino(self):
        try:
            self.arduino = minimalmodbus.Instrument(f"COM{self.port}", 10)
            self.arduino.serial.baudrate = self.baudrate    # type: ignore
            self.arduino.serial.timeout = 3   # type: ignore
            time.sleep(2)  # Wait for the connection to be established
            self.readings = self.arduino.read_registers(
                0, 4, 4)    # type: ignore
            logging.info(f"Connected to Arduino on port {self.port}")
            self.serial_connected = True
        except Exception as e:
            logging.error(f"Failed to connect to Arduino on port {
                          self.port}: {e}")
            self.serial_connected = False

    def get_readings(self):
        try:
            self.readings = self.arduino.read_registers(    # type: ignore
                0, 4, 4)
            self.serial_connected = True
        except:
            logging.error("Failed to read pressure readings")
            self.serial_connected = False
        return self.readings

    def get_valve_states(self):
        try:
            # read_bits MUST use functioncode = 1
            self.valve_states = self.arduino.read_bits(0, 8, 1)  # type: ignore
            self.serial_connected = True
        except:
            logging.error("Failed to read valve states")
            self.serial_connected = False
        return self.valve_states

    def set_valves(self, valve_states):
        try:
            for i in range(8):
                if valve_states[i] != 2:
                    self.arduino.write_bit(i, valve_states[i])  # type: ignore
            self.serial_connected = True
        except:
            logging.error("Failed to set valve states")
            self.serial_connected = False

    def send_reset(self):
        try:
            self.arduino.write_bit(self.resetAddr, 1)  # type: ignore
            self.serial_connected = True
        except:
            logging.error("Failed to reset system")
            self.serial_connected = False

    def send_depressurise(self):
        try:
            self.arduino.write_bit(self.depressuriseAddr, 1)  # type: ignore
            self.serial_connected = True
        except:
            logging.error("Failed to depressurise system")
            self.serial_connected = False

    def get_mode(self):
        return self.mode
