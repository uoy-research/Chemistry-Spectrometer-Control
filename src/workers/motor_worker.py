"""
File: motor_worker.py
Description: Worker thread for motor control
"""

from PyQt6.QtCore import QThread, pyqtSignal, QTimer
import time
import logging
from typing import Optional, Union, Tuple

from controllers.motor_controller import MotorController


class MockMotorController:
    """Mock motor controller for testing."""
    def __init__(self):
        self.running = False
        self._position = 0.0  # Store position as float
        self.POSITION_MAX = 364.40  # Match real motor's maximum position
        self.POSITION_MIN = 0.0     # Home position (top)
        self.SPEED_MAX = 6501  # Match real controller speed limits
        self.SPEED_MIN = 0
        self._is_calibrated = False
        self.logger = logging.getLogger(__name__)
        self._ascending = False
        self._speed = 4000  # Default to medium speed
        self._initial_offset = 0.0  # Track position offset from calibration

    def start(self) -> bool:
        """Start the mock controller."""
        self.running = True
        self.logger.info("Mock motor controller started")
        return True

    def stop(self):
        self.running = False

    def get_position(self) -> float:
        """Get current position relative to bottom."""
        if self._ascending:
            # Move up slowly (increase position relative to bottom)
            new_position = min(self.POSITION_MAX, self._position + 0.1)
            if new_position == self.POSITION_MAX:
                self._ascending = False  # Stop ascending at top
            self._position = new_position
        return self._position

    def set_position(self, position: Union[int, float], wait: bool = False) -> Tuple[bool, float]:
        """Set position relative to bottom.
        
        Args:
            position: Target position from bottom (0.0 = bottom, POSITION_MAX = top)
            wait: Ignored in mock mode
            
        Returns:
            Tuple[bool, float]: (success, actual_target_position)
        """
        try:
            position = float(position)
            actual_target = position

            # Limit position to valid range
            if position > self.POSITION_MAX:
                self.logger.warning(f"Target position {position}mm exceeds maximum {self.POSITION_MAX}mm, limiting to maximum")
                actual_target = self.POSITION_MAX
                position = self.POSITION_MAX
            elif position < self.POSITION_MIN:
                position = self.POSITION_MIN
                actual_target = self.POSITION_MIN
                
            self._position = position
            self.logger.info(f"Mock motor moving to position: {position}mm from bottom")
            return True, actual_target
            
        except (ValueError, TypeError):
            return False, 0.0

    def stop_motor(self) -> bool:
        """Implement stop functionality."""
        self._ascending = False  # Stop any ascent movement
        self._position = self._position  # Stop at current position
        self.logger.info("Mock motor stopped")
        return True

    def start_calibration(self) -> bool:
        """Implement calibration start - sets current position to POSITION_MAX."""
        self._position = self.POSITION_MAX  # Set to maximum (calibration point)
        self._is_calibrated = True
        self.logger.info(f"Mock motor calibrated at position {self.POSITION_MAX}mm")
        return True

    def check_calibrated(self) -> bool:
        """Return calibration state."""
        return self._is_calibrated

    def set_sequence_mode(self, enabled: bool):
        """Enable or disable sequence mode."""
        self._in_sequence = enabled
        self.logger.info(f"Mock motor sequence mode {'enabled' if enabled else 'disabled'}")

    def to_top(self) -> bool:
        """Move motor to top position (POSITION_MAX)."""
        try:
            self._position = self.POSITION_MAX
            self.logger.info("Mock motor moving to top position")
            return True
        except Exception as e:
            self.logger.error(f"Mock motor to_top failed: {e}")
            return False

    def ascent(self) -> bool:
        """Start slow ascent movement (increasing position towards POSITION_MAX)."""
        try:
            self._ascending = True
            self.logger.info("Mock motor starting ascent")
            return True
        except Exception as e:
            self.logger.error(f"Mock motor ascent failed: {e}")
            return False

    def set_speed(self, speed: int) -> bool:
        """Set mock motor speed.
        
        Args:
            speed: Speed value (0-6501)
            
        Returns:
            bool: True if successful
        """
        try:
            if speed < self.SPEED_MIN or speed > self.SPEED_MAX:
                self.logger.error(f"Invalid speed value: {speed}")
                return False
            self._speed = speed
            self.logger.info(f"Mock motor speed set to {speed}")
            return True
        except Exception as e:
            self.logger.error(f"Mock motor set_speed failed: {e}")
            return False


class MotorWorker(QThread):
    """
    Worker thread for handling motor control.

    Signals:
        position_updated(float): Emitted when motor position changes
        movement_completed(bool): Emitted when movement is complete
        error_occurred(str): Emitted when an error occurs
        status_changed(str): Emitted when worker status changes
        calibration_state_changed(bool): Emitted when motor calibration state changes
    """

    position_updated = pyqtSignal(float)
    movement_completed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    calibration_state_changed = pyqtSignal(bool)

    # Add class variable to track instances
    _instance_count = 0

    def __init__(self, port: int, update_interval: float = 0.1, mock: bool = False):
        """Initialize worker.
        
        Args:
            port: COM port number
            update_interval: Position update interval in seconds (default 0.1)
            mock: Use mock controller for testing
        """
        super().__init__()
        
        # Increment instance counter
        MotorWorker._instance_count += 1
        self._instance_id = MotorWorker._instance_count

        self.port = port
        self.update_interval = max(0.01, min(1.0, update_interval))  # Limit between 10ms and 1s
        
        # Setup logger first
        self.logger = logging.getLogger(__name__)
        #self.logger.info(f"Creating MotorWorker instance {self._instance_id} with mock={mock}")

        if mock:
            #self.logger.info("Creating MockMotorController")
            self.controller = MockMotorController()
            self._running = False  # Don't auto-start in mock mode
        else:
            #self.logger.info("Creating real MotorController")
            self.controller = MotorController(port=port)

        self._running = False
        self._paused = False
        self._target_position: Optional[float] = None
        self._current_position: Optional[float] = None
        self._is_calibrated = False
        self._pause_updates = False
        self._in_sequence = False
        self._retry_timer = None
        self._retry_count = 0
        self._pending_position = None
        self._max_retries = 50

    def __del__(self):
        """Destructor to track worker cleanup."""
        MotorWorker._instance_count -= 1
        #self.logger.info(f"Destroying MotorWorker instance {self._instance_id}. Active instances: {MotorWorker._instance_count}")

    @classmethod
    def get_active_count(cls) -> int:
        """Get number of active motor worker instances."""
        return cls._instance_count

    def run(self):
        """Main worker loop."""
        if isinstance(self.controller, MockMotorController):
            self._running = True
            self.logger.info("Mock motor worker thread running")
            self.status_changed.emit("Mock motor worker running")
            
            # Keep the thread alive for mock mode
            while self._running:
                if not self._paused and not self._pause_updates:
                    # Remove the negative sign here
                    self.position_updated.emit(float(self.controller.get_position()))
                time.sleep(self.update_interval)
            
            self.logger.info("Mock motor worker thread stopped")
            return

        # Real motor code...
        self.status_changed.emit("Starting motor worker...")

        if not self.controller.start():
            self.error_occurred.emit("Failed to connect to motor")
            return

        self._running = True
        self.status_changed.emit("Motor worker running")

        while self._running:
            if not self._paused and not self._pause_updates:
                # Get current position
                position = self.controller.get_position()
                
                # Check if controller is still running
                if not self.controller.running:
                    self.logger.error("Motor controller stopped due to connection issues")
                    self._running = False
                    self.status_changed.emit("Motor disconnected")
                    break
                    
                if position is not None:
                    if position != self._current_position:
                        self._current_position = position
                        # Remove the negative sign here
                        self.position_updated.emit(float(position))

                    # Check if target reached
                    if self._target_position is not None:
                        # Remove position inversion here
                        current_adjusted = position
                        if abs(current_adjusted - self._target_position) < 0.005:
                            self._target_position = None
                            self.movement_completed.emit(True)
                else:
                    self.logger.error("Failed to get motor position")

            time.sleep(self.update_interval)

        self.controller.stop()
        self.status_changed.emit("Motor worker stopped")

    def stop(self):
        """Stop the worker."""
        self._cleanup_retry()  # Clean up any pending retries
        self._running = False
        self.wait()
        #self.logger.info(f"Stopped MotorWorker instance {self._instance_id}")

    def pause(self):
        """Pause position monitoring."""
        self._paused = True
        #self.status_changed.emit("Motor worker paused")

    def resume(self):
        """Resume position monitoring."""
        self._paused = False
        #self.status_changed.emit("Motor worker running")

    def set_sequence_mode(self, enabled: bool):
        """Enable or disable sequence mode."""
        self._in_sequence = enabled
        if self.controller and not isinstance(self.controller, MockMotorController):
            self.controller.set_sequence_mode(enabled)
        self.logger.info(f"Motor sequence mode {'enabled' if enabled else 'disabled'}")

    def move_to(self, position: Union[int, float]) -> bool:
        """Move motor to specified position with non-blocking retries."""
        if not self.running:
            self.error_occurred.emit("Motor not connected")
            return False

        try:
            position = float(position)
            self._pending_position = position
            self._retry_count = 0
            
            # Log sequence mode state
            self.logger.info(f"Move command received. Sequence mode: {self._in_sequence}")
            
            # Handle mock mode differently
            if isinstance(self.controller, MockMotorController):
                success, actual_target = self.controller.set_position(position)
                if success:
                    self._target_position = actual_target
                    self.position_updated.emit(actual_target)  # Update UI immediately
                    if actual_target != position:
                        self.status_changed.emit(f"Moving to limited position: {actual_target}mm")
                    return True
                else:
                    self.error_occurred.emit("Failed to move mock motor")
                    return False
            
            # Start retry attempt for real motor
            self._try_move()
            return True

        except (ValueError, TypeError):
            self.error_occurred.emit("Invalid position value")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Failed to move motor: {str(e)}")
            return False

    def _try_move(self):
        """Attempt a single move command."""
        try:
            success, actual_target = self.controller.set_position(self._pending_position, wait=False)
            if success:
                self._target_position = actual_target
                if actual_target != self._pending_position:
                    self.status_changed.emit(f"Moving to limited position: {actual_target}mm")
                self._cleanup_retry()
            else:
                self._handle_move_failure("Move command failed")

        except Exception as e:
            # Log the error and retry
            self.logger.error(f"Move attempt {self._retry_count + 1} failed: {str(e)}")
            self._handle_move_failure(str(e))

    def _handle_move_failure(self, error_msg: str = None):
        """Handle move command failure."""
        self._retry_count += 1
        
        # Continue retrying if in sequence mode or within retry limit
        if self._retry_count < self._max_retries:
            # Schedule next retry
            if not self._retry_timer:
                self._retry_timer = QTimer()
                self._retry_timer.setSingleShot(True)
                self._retry_timer.timeout.connect(self._try_move)
            
            self.logger.warning(f"Move attempt {self._retry_count} failed, retrying in 100ms...")
            self._retry_timer.start(100)  # 100ms delay between retries
        else:
            # Max retries reached
            if error_msg:
                self.error_occurred.emit(f"Move failed after {self._max_retries} attempts: {error_msg}")
            self._cleanup_retry()

    def _cleanup_retry(self):
        """Clean up retry mechanism."""
        if self._retry_timer:
            self._retry_timer.stop()
            self._retry_timer = None
        self._retry_count = 0
        self._pending_position = None

    def calibrate(self) -> bool:
        """Calibrate the motor."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False
        
        try:
            self._pause_updates = True  # Pause position updates
            # Reset target position when starting calibration
            self._target_position = None
            self.status_changed.emit("Starting motor calibration...")

            # Handle mock mode differently
            if isinstance(self.controller, MockMotorController):
                if self.controller.start_calibration():
                    self._is_calibrated = True
                    self.calibration_state_changed.emit(True)
                    self.status_changed.emit("Motor calibration complete")
                    self._pause_updates = False
                    # Emit position update for UI
                    self.position_updated.emit(0.0)
                    self.movement_completed.emit(True)
                    return True
                return False

            # Real motor calibration code...
            if self.controller.start_calibration():
                # Start a timer to check calibration status
                self._calibration_check_timer = QTimer()
                self._calibration_check_timer.setInterval(200)
                self._calibration_attempts = 0
                self._max_calibration_attempts = 100

                def check_calibration():
                    try:
                        if self.controller.check_calibrated():
                            self._calibration_check_timer.stop()
                            self.status_changed.emit("Motor calibration complete")
                            self._is_calibrated = True
                            # Set target position to 0 after calibration
                            self._target_position = 0
                            self.calibration_state_changed.emit(True)
                            self.movement_completed.emit(True)
                            self._pause_updates = False  # Resume position updates
                        else:
                            self._calibration_attempts += 1
                            if self._calibration_attempts >= self._max_calibration_attempts:
                                self._calibration_check_timer.stop()
                                self.error_occurred.emit("Calibration timed out")
                                self._is_calibrated = False
                                self.calibration_state_changed.emit(False)
                                self.movement_completed.emit(False)
                                self._pause_updates = False  # Resume position updates
                    except Exception as e:
                        self._calibration_check_timer.stop()
                        self.error_occurred.emit(f"Calibration error: {str(e)}")
                        self._is_calibrated = False
                        self.calibration_state_changed.emit(False)
                        self.movement_completed.emit(False)
                        self._pause_updates = False  # Resume position updates

                self._calibration_check_timer.timeout.connect(check_calibration)
                self._calibration_check_timer.start()
                return True
            else:
                self._pause_updates = False
                self.error_occurred.emit("Failed to start calibration")
                return False

        except Exception as e:
            self._pause_updates = False
            self.error_occurred.emit(f"Calibration error: {str(e)}")
            return False

    def check_calibrated(self) -> bool:
        """Check if motor is calibrated."""
        if not self.controller.running:
            return False
        
        try:
            is_calibrated = self.controller.check_calibrated()
            if is_calibrated != self._is_calibrated:
                self._is_calibrated = is_calibrated
                self.calibration_state_changed.emit(is_calibrated)
                if is_calibrated:
                    self.status_changed.emit("Motor calibration complete")
                else:
                    self.status_changed.emit("Motor needs calibration")
            return is_calibrated
        except Exception as e:
            self.error_occurred.emit(f"Failed to check calibration: {str(e)}")
            return False

    def emergency_stop(self):
        """Execute emergency stop with retries."""
        try:
            if self.running:
                # Handle mock mode
                if isinstance(self.controller, MockMotorController):
                    if self.controller.stop_motor():
                        self._target_position = None
                        self.status_changed.emit("Motor emergency stopped")
                        self.logger.info("Emergency stop executed successfully")
                        # Reset calibration state
                        self._is_calibrated = False
                        self.calibration_state_changed.emit(False)
                    else:
                        self.error_occurred.emit("Emergency stop failed")
                    return

                # Real motor emergency stop code...
                success = False
                max_retries = 10
                
                for attempt in range(max_retries):
                    try:
                        if self.controller.stop_motor():
                            success = True
                            break
                        else:
                            self.logger.warning(f"Stop attempt {attempt + 1} failed, retrying...")
                    except Exception as e:
                        if attempt == max_retries - 1:  # Last attempt
                            raise
                        self.logger.warning(f"Stop attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(0.1)  # Short delay between retries
                
                if success:
                    self._target_position = None
                    self.status_changed.emit("Motor emergency stopped")
                    self.logger.info("Emergency stop executed successfully")
                    # Reset calibration state
                    self._is_calibrated = False
                    self.calibration_state_changed.emit(False)
                else:
                    self.error_occurred.emit(f"Emergency stop failed after {max_retries} attempts")
                    self.logger.error(f"Emergency stop failed after {max_retries} attempts")
                
        except Exception as e:
            self.error_occurred.emit(f"Emergency stop failed: {str(e)}")
            self.logger.error(f"Emergency stop failed: {e}")

    def stop_movement(self):
        """Stop current movement without stopping the worker thread, with retries."""
        try:
            if self.running:
                success = False
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        if self.controller.stop_motor():
                            success = True
                            self._target_position = None
                            self.status_changed.emit("Motor movement stopped")
                            break
                        else:
                            self.logger.warning(f"Stop attempt {attempt + 1} failed, retrying...")
                    except Exception as e:
                        if attempt == max_retries - 1:  # Last attempt
                            raise
                        self.logger.warning(f"Stop attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(0.1)  # Short delay between retries
                
                if not success:
                    self.error_occurred.emit(f"Failed to stop motor after {max_retries} attempts")
                    self.logger.error(f"Failed to stop motor after {max_retries} attempts")
                
        except Exception as e:
            self.error_occurred.emit(f"Failed to stop motor: {str(e)}")
            self.logger.error(f"Failed to stop motor: {e}")

    def ascent(self) -> bool:
        """Move motor up with retries."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False
        
        try:
            success = False
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    if self.controller.ascent():
                        success = True
                        self.status_changed.emit("Moving motor up")
                        break
                    else:
                        self.logger.warning(f"Ascent attempt {attempt + 1} failed, retrying...")
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    self.logger.warning(f"Ascent attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.1)  # Short delay between retries
            
            return success

        except Exception as e:
            self.error_occurred.emit(f"Failed to move up: {str(e)}")
            return False

    def to_top(self) -> bool:
        """Move motor to top position with retries."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False
        
        try:
            success = False
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    if self.controller.to_top():
                        success = True
                        self.status_changed.emit("Moving motor to top")
                        break
                    else:
                        self.logger.warning(f"To top attempt {attempt + 1} failed, retrying...")
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    self.logger.warning(f"To top attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.1)  # Short delay between retries
            
            return success

        except Exception as e:
            self.error_occurred.emit(f"Failed to move to top: {str(e)}")
            return False

    def set_speed(self, speed: int) -> bool:
        """Set motor speed.
        
        Args:
            speed: Speed value (0-1000)
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.running:
                self.error_occurred.emit("Motor not connected")
                return False
            
            return self.controller.set_speed(speed)
        
        except Exception as e:
            self.error_occurred.emit(f"Failed to set motor speed: {str(e)}")
            return False

    def home(self):
        """Move motor to home position."""
        return self.move_to(0)

    @property
    def running(self) -> bool:
        """Get the running state of the worker."""
        return self._running

    def get_current_position(self) -> Optional[float]:
        """Get the current motor position.
        
        Returns:
            float: Current position or None if not available
        """
        if not self.running:
            return None
        return self._current_position

    def start(self) -> bool:
        """Start the worker thread.
        
        Returns:
            bool: True if successfully started, False otherwise
        """
        try:
            self.logger.info("Starting motor worker...")
            
            # First try to connect the controller
            if not self.controller.start():
                self.error_occurred.emit("Failed to connect to motor controller")
                self.logger.error("Failed to connect to motor controller")
                return False
            
            # Start the thread regardless of mock/real mode
            super().start()  # Start the QThread
            return True
        
        except Exception as e:
            self.error_occurred.emit(f"Failed to start motor worker: {str(e)}")
            self.logger.error(f"Failed to start motor worker: {e}")
            return False

    def step_motor(self, step_char: str) -> bool:
        """Step motor by predefined amount.
        
        Args:
            step_char: Step command character (q,w,e,r,f,v)
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.running:
                self.error_occurred.emit("Motor not connected")
                return False
                
            success = self.controller.step_motor(step_char)
            if success:
                self.status_changed.emit(f"Stepping motor")
                return True
            else:
                self.error_occurred.emit("Failed to step motor")
                return False
                
        except Exception as e:
            self.error_occurred.emit(f"Error stepping motor: {str(e)}")
            return False
