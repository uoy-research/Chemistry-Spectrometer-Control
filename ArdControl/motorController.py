"""
File: motorController.py
Description: Controls motor movements and position management through Modbus protocol.
"""

import threading
import serial
import logging
import time
import csv
import os
import minimalmodbus
import ctypes

class MotorController:
    """
    Controls motor movements and manages position through Modbus communication.
    
    Attributes:
        port (int): COM port number for serial communication
        serial_connected (bool): Connection status flag
        motor_position (int): Current motor position
        target_position (int): Target position for movement
    """
    
    # Class constants
    BAUD_RATE = 9600
    DEFAULT_TIMEOUT = 3
    STEPS_PER_MM = 25600  # microsteps per millimeter
    
    # Modbus commands
    COMMANDS = {
        "HEARTBEAT": 'y',    # Heartbeat response
        "START": 'S',        # Start the Arduino
        "STOP": 's',         # Stop the Arduino
        "DOWN": 'd',         # Move down
        "UP": 'u',           # Move up
        "GOTO_POS": 'p',     # Go to position
        "GET_POS": 'g',      # Get current position
        "GET_STATUS": 't',   # Get status
        "CALIBRATE": 'c',    # Calibrate
    }

    def __init__(self, port: int):
        """
        Initialize motor controller.
        
        Args:
            port (int): COM port number for serial connection
        """
        self.port = port
        self.serial_connected = False
        self.motor_position = 0
        self.target_position = 0
        self.instrument = None
        
        # Thread management
        self.shutdown_flag = False
        self.heartbeat_thread = None
        self.reading_thread = None

    def start(self):
        """Start the motor controller and establish connection."""
        logging.info("Starting motor controller...")
        if self._connect_arduino():
            logging.info("Motor controller started")
        else:
            logging.error("Failed to start motor controller")
            self.serial_connected = False
            self.instrument = None

    def _connect_arduino(self):
        """
        Establish Modbus connection with Arduino.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.instrument = minimalmodbus.Instrument(f"COM{self.port}", 11)
            self.instrument.serial.baudrate = self.BAUD_RATE    # type: ignore
            self.instrument.serial.timeout = self.DEFAULT_TIMEOUT   # type: ignore
            time.sleep(2)  # Wait for connection establishment
            
            # Initialize Arduino
            self.instrument.write_bit(3, 1)  # Toggle init flag
            self.serial_connected = True
            logging.info(f"Connected to Arduino on port {self.port}")
            
            # Verify initialization
            if self.instrument.read_bit(3, 1):  # Read init flag
                logging.info("Arduino initialized")
                return True
            else:
                logging.error("Arduino not initialized")
                return False
                
        except Exception as e:
            logging.error(f"Failed to connect to Arduino on port {self.port}: {e}")
            self.serial_connected = False
            return False

    def get_current_position(self):
        """
        Read current motor position from registers.
        
        Returns:
            int: Current motor position
        """
        try:
            readings = self.instrument.read_registers(5, 2, 3)  # type: ignore
            self.motor_position = self._assemble(readings[0], readings[1])
            self.serial_connected = True
        except Exception as e:
            logging.error(f"Couldn't read motor position: {e}")
            self.serial_connected = False
        return self.motor_position

    def calibrate(self):
        """Initiate motor calibration sequence."""
        try:
            self.instrument.write_register(2, ord('c'))  # Write calibrate command
            time.sleep(1)
            self.instrument.write_bit(1, 1)  # Toggle command flag
            self.serial_connected = True
            logging.info("Calibrating motor, please wait")
        except Exception as e:
            logging.error(f"Couldn't calibrate motor: {e}")
            self.serial_connected = False

    def check_calibrated(self):
        """
        Check if motor is calibrated.
        
        Returns:
            bool: True if calibrated, False otherwise
        """
        try:
            calibrated = self.instrument.read_bit(2, 1)  # type: ignore
            self.serial_connected = True
            return calibrated
        except Exception as e:
            logging.error(f"Couldn't read calibration status: {e}")
            self.serial_connected = False
            return False

    def move_to_position(self, position: int):
        """
        Move motor to specified position.
        
        Args:
            position (int): Target position in steps
        """
        try:
            if self.check_calibrated():
                high, low = self._disassemble(position)
                self.instrument.write_register(3, high)  # Write high word
                self.instrument.write_register(4, low)   # Write low word
                self.instrument.write_register(2, ord('x'))  # Write move command
                self.instrument.write_bit(1, 1)  # Toggle command flag
                self.serial_connected = True
            else:
                logging.error("Motor not calibrated")
        except Exception as e:
            logging.error(f"Couldn't move to position: {e}")
            self.serial_connected = False

    def stop_motor(self):
        """Stop motor movement immediately."""
        try:
            self.instrument.write_register(2, ord('s'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
        except Exception as e:
            logging.error(f"Couldn't stop motor: {e}")
            self.serial_connected = False

    def shutdown(self):
        """Safely shutdown motor controller."""
        try:
            if hasattr(self, 'instrument') and self.instrument:
                self.instrument.write_register(2, ord('s'))
                self.instrument.write_bit(1, 1)
                self.serial_connected = True
        except Exception as e:
            logging.error(f"Couldn't stop motor: {e}")
            self.serial_connected = False

    @staticmethod
    def _disassemble(combined: int) -> tuple[int, int]:
        """
        Split 32-bit position into high and low 16-bit words.
        
        Args:
            combined (int): 32-bit position value
            
        Returns:
            tuple[int, int]: High and low 16-bit words
        """
        combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
        high = (combined >> 16) & 0xFFFF
        low = combined & 0xFFFF
        return high, low

    @staticmethod
    def _assemble(high: int, low: int) -> int:
        """
        Combine high and low 16-bit words into 32-bit position.
        
        Args:
            high (int): High 16-bit word
            low (int): Low 16-bit word
            
        Returns:
            int: Combined 32-bit position value
        """
        high = ctypes.c_int16(high).value  # Convert high to signed int16
        combined = (high << 16) | (low & 0xFFFF)
        return combined

    def ascent(self):
        """Move motor upward."""
        try:
            self.instrument.write_register(2, ord('u'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
        except Exception as e:
            logging.error(f"Couldn't move up: {e}")
            self.serial_connected = False

    def to_top(self):
        """Move motor to top position."""
        try:
            self.instrument.write_register(2, ord('t'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
        except Exception as e:
            logging.error(f"Couldn't move to top: {e}")
            self.serial_connected = False

    def get_top_position(self):
        """
        Get the calibrated top position.
        
        Returns:
            int: Top position value
        """
        try:
            readings = self.instrument.read_registers(7, 2, 3)  # type: ignore
            top_position = self._assemble(readings[0], readings[1])
            self.serial_connected = True
            return top_position
        except Exception as e:
            logging.error(f"Couldn't read top position: {e}")
            self.serial_connected = False
            return 0

    def reset(self):
        """Reset motor controller and close connection."""
        try:
            self.instrument.write_register(2, ord('e'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
        except Exception as e:
            logging.error(f"Couldn't reset motor: {e}")
            self.serial_connected = False
        finally:
            if hasattr(self, 'instrument') and self.instrument:
                self.instrument.serial.close()  # type: ignore
