"""
File: test_arduino_worker.py
Description: Tests for Arduino worker thread
"""

import pytest
from unittest.mock import Mock, patch, call
from PyQt6.QtCore import QThread
import time
import logging

from src.workers.arduino_worker import ArduinoWorker, MockArduinoController


class TestArduinoWorker:
    """Test suite for ArduinoWorker class."""

    @pytest.fixture
    def mock_controller(self):
        """Create mock Arduino controller."""
        with patch('src.workers.arduino_worker.ArduinoController') as mock:
            controller = mock.return_value
            controller.start.return_value = True
            controller.get_readings.return_value = [1.0, 2.0, 3.0]
            controller.set_valves.return_value = True
            controller.send_depressurise.return_value = True
            controller.running = True
            yield controller

    @pytest.fixture
    def worker(self, mock_controller):
        """Create worker with mock controller."""
        return ArduinoWorker(port=1, update_interval=0.01)

    @pytest.fixture
    def mock_worker(self):
        """Create worker with mock controller for testing."""
        return ArduinoWorker(port=1, update_interval=0.01, mock=True)

    def test_initialization(self, worker):
        """Test worker initialization."""
        assert worker.port == 1
        assert worker.update_interval == 0.01
        assert worker._running is False
        assert worker._paused is False
        assert worker._valve_queue == []
        assert isinstance(worker, QThread)

    def test_mock_controller_initialization(self):
        """Test initialization with mock controller."""
        worker = ArduinoWorker(port=1, mock=True)
        assert isinstance(worker.controller, MockArduinoController)
        assert worker.controller.mode == 0
        assert worker.controller.port == 1

    def test_start_stop(self, worker, mock_controller):
        """Test worker start and stop."""
        # Setup signal tracking
        status_changes = []
        worker.status_changed.connect(lambda s: status_changes.append(s))

        # Start worker
        worker.start()
        time.sleep(0.05)  # Allow some cycles

        # Verify startup
        assert worker._running is True
        assert "Starting Arduino worker..." in status_changes
        assert "Arduino worker running" in status_changes
        mock_controller.start.assert_called_once()

        # Stop worker
        worker.stop()
        worker.wait()

        # Verify shutdown
        assert worker._running is False
        assert "Arduino worker stopped" in status_changes
        mock_controller.stop.assert_called_once()

    def test_readings_monitoring(self, worker, mock_controller):
        """Test pressure readings monitoring."""
        # Setup readings sequence
        readings_sequence = [
            [1.0, 2.0, 3.0],
            [1.5, 2.5, 3.5],
            [2.0, 3.0, 4.0],
            None  # Test error handling
        ]
        mock_controller.get_readings.side_effect = readings_sequence

        # Setup signal tracking
        readings_updates = []
        errors = []
        worker.readings_updated.connect(lambda r: readings_updates.append(r))
        worker.error_occurred.connect(lambda e: errors.append(e))

        # Start worker
        worker.start()
        time.sleep(0.15)  # Allow readings updates
        worker.stop()
        worker.wait()

        # Verify readings updates
        assert readings_updates == readings_sequence[:-1]  # Exclude None reading
        assert "Failed to get pressure readings" in errors

    def test_valve_control(self, worker, mock_controller):
        """Test valve control functionality."""
        # Setup signal tracking
        valve_updates = []
        worker.valve_updated.connect(lambda s: valve_updates.append(s))

        # Start worker
        worker.start()

        # Test valid valve states
        valid_states = [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 1, 0, 1, 0, 1, 0]
        ]
        
        for states in valid_states:
            worker.set_valves(states)
            time.sleep(0.05)  # Allow processing

        # Test invalid valve states
        invalid_states = [
            [0, 0, 0],  # Too few states
            [1, 1, 1, 1, 1, 1, 1, 1, 1],  # Too many states
            [0, 1, 2, 0, 1, 0, 1, 0]  # Invalid state value
        ]

        errors = []
        worker.error_occurred.connect(lambda e: errors.append(e))
        
        for states in invalid_states:
            worker.set_valves(states)
            time.sleep(0.05)

        worker.stop()
        worker.wait()

        # Verify valve control
        assert len(valve_updates) == len(valid_states)
        assert all(update is True for update in valve_updates)
        assert "Invalid valve states" in errors

    def test_depressurize(self, worker, mock_controller):
        """Test depressurize functionality."""
        # Setup signal tracking
        errors = []
        worker.error_occurred.connect(lambda e: errors.append(e))

        # Start worker
        worker.start()

        # Test successful depressurize
        assert worker.depressurize() is True
        mock_controller.send_depressurise.assert_called_once()

        # Test failed depressurize
        mock_controller.send_depressurise.return_value = False
        assert worker.depressurize() is True  # Method itself returns None
        assert "Failed to depressurize" in errors

        worker.stop()
        worker.wait()

    def test_pause_resume(self, worker):
        """Test pause and resume functionality."""
        # Setup signal tracking
        status_changes = []
        worker.status_changed.connect(lambda s: status_changes.append(s))

        # Test pause
        worker.pause()
        assert worker._paused is True
        assert "Arduino worker paused" in status_changes

        # Test resume
        worker.resume()
        assert worker._paused is False
        assert "Arduino worker running" in status_changes

    def test_error_handling(self, worker, mock_controller):
        """Test comprehensive error handling."""
        # Setup error tracking
        errors = []
        worker.error_occurred.connect(lambda e: errors.append(e))

        # Test connection failure
        mock_controller.start.return_value = False
        worker.start()
        assert "Failed to connect to Arduino" in errors

        # Test reading errors
        mock_controller.start.return_value = True
        mock_controller.get_readings.side_effect = Exception("Read error")
        worker.start()
        time.sleep(0.05)
        assert "Failed to get pressure readings" in errors

        worker.stop()
        worker.wait()

    def test_valve_queue_processing(self, worker, mock_controller):
        """Test valve command queue processing."""
        worker.start()

        # Queue multiple valve commands
        commands = [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 1, 0, 1, 0, 1, 0]
        ]

        for cmd in commands:
            worker.set_valves(cmd)

        time.sleep(0.15)  # Allow processing
        worker.stop()
        worker.wait()

        # Verify all commands were processed
        assert mock_controller.set_valves.call_count == len(commands)
        mock_controller.set_valves.assert_has_calls([call(cmd) for cmd in commands])

    def test_mock_controller_behavior(self, mock_worker):
        """Test behavior with mock controller."""
        mock_worker.start()

        # Test readings
        readings = mock_worker.controller.get_readings()
        assert readings == [1.0, 2.0, 3.0, 4.0]
        assert len(readings) == 4

        # Test valve control
        assert mock_worker.controller.set_valves([0] * 8) is True
        assert mock_worker.controller.set_valves([1] * 8) is True

        # Test depressurize
        assert mock_worker.controller.send_depressurise() is True

        mock_worker.stop()
        mock_worker.wait()
