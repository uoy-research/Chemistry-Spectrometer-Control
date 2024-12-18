"""
File: arduino_controller.py
Description: Controller for Arduino communication and valve control
"""

import serial
import time
import logging
from typing import List, Optional


class ArduinoController:
    """
    Handles communication with Arduino for valve control and pressure readings.

    Attributes:
        port (str): COM port for Arduino connection
        verbose (bool): Enable verbose logging
        mode (int): Operation mode (1=normal, 2=test)
    """

    def __init__(self, port: int, verbose: bool = False, mode: int = 1):
        """Initialize Arduino controller."""
        self.port = f"COM{port}"
        self.verbose = verbose
        self.mode = mode
        self.serial = None
        self.running = False
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)

    def start(self) -> bool:
        """
        Start communication with Arduino.

        Returns:
            bool: True if connection successful
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=9600,
                timeout=1
            )
            time.sleep(2)  # Wait for Arduino reset
            self.running = True
            self.logger.info(f"Connected to Arduino on {self.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Arduino: {e}")
            return False

    def stop(self):
        """Stop communication with Arduino."""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.running = False

    def get_readings(self) -> Optional[List[float]]:
        """
        Get pressure readings from sensors.

        Returns:
            List[float]: List of pressure readings or None if error
        """
        if not self.running:
            return None

        try:
            if self.mode == 2:  # Test mode
                return [1.0, 2.0, 3.0]  # Mock readings

            self.serial.write(b'r')  # Request readings
            response = self.serial.readline().decode().strip()

            if not response:
                return None

            readings = [float(x) for x in response.split(',')]
            self.logger.debug(f"Readings: {readings}")
            return readings

        except Exception as e:
            self.logger.error(f"Error getting readings: {e}")
            return None

    def set_valves(self, states: List[int]) -> bool:
        """
        Set valve states.

        Args:
            states (List[int]): List of valve states (0=closed, 1=open, 2=unchanged)

        Returns:
            bool: True if successful
        """
        if not self.running or len(states) != 8:
            return False

        try:
            if self.mode == 2:  # Test mode
                return True

            command = 'v' + ''.join(str(s) for s in states)
            self.serial.write(command.encode())
            response = self.serial.readline().decode().strip()

            success = response == 'OK'
            if not success:
                self.logger.error(f"Invalid valve response: {response}")
            return success

        except Exception as e:
            self.logger.error(f"Error setting valves: {e}")
            return False

    def send_depressurise(self) -> bool:
        """
        Send emergency depressurize command.

        Returns:
            bool: True if successful
        """
        try:
            if self.mode == 2:  # Test mode
                return True

            self.serial.write(b'd')
            response = self.serial.readline().decode().strip()
            return response == 'OK'

        except Exception as e:
            self.logger.error(f"Error sending depressurize: {e}")
            return False
