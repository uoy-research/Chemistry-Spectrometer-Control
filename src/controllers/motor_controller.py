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
    POSITION_MAX = 364.40  # Maximum downward position
    POSITION_MIN = 0.0     # Home position (top)
    STEPS_PER_MM = 6400.0

    def __init__(self, port: int, address: int = 11, verbose: bool = False, mode: int = 1):
        self.port = f"COM{port}"
        self.address = address
        self.verbose = verbose
        self.mode = mode
        self.instrument = None
        self.running = False
        self.serial_connected = False
        self._current_position = 0.0
        self.motor_position = 0
        self.target_position = 0
        self._is_calibrated = False
        self._setup_logging()
        self._consecutive_errors = 0  # Add counter for consecutive errors
        self._max_consecutive_errors = 5  # Maximum allowed consecutive errors
        self._in_sequence = False  # Add flag for sequence mode

    def _setup_logging(self):
        """Setup logging for the Arduino controller."""
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)
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
            self.instrument.serial.timeout = 0.2  # Reduce timeout to prevent blocking
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = 'N'
            self.instrument.serial.stopbits = 1
            self.instrument.mode = minimalmodbus.MODE_RTU
            self.instrument.clear_buffers_before_each_transaction = True
            
            # Remove blocking sleep and try immediate connection test
            try:
                self.instrument.write_bit(3, 1)
                self.serial_connected = True
                self.logger.info(f"Connected to motor on {self.port}")
                
                result = self.instrument.read_bit(3, 1) 
                if result:
                    self.logger.info("Motor controller initialized")
                    self.running = True
                    
                    # Get initial position reading
                    try:
                        readings = self.instrument.read_registers(5, 2, functioncode=3)
                        raw_steps = self.assemble(readings[0], readings[1])
                        initial_position = round(raw_steps / self.STEPS_PER_MM, 5)
                        self._initial_offset = initial_position
                        #self.logger.info(f"Initial position offset set to: {initial_position}")
                    except Exception as e:
                        self.logger.error(f"Failed to get initial position: {e}")
                        self._initial_offset = 0
                    
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
                    readings = self.instrument.read_registers(5, 2, functioncode=3)
                    raw_steps = self.assemble(readings[0], readings[1])
                    # Convert to millimeters and apply offset from calibration
                    position = round((raw_steps / self.STEPS_PER_MM) - self._initial_offset, 5)
                    self.motor_position = position
                    self._consecutive_errors = 0  # Reset error counter on success
                    return float(position)
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            self.serial_connected = False
            self._consecutive_errors += 1
            
            # If too many consecutive errors, stop the controller
            if self._consecutive_errors >= self._max_consecutive_errors:
                self.logger.error("Too many consecutive errors, stopping motor controller")
                self.running = False
                self.serial_connected = False
                
            return None

    def start_calibration(self) -> bool:
        """Start the calibration process."""
        try:
            # Reset calibration flag so offset will be recalculated
            self._is_calibrated = False
            
            # Send calibration command
            self.instrument.write_register(2, ord('c'))
            time.sleep(1)
            self.instrument.write_bit(1, 1)
            self.serial_connected = True
            self.logger.info("Calibrating motor, please wait")
            return True
        except Exception as e:
            self.logger.error(f"Couldn't start calibration: {e}")
            self.serial_connected = False
            return False

    def check_calibrated(self) -> bool:
        """Check if motor is calibrated."""
        try:
            calibrated = self.instrument.read_bit(2, 1)
            self.serial_connected = True
            
            # First check if calibration is complete from controller
            if calibrated:
                if not self._is_calibrated:
                    # Now we know calibration is truly complete, wait for motor to settle
                    time.sleep(0.5)
                    
                    # Record position offset after calibration is complete
                    try:
                        readings = self.instrument.read_registers(5, 2, functioncode=3)
                        raw_steps = self.assemble(readings[0], readings[1])
                        calibration_position = round(raw_steps / self.STEPS_PER_MM, 5)
                        self._initial_offset = calibration_position
                        self.logger.info(f"Calibration complete - Position offset set to: {calibration_position}")
                    except Exception as e:
                        self.logger.error(f"Failed to get calibration position: {e}")
                        self._initial_offset = 0
                    
                    self._is_calibrated = True
                
            return bool(calibrated)
        except Exception as e:
            self.logger.error(f"Couldn't read calibration status")
            self.serial_connected = False
            return False

    def set_sequence_mode(self, enabled: bool):
        """Enable or disable sequence mode for continuous movement."""
        self._in_sequence = enabled
        self.logger.info(f"Sequence mode {'enabled' if enabled else 'disabled'}")
    
    def move_to(self, position: Union[int, float], wait: bool = False) -> Tuple[bool, float]:
        """Wrapper for set_position to maintain compatibility."""
        # During sequence mode, ignore "movement in progress" state
        if self._in_sequence:
            return self.set_position(position, wait=False)
        return self.set_position(position, wait)
        
    def set_position(self, position: Union[int, float], wait: bool = False) -> Tuple[bool, float]:
        """Set motor position."""
        if not self.running:
            return False, position

        try:
            position = float(position)
            actual_target = position

            if position > self.POSITION_MAX:
                self.logger.warning(f"Target position {position}mm exceeds maximum {self.POSITION_MAX}mm, limiting to maximum")
                actual_target = self.POSITION_MAX
                position = self.POSITION_MAX

            if self.mode == 2:  # Test mode
                self._current_position = position
                return True, actual_target

            # Only check calibration if not in sequence mode
            if not self._in_sequence:
                if not self.check_calibrated():
                    self.logger.error("Motor not calibrated")
                    return False, position

            # Convert to steps with proper rounding
            position_steps = int(round(position * self.STEPS_PER_MM))
            high, low = self.disassemble(position_steps)
            
            # Send position commands with minimal delay
            try:
                self.instrument.write_register(3, high)
                self.instrument.write_register(4, low)
                self.instrument.write_register(2, ord('x'))
                self.instrument.write_bit(1, 1)
                self.serial_connected = True
            except Exception as e:
                if self._in_sequence:
                    # Fail fast in sequence mode
                    raise
                self.logger.error(f"Failed to send position commands: {e}")
                return False, position

            if wait and not self._in_sequence:
                while True:
                    current = self.get_position()
                    if current is not None:
                        if abs(current + 2 - position) < 0.005:
                            break
                    time.sleep(0.1)

            return True, actual_target

        except Exception as e:
            self.logger.error(f"Error setting position: {e}")
            self.serial_connected = False
            return False, position

    def move_to_position(self, position: Union[int, float]) -> bool:
        """Alternative method for moving to position (for compatibility)."""
        return self.set_position(position)

    def stop_motor(self) -> bool:
        """Stop motor movement with retries."""
        max_retries = 10
        for attempt in range(max_retries):
            try:
                self.instrument.write_register(2, ord('s'))
                self.instrument.write_bit(1, 1)
                self.serial_connected = True
                self.logger.info("Motor stop command sent successfully")
                return True
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    self.logger.error(f"Failed to stop motor after {max_retries} attempts: {e}")
                    self.serial_connected = False
                    return False
                self.logger.warning(f"Stop attempt {attempt + 1} failed, retrying...")
                time.sleep(0.1)  # Short delay between retries

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

    def get_top_position(self) -> Optional[float]:
        """Get the top position of the motor."""
        try:
            readings = self.instrument.read_registers(7, 2, 3)
            raw_position = self.assemble(readings[0], readings[1])
            # Apply offset to top position reading
            position = raw_position - self._position_offset
            self.serial_connected = True
            return float(position)
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
        # Ensure we're working with a 32-bit integer
        combined = int(combined)
        # Extract high and low words
        high = (combined >> 16) & 0xFFFF
        low = combined & 0xFFFF
        return high, low

    def assemble(self, high, low):
        """Assemble high and low 16-bit words into a 32-bit value."""
        # Convert high word to signed 16-bit
        high = ctypes.c_int16(high).value
        # Combine into 32-bit value
        combined = (high << 16) | (low & 0xFFFF)
        return combined

    def set_position_offset(self, offset: float):
        """Set the position offset value."""
        self._position_offset = offset
        self.logger.info(f"Position offset set to {offset}")
        # Update current position with new offset
        if self.running:
            try:
                readings = self.instrument.read_registers(5, 2, functioncode=3)
                raw_position = self.assemble(readings[0], readings[1])
                self.motor_position = raw_position - offset
            except Exception as e:
                self.logger.error(f"Failed to update position after setting offset: {e}")
