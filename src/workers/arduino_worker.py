"""
File: arduino_worker.py
Description: Worker thread for Arduino communication
"""

from PyQt6.QtCore import QThread, pyqtSignal
import time
import logging
from typing import List, Optional

from controllers.arduino_controller import ArduinoController


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
            from controllers.base_controller import MockArduinoController
            self.controller = MockArduinoController(port=port)
        else:
            self.controller = ArduinoController(port=port)

        self._running = False
        self._paused = False
        self._valve_queue = []

        self.logger = logging.getLogger(__name__)

    def run(self):
        """Main worker loop."""
        self.status_changed.emit("Starting Arduino worker...")

        if not self.controller.start():
            self.error_occurred.emit("Failed to connect to Arduino")
            return

        self._running = True
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
