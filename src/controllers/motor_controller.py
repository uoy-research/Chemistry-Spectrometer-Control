"""
File: src/controllers/motor_controller.py
"""

import minimalmodbus
import time
import logging
import ctypes
from typing import Optional, Union, Tuple


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
        self.motor_position = 0
        self.target_position = 0
        self._position_offset = 0  # Add position offset tracking
        self._is_calibrated = False
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
            # Configure Modbus RTU settings
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.timeout = 5
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = 'N'
            self.instrument.serial.stopbits = 1
            self.instrument.mode = minimalmodbus.MODE_RTU
            self.instrument.clear_buffers_before_each_transaction = True
            
            # Wait for connection to stabilize
            time.sleep(1)
            
            try:
                self.instrument.write_bit(3, 1)
                self.serial_connected = True
                self.logger.info(f"Connected to motor on {self.port}")
                
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
        """Get current motor position."""
        if not self.running:
            return None

        try:
            if self.mode == 2:  # Test mode
                return self._current_position

            # Add retry mechanism for reading position
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Read registers with explicit function code
                    readings = self.instrument.read_registers(5, 2, functioncode=3)
                    motor_position = self.assemble(readings[0], readings[1])
                    position = -motor_position
                    self.motor_position = position
                    return float(position)
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    time.sleep(0.1)  # Short delay before retry

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            self.serial_connected = False
            return None

    def calibrate(self) -> bool:
        """Calibrate the motor."""
        try:
            # Send calibration command
            self.instrument.write_register(2, ord('c'))
            time.sleep(1)
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
            self.logger.info("Calibrating motor, please wait")
            
            # Wait for calibration to complete
            time.sleep(4)  # Initial wait time
            
            # Wait until calibration bit is set
            max_attempts = 10  # 5 seconds timeout
            for _ in range(max_attempts):
                if self.check_calibrated():
                    time.sleep(0.5)  # Wait for motor to settle
                    self._is_calibrated = True
                    self.logger.info("Calibration complete")
                    return True
                time.sleep(1)
            
            self.logger.error("Calibration timed out waiting for calibration bit")
            return False
            
        except Exception as e:
            self.logger.error(f"Couldn't calibrate motor: {e}")
            self.serial_connected = False
            return False

    def check_calibrated(self) -> bool:
        """Check if motor is calibrated."""
        try:
            calibrated = self.instrument.read_bit(2, 1)
            self.serial_connected = True
            return bool(calibrated)
        except Exception as e:
            self.logger.error(f"Couldn't read calibration status: {e}")
            self.serial_connected = False
            return False

    def set_position(self, position: Union[int, float], wait: bool = False) -> bool:
        """Set motor position."""
        if not self.running:
            return False

        try:
            position = float(position)
            
            if position > self.POSITION_MAX:
                self.logger.error(f"Position {position} exceeds maximum {self.POSITION_MAX}")
                return False

            if self.mode == 2:  # Test mode
                self._current_position = position
                return True

            if self.check_calibrated():
                # Invert the sign of the position for the motor
                motor_position = -position
                
                # Convert position to high and low words
                high, low = self.disassemble(int(motor_position))
                
                # Send the position to the motor
                self.instrument.write_register(3, high)  # Write high word
                self.instrument.write_register(4, low)   # Write low word
                self.instrument.write_register(2, ord('x'))  # Position command
                self.instrument.write_bit(1, 1)  # Toggle command flag
                self.serial_connected = True

                if wait:
                    while True:
                        current = self.get_position()
                        if current is not None and abs(current - position) < 0.01:
                            break
                        time.sleep(0.1)

                return True
            else:
                self.logger.error("Motor not calibrated")
                return False

        except Exception as e:
            self.logger.error(f"Error setting position: {e}")
            self.serial_connected = False
            return False

    def move_to_position(self, position: Union[int, float]) -> bool:
        """Alternative method for moving to position (for compatibility)."""
        return self.set_position(position)

    def stop_motor(self) -> bool:
        """Stop motor movement."""
        try:
            self.instrument.write_register(2, ord('s'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
            return True
        except Exception as e:
            self.logger.error(f"Couldn't stop motor: {e}")
            self.serial_connected = False
            return False

    def ascent(self) -> bool:
        """Move motor up."""
        try:
            self.instrument.write_register(2, ord('u'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
            return True
        except Exception as e:
            self.logger.error(f"Couldn't move up: {e}")
            self.serial_connected = False
            return False

    def to_top(self) -> bool:
        """Move motor to top position."""
        try:
            self.instrument.write_register(2, ord('t'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
            return True
        except Exception as e:
            self.logger.error(f"Couldn't move to top: {e}")
            self.serial_connected = False
            return False

    def get_top_position(self) -> Optional[int]:
        """Get the top position of the motor."""
        try:
            readings = self.instrument.read_registers(7, 2, 3)
            top_position = self.assemble(readings[0], readings[1])
            self.serial_connected = True
            return top_position
        except Exception as e:
            self.logger.error(f"Couldn't read top position: {e}")
            self.serial_connected = False
            return None

    def reset(self):
        """Reset the motor controller."""
        try:
            self.instrument.write_register(2, ord('e'))
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
        except Exception as e:
            self.logger.error(f"Couldn't reset motor: {e}")
            self.serial_connected = False
        finally:
            if hasattr(self, 'instrument') and self.instrument:
                self.instrument.serial.close()

    def stop(self):
        """Stop the motor controller and clean up."""
        try:
            if self.serial_connected:
                self.stop_motor()
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

    def disassemble(self, combined):
        """Disassemble a 32-bit value into high and low 16-bit words."""
        combined &= 0xFFFFFFFF  # Simulate 32-bit integer overflow
        high = (combined >> 16) & 0xFFFF
        low = combined & 0xFFFF
        return high, low

    def assemble(self, high, low):
        """Assemble high and low 16-bit words into a 32-bit value."""
        high = ctypes.c_int16(high).value   # Convert high to signed int16
        combined = (high << 16) | (low & 0xFFFF)
        return combined
