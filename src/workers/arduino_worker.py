"""
File: arduino_worker.py
Description: Worker thread for Arduino communication
"""

from PyQt6.QtCore import QThread, pyqtSignal
import time
import logging
import random
import math
from typing import List, Optional

from controllers.arduino_controller import ArduinoController


class MockArduinoController:
    """Mock Arduino controller for testing."""

    def __init__(self, port: int):
        self.port = port
        self.running = False
        self.mode = 0
        self._start_time = time.time()
        self.logger = logging.getLogger(__name__)

        # Initialize base pressure values and variation parameters
        # Different base pressure for each sensor
        self._base_pressures = [1.0, 2.0, 3.0, 4.0]
        self._variation_amplitude = 0.2  # Amount of random variation
        self._oscillation_period = 10.0  # Period of oscillation in seconds

    def start(self) -> bool:
        self.running = True
        self._start_time = time.time()  # Reset start time when starting
        self.logger.debug("Mock Arduino controller started")
        return True

    def stop(self):
        self.running = False

    def get_readings(self) -> List[float]:
        """Generate simulated pressure readings with time-varying components."""
        if not self.running:
            return [0.0] * 4

        # Calculate time-based variation
        elapsed_time = time.time() - self._start_time
        oscillation = math.sin(
            2 * math.pi * elapsed_time / self._oscillation_period)

        # Generate readings for each sensor
        readings = []
        for base_pressure in self._base_pressures:
            # Add time-based oscillation and random variation
            random_variation = random.uniform(
                -self._variation_amplitude, self._variation_amplitude)
            pressure = base_pressure + (oscillation * 0.5) + random_variation
            # Ensure pressure stays positive
            pressure = max(0.0, pressure)
            readings.append(pressure)

        return readings

    def set_valves(self, states: List[int]) -> bool:
        # Simulate valve state changes affecting pressures
        if states[1]:  # If inlet valve (Valve 2) is open
            self._base_pressures = [
                p + 0.5 for p in self._base_pressures]  # Increase pressure
        elif states[3]:  # If vent valve (Valve 4) is open
            self._base_pressures = [
                # Decrease pressure
                max(1.0, p - 0.5) for p in self._base_pressures]
        return True

    def send_depressurise(self) -> bool:
        # Reset pressures to base values
        self._base_pressures = [1.0, 2.0, 3.0, 4.0]
        return True


class ArduinoWorker(QThread):
    """
    Worker thread for handling Arduino communication.

    Signals:
        readings_updated(list): Emitted when new pressure readings are available
        valve_updated(bool): Emitted when valve state changes
        error_occurred(str): Emitted when an error occurs
        status_changed(str): Emitted when worker status changes
    """

    readings_updated = pyqtSignal(list)
    valve_updated = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self, port: int, update_interval: float = 0.1, mock: bool = False):
        """Initialize worker.

        Args:
            port: COM port number
            update_interval: Data update interval in seconds
            mock: Use mock controller for testing
        """
        super().__init__()

        self.port = port
        self.update_interval = update_interval
        if mock:
            self.controller = MockArduinoController(port=port)
            self._running = False
        else:
            self.controller = ArduinoController(port=port, verbose=True)

        self._running = False
        self._paused = False
        self._valve_queue = []

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def start(self) -> bool:
        """Start the worker thread.

        Returns:
            bool: True if started successfully
        """
        self.logger.info("Starting Arduino worker thread...")
        if not self._running:
            super().start()
            return True
        return False

    def run(self):
        """Main worker loop."""
        self.logger.info("Arduino worker thread running")
        self.status_changed.emit("Starting Arduino worker...")

        # Try to start the controller
        if not self.controller.start():
            self.error_occurred.emit("Failed to connect to Arduino")
            self.logger.error("Failed to start Arduino controller")
            return

        self._running = True
        self.logger.info("Arduino controller started successfully")
        self.status_changed.emit("Arduino worker running")

        while self._running:
            if not self._paused:
                # Process valve commands
                if self._valve_queue:
                    states = self._valve_queue.pop(0)
                    success = self.controller.set_valves(states)
                    self.valve_updated.emit(success)

                # Get pressure readings
                readings = self.controller.get_readings()
                if readings:
                    self.readings_updated.emit(readings)
                    if isinstance(self.controller, MockArduinoController):
                        # Debug log the mock readings
                        # self.logger.debug(f"Mock readings: {readings}")
                        pass
                else:
                    self.error_occurred.emit("Failed to get pressure readings")

            # Sleep for update interval
            time.sleep(self.update_interval)

        self.controller.stop()
        self.status_changed.emit("Arduino worker stopped")

    def stop(self):
        """Stop the worker."""
        self._running = False
        self.wait()

    def pause(self):
        """Pause data collection."""
        self._paused = True
        self.status_changed.emit("Arduino worker paused")

    def resume(self):
        """Resume data collection."""
        self._paused = False
        self.status_changed.emit("Arduino worker running")

    def set_valves(self, states: List[int]):
        """Queue valve state change."""
        if len(states) != 8:
            self.error_occurred.emit("Invalid valve states")
            return
        self._valve_queue.append(states)

    def depressurize(self):
        """Send emergency depressurize command."""
        if self.controller.running:
            success = self.controller.send_depressurise()
            if not success:
                self.error_occurred.emit("Failed to depressurize")

    @property
    def running(self) -> bool:
        """Get the running state of the worker."""
        return self._running
