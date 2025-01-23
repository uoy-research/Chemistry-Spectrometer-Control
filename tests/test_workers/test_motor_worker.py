"""
File: test_motor_worker.py
Description: Tests for motor worker thread
"""

import pytest
from unittest.mock import Mock, patch, call
from PyQt6.QtCore import QThread
import time
import logging

from src.workers.motor_worker import MotorWorker, MockMotorController


class TestMotorWorker:
    """Test suite for MotorWorker class."""

    @pytest.fixture
    def mock_controller(self):
        """Create mock motor controller."""
        with patch('src.workers.motor_worker.MotorController') as mock:
            controller = mock.return_value
            controller.start.return_value = True
            controller.get_position.return_value = 0
            controller.set_position.return_value = True
            controller.stop_motor.return_value = True
            controller.running = True
            yield controller

    @pytest.fixture
    def worker(self, mock_controller):
        """Create worker with mock controller."""
        worker = MotorWorker(port=1, update_interval=0.01)
        return worker

    @pytest.fixture
    def mock_worker(self):
        """Create worker with mock controller for testing."""
        return MotorWorker(port=1, update_interval=0.01, mock=True)

    def test_initialization(self, worker):
        """Test worker initialization."""
        assert worker.port == 1
        assert worker.update_interval == 0.01
        assert worker._running is False
        assert worker._paused is False
        assert worker._target_position is None
        assert worker._current_position is None
        assert isinstance(worker, QThread)

    def test_mock_controller_initialization(self):
        """Test initialization with mock controller."""
        worker = MotorWorker(port=1, mock=True)
        assert isinstance(worker.controller, MockMotorController)
        assert worker.controller.POSITION_MIN == 0.0
        assert worker.controller.POSITION_MAX == 1000.0

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
        assert "Starting motor worker..." in status_changes
        assert "Motor worker running" in status_changes
        mock_controller.start.assert_called_once()

        # Stop worker
        worker.stop()
        worker.wait()

        # Verify shutdown
        assert worker._running is False
        assert "Motor worker stopped" in status_changes
        mock_controller.stop.assert_called_once()

    def test_position_monitoring(self, worker, mock_controller):
        """Test position monitoring and updates."""
        # Setup position sequence
        positions = [0.0, 10.0, 20.0, 30.0]
        mock_controller.get_position.side_effect = positions

        # Setup signal tracking
        position_updates = []
        worker.position_updated.connect(lambda p: position_updates.append(p))

        # Start worker
        worker.start()
        time.sleep(0.15)  # Allow position updates
        worker.stop()
        worker.wait()

        # Verify position updates
        assert position_updates == positions
        assert all(isinstance(p, float) for p in position_updates)

    def test_movement_completion(self, worker, mock_controller):
        """Test movement completion detection."""
        # Setup position sequence approaching target
        positions = [0.0, 50.0, 99.99, 100.0]  # Test float comparison tolerance
        mock_controller.get_position.side_effect = positions

        # Setup signal tracking
        completed_signals = []
        worker.movement_completed.connect(lambda s: completed_signals.append(s))

        # Start worker and move
        worker.start()
        assert worker.move_to(100.0) is True
        time.sleep(0.15)  # Allow movement
        worker.stop()
        worker.wait()

        # Verify completion signal
        assert True in completed_signals

    def test_error_handling(self, worker, mock_controller):
        """Test error handling scenarios."""
        # Setup error tracking
        errors = []
        worker.error_occurred.connect(lambda e: errors.append(e))

        # Test connection failure
        mock_controller.start.return_value = False
        worker.start()
        assert "Failed to connect to motor" in errors

        # Test position reading error
        mock_controller.start.return_value = True
        mock_controller.get_position.side_effect = Exception("Read error")
        worker.start()
        time.sleep(0.05)
        assert "Failed to get motor position" in errors

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
        assert "Motor worker paused" in status_changes

        # Test resume
        worker.resume()
        assert worker._paused is False
        assert "Motor worker running" in status_changes

    def test_emergency_stop(self, worker, mock_controller):
        """Test emergency stop functionality."""
        # Setup signal tracking
        status_changes = []
        errors = []
        worker.status_changed.connect(lambda s: status_changes.append(s))
        worker.error_occurred.connect(lambda e: errors.append(e))

        # Start worker
        worker.start()
        time.sleep(0.05)

        # Test successful emergency stop
        worker.emergency_stop()
        assert "Motor emergency stopped" in status_changes
        mock_controller.stop_motor.assert_called_once()

        # Test emergency stop with error
        mock_controller.stop_motor.side_effect = Exception("Stop error")
        worker.emergency_stop()
        assert any("Emergency stop failed" in e for e in errors)

    def test_concurrent_movement_rejection(self, worker):
        """Test rejection of concurrent movements."""
        # Setup error tracking
        errors = []
        worker.error_occurred.connect(lambda e: errors.append(e))

        # Start worker
        worker.start()

        # Request first movement
        assert worker.move_to(100.0) is True
        assert worker._target_position == 100.0

        # Request second movement
        assert worker.move_to(200.0) is False
        assert "Movement already in progress" in errors
        assert worker._target_position == 100.0  # Target unchanged

    def test_invalid_position_handling(self, worker):
        """Test handling of invalid position values."""
        # Setup error tracking
        errors = []
        worker.error_occurred.connect(lambda e: errors.append(e))

        worker.start()

        # Test invalid position types
        invalid_positions = [
            "invalid",
            None,
            [],
            {},
        ]
        for pos in invalid_positions:
            assert worker.move_to(pos) is False
            assert "Invalid position value" in errors

    def test_float_position_handling(self, mock_worker):
        """Test handling of float position values."""
        mock_worker.start()

        # Test float positions
        test_positions = [0.0, 100.5, 500.75, 1000.0]
        for pos in test_positions:
            assert mock_worker.move_to(pos) is True
            assert mock_worker._target_position == pos
            assert isinstance(mock_worker._target_position, float)

    def test_stop_movement(self, worker, mock_controller):
        """Test stopping current movement."""
        # Setup signal tracking
        status_changes = []
        worker.status_changed.connect(lambda s: status_changes.append(s))

        # Start worker and movement
        worker.start()
        worker.move_to(100.0)

        # Stop movement
        worker.stop_movement()
        assert worker._target_position is None
        assert "Motor movement stopped" in status_changes
        mock_controller.stop_motor.assert_called_once()
