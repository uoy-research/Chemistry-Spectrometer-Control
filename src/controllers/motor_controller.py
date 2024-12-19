"""
File: src/controllers/motor_controller.py
"""

import minimalmodbus
import time
import logging
from typing import Optional


class MotorController:
    SPEED_MAX = 1000
    SPEED_MIN = 0
    POSITION_MAX = 1000
    POSITION_MIN = 0

    def __init__(self, port: int, address: int = 1, verbose: bool = False, mode: int = 1):
        self.port = f"COM{port}"
        self.address = address
        self.verbose = verbose
        self.mode = mode
        self.instrument = None
        self.running = False
        self._current_position = 500  # For test mode
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

            self.instrument = minimalmodbus.Instrument(self.port, self.address)
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.timeout = 1
            self.running = True
            self.logger.info(f"Connected to motor on {self.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to motor: {e}")
            return False

    def get_position(self) -> Optional[int]:
        if not self.running:
            return None

        try:
            if self.mode == 2:  # Test mode
                return self._current_position

            return self.instrument.read_register(0x0117)

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            return None

    def set_position(self, position: int, wait: bool = False) -> bool:
        if not self.running:
            return False

        if not self.POSITION_MIN <= position <= self.POSITION_MAX:
            self.logger.error(f"Position {position} out of range")
            return False

        try:
            if self.mode == 2:  # Test mode
                self._current_position = position
                return True

            self.instrument.write_register(0x0118, position)

            if wait:
                while True:
                    current = self.get_position()
                    if current == position:
                        break
                    time.sleep(0.1)

            return True

        except Exception as e:
            self.logger.error(f"Error setting position: {e}")
            return False
