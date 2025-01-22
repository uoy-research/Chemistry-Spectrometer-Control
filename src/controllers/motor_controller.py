"""
File: src/controllers/motor_controller.py
"""

import minimalmodbus
import time
import logging
from typing import Optional, Union


class MotorController:
    SPEED_MAX = 1000
    SPEED_MIN = 0
    POSITION_MAX = 1000.0  # Maximum downward position
    POSITION_MIN = 0.0     # Home position (top)

    def __init__(self, port: int, address: int = 1, verbose: bool = False, mode: int = 1):
        self.port = f"COM{port}"
        self.address = address
        self.verbose = verbose
        self.mode = mode
        self.instrument = None
        self.running = False
        self._current_position = 0.0  # Initialize at home position for test mode
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

    def get_position(self) -> Optional[float]:
        """Get current motor position.
        
        Returns:
            float: Current position or None if not available
        """
        if not self.running:
            return None

        try:
            if self.mode == 2:  # Test mode
                return self._current_position

            # Convert from motor units if needed
            raw_position = self.instrument.read_register(0x0117)
            return float(raw_position)

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            return None

    def set_position(self, position: Union[int, float], wait: bool = False) -> bool:
        """Set motor position where 0 is home (top) position.
        
        Args:
            position: Target position (0 = home/top, increasing = down)
            wait: Whether to wait for movement to complete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.running:
            return False

        # Convert position to float for comparison
        position = float(position)
        
        if not self.POSITION_MIN <= position <= self.POSITION_MAX:
            self.logger.error(f"Position {position} out of range")
            return False

        try:
            if self.mode == 2:  # Test mode
                self._current_position = position
                return True

            # Convert to motor units if needed
            motor_position = int(position)  # Or apply any necessary conversion
            self.instrument.write_register(0x0118, motor_position)

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

    def stop_motor(self) -> bool:
        """Stop motor movement.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.running:
                # Send stop command to motor
                self.send_command('STOP')
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to stop motor: {e}")
            return False
