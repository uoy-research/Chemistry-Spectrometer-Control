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

    def __init__(self, port: int, address: int = 11, verbose: bool = False, mode: int = 1):
        self.port = f"COM{port}"
        self.address = address
        self.verbose = verbose
        self.mode = mode
        self.instrument = None
        self.running = False
        self.serial_connected = False  # Add serial connection state tracking
        self._current_position = 0.0  # Initialize at home position for test mode
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging for the Arduino controller."""
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.DEBUG)

    def start(self) -> bool:
        """Start and initialize the motor controller.
        
        Returns:
            bool: True if successfully started and initialized, False otherwise
        """
        try:
            if self.mode == 2:  # Test mode
                self.running = True
                self.serial_connected = True
                return True

            self.instrument = minimalmodbus.Instrument(self.port, self.address)
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.timeout = 3
            
            # Wait for connection to stabilize
            time.sleep(1)
            
            try:
                # Set initialization flag
                self.instrument.write_bit(3, 1)
                self.serial_connected = True
                self.logger.info(f"Connected to motor on {self.port}")
                
                # Verify initialization
                result = self.instrument.read_bit(3, 1)
                if result:
                    self.logger.info("Motor controller initialized")
                    self.running = True
                    return True
                else:
                    self.logger.error("Motor controller not initialized")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize motor controller: {e}")
                return False

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

            # Read two registers (high word first, then low word)
            registers = self.instrument.read_registers(5, 2, 3)
            
            # Combine high and low words into a single value
            # High word is shifted left 16 bits and combined with low word
            position = (registers[0] << 16) | registers[1]
            
            return float(position)

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

    def stop(self):
        """Stop the motor controller and clean up."""
        try:
            if self.serial_connected:
                # Clear initialization flag before disconnecting
                try:
                    self.instrument.write_bit(3, 0)
                except Exception as e:
                    self.logger.warning(f"Failed to clear init flag: {e}")
                    
            if self.instrument is not None:
                try:
                    self.instrument.serial.close()
                except Exception as e:
                    self.logger.warning(f"Failed to close serial port: {e}")
                    
            self.running = False
            self.serial_connected = False
            self.logger.info("Motor controller stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping motor controller: {e}")
