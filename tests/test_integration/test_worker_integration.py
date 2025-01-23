"""
File: test_worker_integration.py
Description: Integration tests between workers and main application
"""

import pytest
from unittest.mock import Mock, patch, call
from PyQt6.QtCore import QThread
import time
import logging

from src.workers.arduino_worker import ArduinoWorker, MockArduinoController
from src.workers.motor_worker import MotorWorker, MockMotorController
from src.ui.main_window import MainWindow


class TestWorkerIntegration:
    """Test suite for worker integration."""

    @pytest.fixture
    def mock_workers(self):
        """Create worker instances with mock controllers."""
        arduino = ArduinoWorker(port=1, mock=True)
        motor = MotorWorker(port=1, mock=True)
        return arduino, motor

    @pytest.fixture
    def main_window(self):
        """Create main window instance in test mode."""
        return MainWindow(test_mode=True)

    def test_worker_initialization(self, mock_workers):
        """Test worker initialization and interaction."""
        arduino, motor = mock_workers

        # Verify initial state
        assert not arduino.running
        assert not motor.running
        assert isinstance(arduino.controller, MockArduinoController)
        assert isinstance(motor.controller, MockMotorController)

        # Start workers
        arduino.start()
        motor.start()
        time.sleep(0.05)  # Allow startup

        # Verify running state
        assert arduino.running
        assert motor.running

        # Stop workers
        arduino.stop()
        motor.stop()
        arduino.wait()
        motor.wait()

        # Verify stopped state
        assert not arduino.running
        assert not motor.running

    def test_synchronized_operations(self, mock_workers):
        """Test synchronized operations between workers."""
        arduino, motor = mock_workers

        # Setup signal tracking
        motor_updates = []
        valve_updates = []
        motor.position_updated.connect(lambda p: motor_updates.append(p))
        arduino.valve_updated.connect(lambda s: valve_updates.append(s))

        # Start workers
        arduino.start()
        motor.start()
        time.sleep(0.05)

        # Perform synchronized operations
        motor.move_to(100.0)
        arduino.set_valves([1] * 8)
        time.sleep(0.15)  # Allow operations to complete

        # Verify operations
        assert motor.get_current_position() == 100.0
        assert len(motor_updates) > 0
        assert len(valve_updates) > 0

        # Cleanup
        arduino.stop()
        motor.stop()
        arduino.wait()
        motor.wait()

    def test_error_propagation(self, mock_workers):
        """Test error handling and propagation between workers."""
        arduino, motor = mock_workers

        # Track errors
        arduino_errors = []
        motor_errors = []
        arduino.error_occurred.connect(lambda e: arduino_errors.append(e))
        motor.error_occurred.connect(lambda e: motor_errors.append(e))

        arduino.start()
        motor.start()

        # Test invalid operations
        arduino.set_valves([0] * 7)  # Invalid valve states
        motor.move_to(-1.0)  # Invalid position
        time.sleep(0.05)

        assert any("Invalid valve states" in e for e in arduino_errors)
        assert any("Invalid position value" in e for e in motor_errors)

        arduino.stop()
        motor.stop()

    def test_main_window_integration(self, main_window):
        """Test worker integration with main window."""
        # Verify worker initialization
        assert isinstance(main_window.arduino_worker, ArduinoWorker)
        assert isinstance(main_window.motor_worker, MotorWorker)
        assert main_window.arduino_worker.controller.mode == 2  # Test mode
        assert main_window.motor_worker.controller.mode == 2    # Test mode

        # Test sequence execution
        main_window.steps = [
            main_window.Step('p', 100),  # Pressurize
            main_window.Step('v', 100, 500)  # Vent with motor movement
        ]
        
        main_window.start_sequence()
        time.sleep(0.3)  # Allow sequence to run

        # Verify sequence execution
        assert len(main_window.steps) == 0  # Sequence completed

    def test_emergency_handling(self, mock_workers, main_window):
        """Test emergency situation handling."""
        arduino, motor = mock_workers
        arduino.start()
        motor.start()

        # Track status changes
        status_changes = []
        arduino.status_changed.connect(lambda s: status_changes.append(s))
        motor.status_changed.connect(lambda s: status_changes.append(s))

        # Simulate emergency
        motor.emergency_stop()
        arduino.depressurize()
        time.sleep(0.05)

        # Verify emergency handling
        assert "Motor emergency stopped" in status_changes
        assert not motor.running
        assert arduino.running  # Arduino should keep monitoring

        # Cleanup
        arduino.stop()
        motor.stop()

    def test_concurrent_operations(self, mock_workers):
        """Test concurrent operations between workers."""
        arduino, motor = mock_workers
        arduino.start()
        motor.start()

        # Perform rapid concurrent operations
        for i in range(10):
            motor.move_to(float(i * 100))
            arduino.set_valves([i % 2] * 8)
            time.sleep(0.01)

        time.sleep(0.1)  # Allow operations to complete

        # Verify system stability
        assert arduino.running
        assert motor.running
        assert isinstance(motor.get_current_position(), float)

        arduino.stop()
        motor.stop()

    def test_worker_recovery(self, mock_workers):
        """Test worker recovery after errors."""
        arduino, motor = mock_workers

        # Start and verify initial state
        assert arduino.start()
        assert motor.start()

        # Simulate failures and recovery
        with patch.object(arduino.controller, 'get_readings', 
                         side_effect=[Exception("Read error"), [1.0, 2.0, 3.0]]):
            readings = arduino.controller.get_readings()  # Should fail
            readings = arduino.controller.get_readings()  # Should recover
            assert readings == [1.0, 2.0, 3.0]

        # Verify system remains operational
        assert arduino.running
        assert motor.running

        arduino.stop()
        motor.stop()
