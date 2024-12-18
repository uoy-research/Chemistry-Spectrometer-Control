"""
File: motor_controller.py
Description: Controller for stepper motor communication and control
"""

import minimalmodbus
import time
import logging
from typing import Optional


class MotorController:
    """
    Handles communication with stepper motor controller.

    Attributes:
        port (str): COM port for motor connection
        address (int): Modbus address
        verbose (bool): Enable verbose logging
        mode (int): Operation mode (1=normal, 2=test)
    """

    # Motor constants
    SPEED_MAX = 1000
    SPEED_MIN = 0
    POSITION_MAX = 1000
    POSITION_MIN = 0

    def __init__(self, port: int, address: int = 1, verbose: bool = False, mode: int = 1):
        """Initialize motor controller."""
        self.port = f"COM{port}"
        self.address = address
        self.verbose = verbose
        self.mode = mode
        self.instrument = None
        self.running = False
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)

    def start(self) -> bool:
        """
        Start communication with motor controller.

        Returns:
            bool: True if connection successful
        """
        try:
            self.instrument = minimalmodbus.Instrument(
                self.port,
                self.address
            )
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.timeout = 1

            # Test communication
            self.get_position()
            self.running = True
            self.logger.info(f"Connected to motor on {self.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to motor: {e}")
            return False

    def stop(self):
        """Stop communication with motor controller."""
        if self.instrument:
            self.instrument.serial.close()
        self.running = False

    def get_position(self) -> Optional[int]:
        """
        Get current motor position.

        Returns:
            int: Current position or None if error
        """
        if not self.running:
            return None

        try:
            if self.mode == 2:  # Test mode
                return 500  # Mock position

            position = self.instrument.read_register(0x0118)
            self.logger.debug(f"Current position: {position}")
            return position

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            return None

    def set_position(self, position: int, wait: bool = True) -> bool:
        """
        Move motor to specified position.

        Args:
            position (int): Target position
            wait (bool): Wait for movement to complete

        Returns:
            bool: True if successful
        """
        if not self.running:
            return False

        if not self.POSITION_MIN <= position <= self.POSITION_MAX:
            self.logger.error(f"Position {position} out of range")
            return False

        try:
            if self.mode == 2:  # Test mode
                time.sleep(1)  # Simulate movement
                return True

            # Set target position
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

    def set_speed(self, speed: int) -> bool:
        """
        Set motor speed.

        Args:
            speed (int): Target speed

        Returns:
            bool: True if successful
        """
        if not self.running:
            return False

        if not self.SPEED_MIN <= speed <= self.SPEED_MAX:
            self.logger.error(f"Speed {speed} out of range")
            return False

        try:
            if self.mode == 2:  # Test mode
                return True

            self.instrument.write_register(0x0119, speed)
            return True

        except Exception as e:
            self.logger.error(f"Error setting speed: {e}")
            return False

    def home(self) -> bool:
        """
        Move motor to home position.

        Returns:
            bool: True if successful
        """
        return self.set_position(0, wait=True)
