"""
File: src/controllers/motor_controller.py
"""

import minimalmodbus
import time
import logging
import ctypes
import threading
from typing import Optional, Union, Tuple


class MotorController:
    SPEED_MAX = 6501
    SPEED_MIN = 0
    ACCEL_MAX = 23250  # Add acceleration limits
    ACCEL_MIN = 0
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
        self._limits_enabled = True  # Add flag for motor limits
        self._error_state = False  # Add flag to track error state

        # Add locks for different operations
        self._modbus_lock = threading.Lock()  # Main communication lock
        self._command_lock = threading.Lock()  # High-priority command lock
        self._command_in_progress = False  # Flag for command priority

        # Add command prioritization flags
        self.last_position_read_time = 0
        self.position_read_interval = 0.1  # Minimum time between position reads

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
        self._error_state = False  # Reset error state on start
        try:
            if self.mode == 2:  # Test mode
                self.running = True
                self.serial_connected = True
                return True

            self.instrument = minimalmodbus.Instrument(self.port, self.address)
            # Configure Modbus RTU settings
            self.instrument.serial.baudrate = 115200
            self.instrument.serial.timeout = 0.005  # Reduce timeout to prevent blocking
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = 'N'
            self.instrument.serial.stopbits = 1
            self.instrument.mode = minimalmodbus.MODE_RTU
            self.instrument.clear_buffers_before_each_transaction = True

            # Remove blocking sleep and try immediate connection test
            try:
                self.instrument.write_bit(3, 1)
                self.serial_connected = True
                # self.logger.info(f"Connected to motor on {self.port}")

                result = self.instrument.read_bit(3, 1)
                if result:
                    self.logger.info("Motor controller initialized")
                    self.running = True

                    # Get initial position reading
                    try:
                        readings = self.instrument.read_registers(
                            5, 2, functioncode=3)
                        raw_steps = self.assemble(readings[0], readings[1])
                        initial_position = round(
                            raw_steps / self.STEPS_PER_MM, 5)
                        self._initial_offset = initial_position
                        # self.logger.info(f"Initial position offset set to: {initial_position}")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to get initial position: {e}")
                        self._initial_offset = 0

                    return True
                else:
                    self.logger.error("Motor controller not initialized")
                    return False

            except Exception as e:
                self.logger.error(
                    f"Failed to initialize motor controller: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to connect to motor: {e}")
            return False

    def get_position(self) -> Optional[float]:
        """Get current motor position."""
        # Skip position reading if high-priority command is in progress
        if self._command_in_progress:
            return self._current_position

        if not self.running:
            return None

        try:
            with self._modbus_lock:  # Use main lock for position reading
                readings = self.instrument.read_registers(5, 2, functioncode=3)
                raw_steps = self.assemble(readings[0], readings[1])
                position = round(
                    (raw_steps / self.STEPS_PER_MM) - self._initial_offset, 5)

                # Store previous position to detect when target is reached
                self._previous_position = self._current_position
                self._current_position = position

                self._consecutive_errors = 0
                return float(position)

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            self.serial_connected = False
            self._consecutive_errors += 1
            return self._current_position

    def start_calibration(self) -> bool:
        """Start the calibration process."""
        try:
            # Reset calibration flag so offset will be recalculated
            self._is_calibrated = False

            # Send calibration command
            self.instrument.write_register(2, ord('c'))
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
                        readings = self.instrument.read_registers(
                            5, 2, functioncode=3)
                        raw_steps = self.assemble(readings[0], readings[1])
                        calibration_position = round(
                            raw_steps / self.STEPS_PER_MM, 5)
                        # Calculate offset to make current position show POSITION_MAX
                        self._initial_offset = calibration_position - self.POSITION_MAX
                        self.logger.info(
                            f"Calibration complete - Position offset set to: {self._initial_offset}")

                        # Set calibration state
                        self._is_calibrated = True
                        # Return True to indicate successful calibration
                        return True

                    except Exception as e:
                        self.logger.error(
                            f"Failed to get calibration position: {e}")
                        self._initial_offset = 0
                        return False

            return bool(calibrated)
        except Exception as e:
            self.serial_connected = False
            return False

    def set_sequence_mode(self, enabled: bool):
        """Enable or disable sequence mode for continuous movement."""
        self._in_sequence = enabled
        self.logger.info(
            f"Sequence mode {'enabled' if enabled else 'disabled'}")

    def move_to(self, position: Union[int, float], wait: bool = False) -> Tuple[bool, float]:
        """Wrapper for set_position to maintain compatibility."""
        # During sequence mode, ignore "movement in progress" state
        if self._in_sequence:
            return self.set_position(position, wait=False)
        return self.set_position(position, wait)

    def set_position(self, position: Union[int, float], wait: bool = False) -> Tuple[bool, float]:
        """Set motor position with high priority."""
        if not self.running or self._error_state:
            return False, position

        try:
            position = float(position)
            actual_target = position

            # Apply limits if enabled
            if self._limits_enabled:
                if position > self.POSITION_MAX:
                    actual_target = self.POSITION_MAX
                    position = self.POSITION_MAX
                elif position < self.POSITION_MIN:
                    position = self.POSITION_MIN
                    actual_target = self.POSITION_MIN

            # Convert position to steps
            position_steps = int(
                round((self.POSITION_MAX - position) * self.STEPS_PER_MM))
            high, low = self.disassemble(position_steps)

            # Debug output
            self.logger.info(
                f"Setting position to {position}mm (steps: {position_steps})")
            self.logger.info(f"High word: {high}, Low word: {low}")

            # Use command lock for high-priority operations
            with self._command_lock:
                self._command_in_progress = True  # Set priority flag
                try:
                    with self._modbus_lock:  # Also acquire modbus lock
                        # Clear buffers once
                        self.instrument.serial.reset_input_buffer()
                        self.instrument.serial.reset_output_buffer()

                        # Send all commands in a single batch when possible
                        self.logger.info(
                            "Writing registers for command register & position command")
                        self.instrument.write_registers(
                            2, [ord('x'), high, low])

                    self.serial_connected = True
                    return True, actual_target

                finally:
                    self._command_in_progress = False  # Clear priority flag

        except Exception as e:
            self.logger.error(f"Error setting position: {e}")
            self.serial_connected = False
            return False, position

    def move_to_position(self, position: Union[int, float]) -> bool:
        """Alternative method for moving to position (for compatibility)."""
        return self.set_position(position)

    def stop_motor(self) -> bool:
        """Stop motor movement with retries."""
        if not self.running:
            return False

        # Acquire lock for command execution
        with self._modbus_lock:
            # Set command priority flag
            self._command_in_progress = True

            try:
                max_retries = 10
                for attempt in range(max_retries):
                    try:
                        # Increase timeout for stop command
                        original_timeout = self.instrument.serial.timeout
                        # self.instrument.serial.timeout = 0.5  # 500ms timeout

                        try:
                            self.instrument.write_register(2, ord('e'))
                            self.serial_connected = True
                            self.logger.info(
                                "Motor stop command sent successfully")
                            return True
                        finally:
                            # Restore original timeout
                            self.instrument.serial.timeout = original_timeout

                    except Exception as e:
                        if attempt == max_retries - 1:  # Last attempt
                            self.logger.error(
                                f"Failed to stop motor after {max_retries} attempts: {e}")
                            self.serial_connected = False
                            return False
                        self.logger.warning(
                            f"Stop attempt {attempt + 1} failed, retrying...")
                        time.sleep(0.005)  # Short delay between retries

                return False
            finally:
                # Always clear command priority flag
                self._command_in_progress = False

    def to_bottom(self) -> bool:
        """Move motor to bottom position."""
        if not self.running or self._error_state:  # Check error state
            self.logger.error(
                "Motor controller is in error state or not running")
            return False

        # Acquire lock for command execution
        with self._modbus_lock:
            # Set command priority flag
            self._command_in_progress = True

            try:
                # Increase timeout for this command
                original_timeout = self.instrument.serial.timeout
                self.instrument.serial.timeout = 0.5  # 500ms timeout

                try:
                    self.instrument.write_register(2, ord('b'))
                    self.serial_connected = True
                    return True
                finally:
                    # Restore original timeout
                    self.instrument.serial.timeout = original_timeout
            except Exception as e:
                self.logger.error(f"Couldn't move to bottom: {e}")
                self.serial_connected = False
                return False
            finally:
                # Always clear command priority flag
                self._command_in_progress = False

    def to_top(self) -> bool:
        """Move motor to top position."""
        if not self.running or self._error_state:  # Check error state
            self.logger.error(
                "Motor controller is in error state or not running")
            return False

        # Acquire lock for command execution
        with self._modbus_lock:
            # Set command priority flag
            self._command_in_progress = True

            try:
                # Increase timeout for this command
                original_timeout = self.instrument.serial.timeout
                self.instrument.serial.timeout = 0.5  # 500ms timeout

                try:
                    self.instrument.write_register(2, ord('t'))
                    self.serial_connected = True
                    return True
                finally:
                    # Restore original timeout
                    self.instrument.serial.timeout = original_timeout
            except Exception as e:
                self.logger.error(f"Couldn't move to top: {e}")
                self.serial_connected = False
                return False
            finally:
                # Always clear command priority flag
                self._command_in_progress = False

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
            self.serial_connected = True
        except Exception as e:
            self.logger.error(f"Couldn't reset motor: {e}")
            self.serial_connected = False
        finally:
            if hasattr(self, 'instrument') and self.instrument:
                self.instrument.serial.close()

    def stop(self):
        """Stop the motor controller and clean up."""
        self._error_state = True  # Set error state when stopping
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
                self.logger.error(
                    f"Failed to update position after setting offset: {e}")

    def set_speed(self, speed: int) -> bool:
        """Set motor speed via Modbus.

        Args:
            speed: Speed value (0-6500)

        Returns:
            bool: True if successful
        """
        try:
            # Validate speed range
            if speed < self.SPEED_MIN or speed > self.SPEED_MAX:
                self.logger.error(f"Invalid speed value: {speed}")
                return False

            # Write speed to register 9
            self.instrument.write_register(9, speed)
            # self.logger.info(f"Motor speed set to {speed}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to set motor speed: {e}")
            return False

    def step_motor(self, step_char: str) -> bool:
        """Step motor by predefined amount.

        Args:
            step_char: Command character:
                'q': +50mm
                'w': +10mm
                'd': +1mm
                'r': -1mm
                'f': -10mm
                'v': -50mm

        Returns:
            bool: True if command sent successfully
        """
        try:
            # Send step command
            self.instrument.write_register(2, ord(step_char))
            self.serial_connected = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to send step command: {e}")
            self.serial_connected = False
            return False

    def set_limits_enabled(self, enabled: bool):
        """Enable or disable motor position limits."""
        self._limits_enabled = enabled
        self.logger.info(
            f"Motor limits {'enabled' if enabled else 'disabled'}")

    def check_position_valid(self, position: float) -> bool:
        """Check if position is within valid range."""
        if not self._limits_enabled:
            return True
        return self.POSITION_MIN <= position <= self.POSITION_MAX

    def set_acceleration(self, accel: int) -> bool:
        """Set motor acceleration via Modbus.

        Args:
            accel: Acceleration value (0-23250)

        Returns:
            bool: True if successful
        """
        try:
            # Validate acceleration range
            if accel < self.ACCEL_MIN or accel > self.ACCEL_MAX:
                self.logger.error(f"Invalid acceleration value: {accel}")
                return False

            # Write acceleration to register 10
            self.instrument.write_register(10, accel)
            return True

        except Exception as e:
            self.logger.error(f"Failed to set motor acceleration: {e}")
            return False

    def get_velocity(self) -> Optional[float]:
        """Get current motor velocity from registers 11 (high) and 12 (low).

        Returns:
            float: Current velocity or None if read fails
        """
        if not self.running:
            return None

        try:
            # Skip velocity reading if high-priority command is in progress
            if self._command_in_progress:
                return None

            with self._modbus_lock:  # Use main lock for velocity reading
                # Read both registers
                readings = self.instrument.read_registers(
                    11, 2, functioncode=3)
                # Assemble the velocity value from high and low bytes
                velocity = self.assemble(readings[0], readings[1])
                self.serial_connected = True
                return float(velocity)
        except Exception as e:
            self.logger.error(f"Failed to read motor velocity: {e}")
            self.serial_connected = False
            return None
