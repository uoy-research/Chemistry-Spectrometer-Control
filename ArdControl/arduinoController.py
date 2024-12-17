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
    """
    Controls communication with Arduino for valve and pressure management.
    
    Handles serial communication, valve states, and pressure readings through
    Modbus protocol.
    """
    
    # Class constants
    BAUD_RATE = 9600
    DEFAULT_TIMEOUT = 3
    
    # Modbus addresses
    VALVE_ADDRESSES = range(8)  # 0-7
    PRESSURE_ADDRESSES = range(4)  # 0-3
    TTL_ADDRESS = 16
    RESET_ADDRESS = 17
    DEPRESSURIZE_ADDRESS = 18
    
    def __init__(self, port: int, verbose: bool, mode: int):
        """
        Initialize Arduino controller.
        
        Args:
            port (int): COM port number
            verbose (bool): Enable verbose logging
            mode (int): Operation mode (0=manual, 1=sequence, 2=TTL)
        """
        self.port = port
        self.verbose = verbose
        self.mode = mode
        
        # Status flags
        self.serial_connected = False
        self.new_reading = False
        
        # State containers
        self.arduino = None
        self.valve_states = [0] * 8
        self.readings = [0] * 4
        
        self._configure_logging()
        self._validate_mode()

    def _configure_logging(self):
        if self.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    def _validate_mode(self):
        if self.mode == 0:
            logging.info("Manual mode enabled")
        elif self.mode == 1:
            logging.info("Magritek mode enabled")
        elif self.mode == 2:
            logging.info("TTL mode enabled")
        else:
            logging.error("Invalid mode, defaulting to manual mode")
            self.mode = 0

    def start(self):
        logging.info("Starting server...")
        if self.connect_arduino():
            try:
                if self.mode == 2:
                    # type: ignore # Enable TTL control
                    self.arduino.write_bit(self.TTL_ADDRESS, 1)  # type: ignore
                else:
                    # type: ignore # Disable TTL control
                    self.arduino.write_bit(self.TTL_ADDRESS, 0)  # type: ignore
                logging.info("Arduino started")
            except:
                logging.error("Failed to connect to Arduino. Server not started.")
                self.arduino = None
                self.serial_connected = False
        else:
            logging.error("Failed to connect to Arduino. Server not started.")
            self.arduino = None
            self.serial_connected = False

    def connect_arduino(self):
        try:
            self.arduino = minimalmodbus.Instrument(f"COM{self.port}", 10)
            self.arduino.serial.baudrate = self.BAUD_RATE    # type: ignore
            self.arduino.serial.timeout = self.DEFAULT_TIMEOUT   # type: ignore
            # self.arduino.close_port_after_each_call = True
            time.sleep(1)  # Wait for the connection to be established
            self.readings = self.arduino.read_registers(
                0, 4, 4)    # type: ignore
            logging.info(f"Connected to Arduino on port {self.port}")
            self.serial_connected = True
            return True
        except Exception as e:
            logging.error(f"Failed to connect to Arduino on port {
                          self.port}: {e}")
            self.serial_connected = False
            return False

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
            """
            for i in range(8):
                if valve_states[i] != 2:
                    self.arduino.write_bit(i, valve_states[i])  # type: ignore
            self.serial_connected = True
            """
            write_states = [self.valve_states[i] if valve_states[i]
                            == 2 else valve_states[i] for i in range(8)]
            self.arduino.write_bits(0, write_states)  # type: ignore
            self.serial_connected = True
        except:
            logging.error("Failed to set valve states")
            self.serial_connected = False

    def send_reset(self):
        try:
            self.arduino.write_bit(self.RESET_ADDRESS, 1)  # type: ignore
            self.serial_connected = True
        except:
            #logging.error("Failed to reset system")
            self.serial_connected = False
        finally:
            if hasattr(self.arduino, 'serial'):
                self.arduino.serial.close()  # type: ignore

    def send_depressurise(self):
        try:
            self.arduino.write_bit(self.DEPRESSURIZE_ADDRESS, 1)  # type: ignore
            self.serial_connected = True
        except:
            logging.error("Failed to depressurise system")
            self.serial_connected = False

    def get_mode(self):
        return self.mode

    def get_ttl_state(self):
        return self.arduino.read_bit(16, 1)  # type: ignore

    def disable_ttl(self):
        try:
            self.arduino.write_bit(self.TTL_ADDRESS, 0)  # type: ignore
            self.serial_connected = True
        except:
            logging.error("Failed to disable TTL")
            self.serial_connected = False
