"""
File: motor_worker.py
Description: Worker thread for motor control
"""

from PyQt6.QtCore import QThread, pyqtSignal, QTimer
import time
import logging
from typing import Optional, Union

from controllers.motor_controller import MotorController


class MockMotorController:
    """Mock motor controller for testing."""
    def __init__(self):
        self.running = False
        self._position = 0.0  # Store position as float
        self.POSITION_MAX = 1000.0
        self.POSITION_MIN = 0.0

    def start(self) -> bool:
        self.running = True
        return True

    def stop(self):
        self.running = False

    def get_position(self) -> float:
        return self._position

    def set_position(self, position: Union[int, float], wait: bool = False) -> bool:
        """Set position with float support."""
        try:
            position = float(position)  # Convert to float
            if not (self.POSITION_MIN <= position <= self.POSITION_MAX):
                return False
            self._position = position
            return True
        except (ValueError, TypeError):
            return False

    def stop_motor(self) -> bool:
        return True


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

    def __init__(self, port: int, update_interval: float = 0.1, mock: bool = False):
        """Initialize worker.
        
        Args:
            port: COM port number
            update_interval: Position update interval in seconds
            mock: Use mock controller for testing
        """
        super().__init__()

        self.port = port
        self.update_interval = update_interval
        if mock:
            self.controller = MockMotorController()
            self._running = False  # Don't auto-start in mock mode
        else:
            self.controller = MotorController(port=port)

        self._running = False
        self._paused = False
        self._target_position: Optional[float] = None
        self._current_position: Optional[float] = None
        self._is_calibrated = False

        self.logger = logging.getLogger(__name__)

    def run(self):
        """Main worker loop."""
        # Don't actually run if in mock mode
        if isinstance(self.controller, MockMotorController):
            self._running = True
            return

        self.status_changed.emit("Starting motor worker...")

        if not self.controller.start():
            self.error_occurred.emit("Failed to connect to motor")
            return

        self._running = True
        self.status_changed.emit("Motor worker running")

        while self._running:
            if not self._paused:
                # Get current position
                position = self.controller.get_position()
                if position is not None:
                    if position != self._current_position:
                        self._current_position = position
                        # Invert position value for UI display
                        self.position_updated.emit(-float(position))

                    # Check if target reached
                    if self._target_position is not None:
                        # Add initial offset to current position for comparison
                        current_adjusted = -position #self.controller._initial_offset - position
                        #self.logger.info(f"Current: {current_adjusted}, Target: {self._target_position}")
                        if abs(current_adjusted - self._target_position) < 0.005:
                            self._target_position = None
                            self.movement_completed.emit(True)
                else:
                    self.error_occurred.emit("Failed to get motor position")

                time.sleep(self.update_interval)

        self.controller.stop()
        self.status_changed.emit("Motor worker stopped")

    def stop(self):
        """Stop the worker."""
        self._running = False
        self.wait()

    def pause(self):
        """Pause position monitoring."""
        self._paused = True
        self.status_changed.emit("Motor worker paused")

    def resume(self):
        """Resume position monitoring."""
        self._paused = False
        self.status_changed.emit("Motor worker running")

    def move_to(self, position: Union[int, float]) -> bool:
        """Move motor to specified position."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False

        if self._target_position is not None:
            self.error_occurred.emit("Movement already in progress")
            return False

        try:
            position = float(position)  # Ensure position is float
            if self.controller.set_position(position, wait=False):
                self._target_position = position
                return True
            return False
        except (ValueError, TypeError):
            self.error_occurred.emit("Invalid position value")
            return False

    def calibrate(self) -> bool:
        """Calibrate the motor."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False
        
        try:
            self.status_changed.emit("Starting motor calibration...")
            if self.controller.start_calibration():
                # Start a timer to check calibration status
                self._calibration_check_timer = QTimer()
                self._calibration_check_timer.setInterval(200)  # Check every 200ms
                self._calibration_attempts = 0
                self._max_calibration_attempts = 25  # 5 seconds total

                def check_calibration():
                    try:
                        if self.controller.check_calibrated():
                            self._calibration_check_timer.stop()
                            self.status_changed.emit("Motor calibration complete")
                            self._is_calibrated = True
                            self.calibration_state_changed.emit(True)
                            self.movement_completed.emit(True)
                        else:
                            self._calibration_attempts += 1
                            if self._calibration_attempts >= self._max_calibration_attempts:
                                self._calibration_check_timer.stop()
                                self.error_occurred.emit("Calibration timed out")
                                self._is_calibrated = False
                                self.calibration_state_changed.emit(False)
                                self.movement_completed.emit(False)
                    except Exception as e:
                        self._calibration_check_timer.stop()
                        self.error_occurred.emit(f"Calibration error: {str(e)}")
                        self._is_calibrated = False
                        self.calibration_state_changed.emit(False)
                        self.movement_completed.emit(False)

                self._calibration_check_timer.timeout.connect(check_calibration)
                self._calibration_check_timer.start()
                return True
            else:
                self.error_occurred.emit("Failed to start calibration")
                return False
        except Exception as e:
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
            return is_calibrated
        except Exception as e:
            self.error_occurred.emit(f"Failed to check calibration: {str(e)}")
            return False

    def emergency_stop(self):
        """Execute emergency stop."""
        try:
            if self.running:
                # Stop any current movement
                self.controller.stop_motor()
                self._target_position = None
                # Signal that we've stopped
                self.status_changed.emit("Motor emergency stopped")
                self.logger.info("Emergency stop executed")
        except Exception as e:
            self.error_occurred.emit(f"Emergency stop failed: {str(e)}")
            self.logger.error(f"Emergency stop failed: {e}")

    def stop_movement(self):
        """Stop current movement without stopping the worker thread."""
        try:
            if self.running:
                self.controller.stop_motor()
                self._target_position = None
                self.status_changed.emit("Motor movement stopped")
        except Exception as e:
            self.error_occurred.emit(f"Failed to stop motor: {str(e)}")
            self.logger.error(f"Failed to stop motor: {e}")

    def ascent(self) -> bool:
        """Move motor up."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False
        
        try:
            if self.controller.ascent():
                self.status_changed.emit("Moving motor up")
                return True
            return False
        except Exception as e:
            self.error_occurred.emit(f"Failed to move up: {str(e)}")
            return False

    def to_top(self) -> bool:
        """Move motor to top position."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False
        
        try:
            if self.controller.to_top():
                self.status_changed.emit("Moving motor to top")
                return True
            return False
        except Exception as e:
            self.error_occurred.emit(f"Failed to move to top: {str(e)}")
            return False

    def set_speed(self, speed: int):
        """Set motor speed."""
        if not self.controller.running:
            self.error_occurred.emit("Motor not connected")
            return False
        return self.controller.set_speed(speed)

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
            # First try to connect the controller
            if not self.controller.start():
                return False
            
            # If controller connected successfully, start the thread
            super().start()  # Start the QThread
            return True
        
        except Exception as e:
            self.error_occurred.emit(f"Failed to start motor worker: {str(e)}")
            self.logger.error(f"Failed to start motor worker: {e}")
            return False
