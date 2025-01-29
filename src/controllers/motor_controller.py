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
    POSITION_MAX = 91.10  # Maximum downward position
    POSITION_MIN = 0.0     # Home position (top)

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
            self.instrument.serial.timeout = 0.5
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
                    
                    # Get initial position reading
                    try:
                        readings = self.instrument.read_registers(5, 2, functioncode=3)
                        raw_steps = self.assemble(readings[0], readings[1])
                        initial_position = round(raw_steps / 25600.0, 5)
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
                    position = round((raw_steps / 25600.0) - self._initial_offset, 5)
                    self.motor_position = position
                    return float(position)
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
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
                        calibration_position = round(raw_steps / 25600.0, 5)
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

    def set_position(self, position: Union[int, float], wait: bool = False) -> Tuple[bool, float]:
        """Set motor position.
        
        Returns:
            Tuple[bool, float]: (success, actual_target_position)
        """
        if not self.running:
            return False, position

        try:
            position = float(position)
            actual_target = position  # Store the actual target that will be used
            
            if position > self.POSITION_MAX:
                self.logger.warning(f"Target position {position}mm exceeds maximum {self.POSITION_MAX}mm, limiting to maximum")
                actual_target = self.POSITION_MAX
                position = self.POSITION_MAX

            if self.mode == 2:  # Test mode
                self._current_position = position
                return True, actual_target

            if self.check_calibrated():
                # Add static offset to target position
                adjusted_position = position
                # Convert from mm to microsteps with proper rounding
                position_steps = int(round(adjusted_position * 25600.0))
                
                # Convert position to high and low words
                high, low = self.disassemble(position_steps)
                
                # Send the position to the motor
                self.instrument.write_register(3, high)
                self.instrument.write_register(4, low)
                self.instrument.write_register(2, ord('x'))
                self.instrument.write_bit(1, 1)
                self.serial_connected = True

                if wait:
                    while True:
                        current = self.get_position()
                        if current is not None:
                            current_adjusted = current + 2
                            self.logger.info(f"Current: {current}, Target: {position}, Diff: {abs(current_adjusted - position)}")
                            if abs(current_adjusted - position) < 0.005:
                                break
                        time.sleep(0.1)

                return True, actual_target
            else:
                self.logger.error("Motor not calibrated")
                return False, position

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
