"""
File: motor_worker.py
Description: Worker thread for motor control
"""

from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QMutex, QWaitCondition
import time
import logging
from typing import Optional, Union, Tuple, List, Dict, Any
import threading
import queue
from pathlib import Path

from controllers.motor_controller import MotorController
from utils.timing_logger import get_timing_logger  # Add import


class MockMotorController:
    """Mock motor controller for testing."""

    # Add step sizes as class constants
    STEP_SIZES = {
        'q': 50.0,   # +50mm
        'w': 10.0,   # +10mm
        'd': 1.0,    # +1mm
        'r': -1.0,   # -1mm
        'f': -10.0,  # -10mm
        'v': -50.0   # -50mm
    }

    def __init__(self):
        self.running = False
        self._position = 0.0  # Store position as float
        self.POSITION_MAX = 324.05  # Match real motor's maximum position
        self.POSITION_MIN = 0.0     # Home position (top)
        self.SPEED_MAX = 6501  # Match real controller speed limits
        self.SPEED_MIN = 0
        self._is_calibrated = False
        self.logger = logging.getLogger(__name__)
        self._ascending = False
        self._speed = 4000  # Default to medium speed
        self._initial_offset = 0.0  # Track position offset from calibration
        self._limits_enabled = True
        self.ACCEL_MAX = 23250  # Match real controller acceleration limits
        self.ACCEL_MIN = 0
        self._acceleration = 4000  # Default acceleration

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
        """Set mock motor position with optional limit checking."""
        try:
            position = float(position)
            actual_target = position

            # Apply limits only if enabled
            if self._limits_enabled:
                if position > self.POSITION_MAX:
                    self.logger.warning(
                        f"Target position {position}mm exceeds maximum {self.POSITION_MAX}mm, limiting to maximum")
                    actual_target = self.POSITION_MAX
                    position = self.POSITION_MAX
                elif position < self.POSITION_MIN:
                    position = self.POSITION_MIN
                    actual_target = self.POSITION_MIN

            self._position = position
            self.logger.info(
                f"Mock motor moving to position: {position}mm from bottom")
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
        self.logger.info(
            f"Mock motor calibrated at position {self.POSITION_MAX}mm")
        return True

    def check_calibrated(self) -> bool:
        """Return calibration state."""
        return self._is_calibrated

    def set_sequence_mode(self, enabled: bool):
        """Enable or disable sequence mode."""
        self._in_sequence = enabled
        self.logger.info(
            f"Mock motor sequence mode {'enabled' if enabled else 'disabled'}")

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

    def step_motor(self, step_char: str) -> bool:
        """Simulate stepping with optional limit checking."""
        try:
            if not self.running:
                return False

            step_size = self.STEP_SIZES.get(step_char)
            if step_size is None:
                self.logger.error(f"Invalid step command: {step_char}")
                return False

            # Calculate new position
            new_position = self._position + step_size

            # Limit to valid range only if enabled
            if self._limits_enabled:
                if new_position > self.POSITION_MAX:
                    new_position = self.POSITION_MAX
                    self.logger.warning(
                        "Step would exceed maximum position, limiting to maximum")
                elif new_position < self.POSITION_MIN:
                    new_position = self.POSITION_MIN
                    self.logger.warning(
                        "Step would exceed minimum position, limiting to minimum")

            self._position = new_position
            self.logger.info(
                f"Mock motor stepped by {step_size}mm to position {self._position}mm")
            return True

        except Exception as e:
            self.logger.error(f"Mock step_motor failed: {e}")
            return False

    def set_limits_enabled(self, enabled: bool):
        """Enable or disable motor position limits."""
        self._limits_enabled = enabled
        self.logger.info(
            f"Mock motor limits {'enabled' if enabled else 'disabled'}")

    def set_acceleration(self, accel: int) -> bool:
        """Set mock motor acceleration.

        Args:
            accel: Acceleration value (0-23250)

        Returns:
            bool: True if successful
        """
        try:
            if accel < self.ACCEL_MIN or accel > self.ACCEL_MAX:
                self.logger.error(f"Invalid acceleration value: {accel}")
                return False
            self._acceleration = accel
            self.logger.info(f"Mock motor acceleration set to {accel}")
            return True
        except Exception as e:
            self.logger.error(f"Mock motor set_acceleration failed: {e}")
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
        position_reached(float): Emitted when motor position reaches a target
        critical_error_occurred(str): Emitted when a critical error occurs
    """

    position_updated = pyqtSignal(float)
    movement_completed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    calibration_state_changed = pyqtSignal(bool)
    position_reached = pyqtSignal(float)
    critical_error_occurred = pyqtSignal(str)

    # Class variables for instance management
    _instance_count = 0
    _instance_lock = threading.Lock()
    _active_instances = set()  # Track active instances

    def __init__(self, port: int, update_interval: float = 0.1, mock: bool = False, timing_mode: bool = False):
        """Initialize worker.

        Args:
            port: COM port number
            update_interval: Position update interval in seconds (default 0.1)
            mock: Use mock controller for testing
            timing_mode: Enable timing logs for events
        """
        super().__init__()
        
        # Check if we already have an active instance
        with self._instance_lock:
            if self._instance_count > 0:
                # Clean up any existing instances
                for instance in list(self._active_instances):
                    try:
                        instance.cleanup()
                    except Exception:
                        pass
                self._active_instances.clear()
                self._instance_count = 0
            
            # Create new instance
            self._instance_count += 1
            self._instance_id = self._instance_count
            self._active_instances.add(self)

        self.port = port
        # Limit between 10ms and 1s
        self.update_interval = max(0.01, min(1.0, update_interval))

        # Setup logger first
        self.logger = logging.getLogger(__name__)
        # self.logger.info(f"Creating MotorWorker instance {self._instance_id} with mock={mock}")

        if mock:
            # self.logger.info("Creating MockMotorController")
            self.controller = MockMotorController()
            self._running = False  # Don't auto-start in mock mode
        else:
            # self.logger.info("Creating real MotorController")
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

        # Add command queue for prioritizing commands
        self._command_queue = queue.Queue()
        self._command_lock = threading.Lock()
        self._command_processing = False

        # Reduce position polling frequency when idle
        self._idle_update_interval = 0.1  # 100ms when idle
        self._active_update_interval = 0.05  # 50ms when active
        self._last_command_time = 0
        self._idle_timeout = 5.0  # Switch to idle mode after 5 seconds of no commands

        # Add position limits from controller
        self.max_position = self.controller.POSITION_MAX
        self.min_position = self.controller.POSITION_MIN

        self.timing_mode = timing_mode
        if timing_mode:
            # Make sure we get a valid logger
            self.timing_logger = get_timing_logger()
            if self.timing_logger is None:
                # If get_timing_logger returns None, create a fallback logger
                self.timing_logger = logging.getLogger('motor_timing')
                self.timing_logger.setLevel(logging.INFO)

                # Create a file handler if needed
                try:
                    log_dir = Path("C:/ssbubble/logs")
                    log_dir.mkdir(parents=True, exist_ok=True)
                    log_file = log_dir / \
                        f"motor_timing_{time.strftime('%Y%m%d_%H%M%S')}.log"
                    handler = logging.FileHandler(log_file)
                    formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(message)s',
                                                  datefmt='%Y-%m-%d %H:%M:%S')
                    handler.setFormatter(formatter)
                    self.timing_logger.addHandler(handler)
                except Exception as e:
                    self.logger.error(f"Failed to create timing logger: {e}")

            # Initialize timing variables
            self._last_command_time = 0
        else:
            self.timing_logger = None

        # Initialize target position tracking
        self._target_position = None
        self._current_position = 0.0
        self._previous_position = 0.0

        # Add position update timer
        self._position_timer = QTimer()
        self._position_timer.timeout.connect(self._check_position)
        self._position_timer.setInterval(
            int(update_interval * 1000))  # Convert to milliseconds

    def __del__(self):
        """Ensure instance count is decremented on deletion."""
        try:
            with self._instance_lock:
                MotorWorker._instance_count = max(
                    0, MotorWorker._instance_count - 1)
        except Exception:
            pass  # Ignore errors during deletion

    @classmethod
    def get_active_count(cls) -> int:
        """Get number of active motor worker instances."""
        return cls._instance_count

    def run(self):
        """Run the worker thread."""
        self._running = True
        self.logger.info(f"MotorWorker {self._instance_id} started")
        self.status_changed.emit("Motor worker started")

        # Main worker loop
        while self._running:
            if not self._paused:
                self._check_command_queue()

            # Adaptive sleep based on activity
            if time.time() - self._last_command_time > self._idle_timeout:
                # Idle mode - slower updates
                time.sleep(self._idle_update_interval)
            else:
                # Active mode - faster updates
                time.sleep(self._active_update_interval)

        self.logger.info(f"MotorWorker {self._instance_id} stopped")
        self.status_changed.emit("Motor worker stopped")

    def _check_command_queue(self):
        """Check if there are commands to process."""
        if self._command_processing:
            return  # Already processing commands

        if not self._command_queue.empty():
            with self._command_lock:
                if not self._command_processing:
                    self._command_processing = True
                    self._process_next_command()

    def _process_next_command(self):
        """Process the next command in the queue with improved error handling."""
        try:
            if self._command_queue.empty():
                self._command_processing = False
                return

            # Look for priority commands first
            priority_command = None
            for i in range(self._command_queue.qsize()):
                try:
                    cmd = list(self._command_queue.queue)[i]
                    if cmd.get('priority', False):
                        priority_command = self._command_queue.queue[i]
                        self._command_queue.queue.remove(priority_command)
                        break
                except:
                    pass  # Skip if there's an issue accessing a command

            # Use priority command if found, otherwise get next in queue
            command = priority_command if priority_command else self._command_queue.get()
            self._last_command_time = time.time()

            cmd_type = command.get('type')
            args = command.get('args', [])
            kwargs = command.get('kwargs', {})

            if cmd_type == 'move_to':
                position = args[0] if args else kwargs.get('position')
                if position is not None:
                    # For move commands, use the retry mechanism
                    self._pending_position = position
                    self._try_move()
            elif cmd_type == 'stop':
                success = self.controller.stop_motor()
                if not success:
                    # Retry stop command up to 3 times
                    for i in range(3):
                        time.sleep(0.05)  # Short delay between retries
                        if self.controller.stop_motor():
                            break
            elif cmd_type == 'to_top':
                success = self.controller.to_top()
                if not success and self.timing_mode:
                    self.timing_logger.info(
                        "MOTOR_COMMAND_FAILED - Command: to_top")
            elif cmd_type == 'to_bottom':
                success = self.controller.to_bottom()
                if not success and self.timing_mode:
                    self.timing_logger.info(
                        "MOTOR_COMMAND_FAILED - Command: to_bottom")
            elif cmd_type == 'calibrate':
                success = self.controller.start_calibration()
                if not success and self.timing_mode:
                    self.timing_logger.info(
                        "MOTOR_COMMAND_FAILED - Command: calibrate")
            elif cmd_type == 'set_speed':
                speed = args[0] if args else kwargs.get('speed')
                if speed is not None:
                    success = self.controller.set_speed(speed)
                    if not success and self.timing_mode:
                        self.timing_logger.info(
                            f"MOTOR_COMMAND_FAILED - Command: set_speed, Value: {speed}")

            # Process next command if any
            if not self._command_queue.empty():
                self._process_next_command()
            else:
                self._command_processing = False

        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            self._command_processing = False

    def stop(self):
        """Stop the worker."""
        self._cleanup_retry()  # Clean up any pending retries
        self._running = False
        self.wait()
        # self.logger.info(f"Stopped MotorWorker instance {self._instance_id}")

    def pause(self):
        """Pause position monitoring."""
        self._paused = True
        # self.status_changed.emit("Motor worker paused")

    def resume(self):
        """Resume position monitoring."""
        self._paused = False
        # self.status_changed.emit("Motor worker running")

    def set_sequence_mode(self, enabled: bool):
        """Enable or disable sequence mode."""
        self._in_sequence = enabled
        if self.controller and not isinstance(self.controller, MockMotorController):
            self.controller.set_sequence_mode(enabled)
        self.logger.info(
            f"Motor sequence mode {'enabled' if enabled else 'disabled'}")

    def move_to(self, position: Union[int, float]) -> bool:
        """Move motor to specified position with non-blocking retries."""
        if not self.running:
            self.error_occurred.emit("Motor not connected")
            return False

        try:
            position = float(position)
            # self.logger.info(
            #    f"Received move command to position: {position}mm")
            self._pending_position = position
            self._target_position = position  # Make sure target is set
            self._retry_count = 0

            # Log timing event when command is sent
            if self.timing_mode:
                self._last_command_time = time.time()  # Store command time
                # self.timing_logger.info(
                #
                #    f"MOTOR_COMMAND_SENT - Target Position: {position}mm")

            # Add command to queue for real motor
            self._command_queue.put({
                'type': 'move_to',
                'args': [position],
                'kwargs': {'position': position},
                'priority': True  # Mark position commands as high priority
            })

            # Start retry mechanism immediately
            self._try_move()

            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to move motor: {str(e)}")
            # self.logger.error(f"Exception in move_to: {str(e)}")
            return False

    def _try_move(self):
        """Attempt a single move command with automatic retries."""
        try:
            if self._pending_position is None:  # Check for None specifically, not falsy values
                return  # No pending position to process

            success, actual_target = self.controller.set_position(
                self._pending_position, wait=False)

            if success:
                self._target_position = actual_target
                # Log timing event if target was limited
                # if self.timing_mode and actual_target != self._pending_position:
                #    self.timing_logger.info(
                #        f"MOTOR_COMMAND_LIMITED - Original: {self._pending_position}mm, Limited To: {actual_target}mm")
                if actual_target != self._pending_position:
                    self.status_changed.emit(
                        f"Moving to limited position: {actual_target}mm")
                self._cleanup_retry()
            else:
                self._handle_move_failure("Move command failed")

        except Exception as e:
            # Log the error and retry
            # self.logger.error(
            #    f"Move attempt {self._retry_count + 1} failed: {str(e)}")
            self._handle_move_failure(str(e))

    def _handle_move_failure(self, error_msg: str = None):
        """Handle move command failure with automatic retries."""
        self._retry_count += 1

        # Continue retrying if in sequence mode or within retry limit
        if self._retry_count < self._max_retries:
            # Schedule next retry with exponential backoff (but cap at 500ms)
            retry_delay = min(10 * (2 ** (self._retry_count // 3)), 500)

            if self._retry_count % 5 == 0:  # Log only every 5 retries to avoid spam
                self.logger.warning(
                    f"Move attempt {self._retry_count} failed, retrying in {retry_delay}ms...")

            if not self._retry_timer:
                self._retry_timer = QTimer()
                self._retry_timer.setSingleShot(True)
                self._retry_timer.timeout.connect(self._try_move)

            self._retry_timer.start(retry_delay)  # Retry with backoff delay
        else:
            # Max retries reached
            if error_msg:
                self.error_occurred.emit(
                    f"Move failed after {self._max_retries} attempts: {error_msg}")
                # Log timing event for failure
                if self.timing_mode:
                    self.timing_logger.info(
                        f"MOTOR_COMMAND_FAILED - Position: {self._pending_position}mm, Attempts: {self._max_retries}")
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

            # Add calibration command to queue with high priority
            self._command_queue.put({
                'type': 'calibrate',
                'priority': True
            })

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
                        self.logger.info(
                            "Emergency stop executed successfully")
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
                            self.logger.warning(
                                f"Stop attempt {attempt + 1} failed, retrying...")
                    except Exception as e:
                        if attempt == max_retries - 1:  # Last attempt
                            raise
                        self.logger.warning(
                            f"Stop attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(0.1)  # Short delay between retries

                if success:
                    self._target_position = None
                    self.status_changed.emit("Motor emergency stopped")
                    self.logger.info("Emergency stop executed successfully")
                    # Reset calibration state
                    self._is_calibrated = False
                    self.calibration_state_changed.emit(False)
                else:
                    self.error_occurred.emit(
                        f"Emergency stop failed after {max_retries} attempts")
                    self.logger.error(
                        f"Emergency stop failed after {max_retries} attempts")

        except Exception as e:
            self.error_occurred.emit(f"Emergency stop failed: {str(e)}")
            self.logger.error(f"Emergency stop failed: {e}")

    def stop_movement(self):
        """Stop current movement without stopping the worker thread, with retries."""
        try:
            if self.running:
                # Handle mock mode
                if isinstance(self.controller, MockMotorController):
                    if self.controller.stop_motor():
                        self._target_position = None
                        self.status_changed.emit("Motor movement stopped")
                    else:
                        self.error_occurred.emit("Failed to stop mock motor")
                    return

                # Add stop command to queue for real motor
                self._command_queue.put({
                    'type': 'stop',
                    'priority': True  # Mark as high priority
                })

                # Reset target position
                self._target_position = None
                self.status_changed.emit("Motor movement stopping...")

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
                        self.logger.warning(
                            f"Ascent attempt {attempt + 1} failed, retrying...")
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    self.logger.warning(
                        f"Ascent attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.1)  # Short delay between retries

            return success

        except Exception as e:
            self.error_occurred.emit(f"Failed to move up: {str(e)}")
            return False

    def to_top(self) -> bool:
        """Move motor to top position."""
        if not self.running:
            self.error_occurred.emit("Motor not connected")
            return False

        try:
            # Handle mock mode
            if isinstance(self.controller, MockMotorController):
                if self.controller.to_top():
                    self.logger.info("Moving mock motor to top position")
                    return True
                return False

            # Add command to queue for real motor
            self._command_queue.put({
                'type': 'to_top'
            })

            self.logger.info("Moving motor to top position")
            self.status_changed.emit("Moving motor to top position")
            return True

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

            # Handle mock mode
            if isinstance(self.controller, MockMotorController):
                return self.controller.set_speed(speed)

            # Add speed command to queue
            self._command_queue.put({
                'type': 'set_speed',
                'args': [speed],
                'kwargs': {'speed': speed}
            })

            self.logger.info(f"Queued motor speed change to {speed}")
            return True

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
                # self.error_occurred.emit(
                #    "Failed to connect to motor controller")
                self.logger.error("Failed to connect to motor controller")
                return False

            # Start position update timer
            self._position_timer.start()

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

    def set_limits_enabled(self, enabled: bool):
        """Enable or disable motor position limits."""
        self.controller.set_limits_enabled(enabled)

    def cleanup(self):
        """Clean up resources and stop the worker."""
        try:
            # Stop any active timers
            if hasattr(self, '_calibration_check_timer') and self._calibration_check_timer:
                self._calibration_check_timer.stop()

            # Clear command queue
            while not self._command_queue.empty():
                try:
                    self._command_queue.get_nowait()
                except queue.Empty:
                    break

            # Stop the motor controller
            if self.controller:
                try:
                    self.controller.stop_motor()
                    self.controller.stop()  # This will reset the controller state
                except Exception as e:
                    self.logger.error(f"Error stopping motor controller: {e}")

            # Reset worker state
            self._is_calibrated = False
            self._target_position = None
            self._current_position = 0.0
            self._paused = False
            self._pause_updates = False
            self._command_in_progress = False
            self._in_sequence = False

            # Remove from active instances
            with self._instance_lock:
                if self in self._active_instances:
                    self._active_instances.remove(self)
                self._instance_count = max(0, self._instance_count - 1)

            self.logger.info("Motor worker cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Error during motor worker cleanup: {e}")
            # Still try to remove from active instances even if cleanup fails
            with self._instance_lock:
                if self in self._active_instances:
                    self._active_instances.remove(self)
                self._instance_count = max(0, self._instance_count - 1)

    def stop(self):
        """Stop the worker thread."""
        self._running = False
        self.cleanup()  # Ensure cleanup is called when stopping
        self.wait()  # Wait for thread to finish

    @classmethod
    def reset_instance_count(cls):
        """Reset the instance counter and clean up all active instances."""
        with cls._instance_lock:
            for instance in list(cls._active_instances):
                try:
                    instance.cleanup()
                except Exception:
                    pass
            cls._active_instances.clear()
            cls._instance_count = 0

    def to_bottom(self) -> bool:
        """Move motor to bottom position."""
        if not self.running:
            self.error_occurred.emit("Motor not connected")
            return False

        try:
            # Handle mock mode
            if isinstance(self.controller, MockMotorController):
                success = self.controller.set_position(
                    self.controller.POSITION_MAX)
                if success:
                    self.logger.info("Moving mock motor to bottom position")
                    return True
                return False

            # Add command to queue for real motor
            self._command_queue.put({
                'type': 'to_bottom'
            })

            self.logger.info("Moving motor to bottom position")
            self.status_changed.emit("Moving motor to bottom position")
            return True

        except Exception as e:
            self.error_occurred.emit(f"Failed to move to bottom: {str(e)}")
            return False

    def set_acceleration(self, accel: int) -> bool:
        """Set motor acceleration.

        Args:
            accel: Acceleration value (0-23250)

        Returns:
            bool: True if successful
        """
        try:
            if not self.running:
                self.error_occurred.emit("Motor not connected")
                return False

            # Validate acceleration range
            if accel < self.controller.ACCEL_MIN or accel > self.controller.ACCEL_MAX:
                self.logger.error(f"Invalid acceleration value: {accel}")
                return False

            success = self.controller.set_acceleration(accel)
            if success:
                self.logger.info(f"Motor acceleration set to {accel}")
                return True
            else:
                self.error_occurred.emit("Failed to set motor acceleration")
                return False

        except Exception as e:
            self.error_occurred.emit(f"Failed to set motor acceleration: {e}")
            return False

    def _check_position(self):
        """Check current motor position and emit updates."""
        # Skip position check if updates are paused
        if self._pause_updates:
            return

        if not self._paused and self.controller.running:
            try:
                position = self.controller.get_position()
                if position is not None:
                    self._current_position = position
                    self.position_updated.emit(position)

                    # Check if target position is reached
                    if self._target_position is not None:
                        if abs(position - self._target_position) < 0.1:  # Within 0.1mm tolerance
                            self.position_reached.emit(position)
                            self._target_position = None
            except Exception as e:
                # Check for critical error from controller
                if isinstance(e, MotorController.MotorCriticalError):
                    self.logger.critical(f"Critical motor error: {e}")
                    self.critical_error_occurred.emit(str(e))
                    self.stop()
                else:
                    self.logger.error(f"Error checking position: {e}")
