"""
File: src/controllers/arduino_controller.py
"""

import serial
import time
import logging
from typing import List, Optional


class ArduinoController:
    def __init__(self, port: int, verbose: bool = False, mode: int = 1):
        self.port = f"COM{port}"
        self.verbose = verbose
        self.mode = mode
        self.serial = None
        self.running = False
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging for the Arduino controller."""
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

    def start(self) -> bool:
        try:
            if self.mode == 2:  # Test mode
                self.running = True
                return True

            self.serial = serial.Serial(self.port, 9600, timeout=1)
            self.running = True
            self.logger.info(f"Connected to Arduino on {self.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Arduino: {e}")
            return False

    def get_readings(self) -> Optional[List[float]]:
        if not self.running:
            return None

        try:
            if self.mode == 2:  # Test mode
                return [1.0, 2.0, 3.0]

            response = self.serial.readline().decode().strip()
            if not response:
                return None

            try:
                readings = [float(x) for x in response.split(',')]
                self.logger.debug(f"Readings: {readings}")
                return readings
            except ValueError:
                return None

        except Exception as e:
            self.logger.error(f"Error getting readings: {e}")
            return None

    def set_valves(self, states: List[int]) -> bool:
        if not self.running:
            return False

        if len(states) != 8 or not all(x in [0, 1] for x in states):
            return False

        try:
            if self.mode == 2:  # Test mode
                return True

            command = f"v{''.join(map(str, states))}"
            self.serial.write(command.encode())
            response = self.serial.readline().decode().strip()
            return response == "OK"

        except Exception as e:
            self.logger.error(f"Error setting valves: {e}")
            return False
