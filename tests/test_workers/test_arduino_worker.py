"""
File: test_motor_worker.py
Description: Tests for motor worker thread
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QThread
import time

from src.workers.motor_worker import MotorWorker


@pytest.fixture
def mock_controller():
    """Create mock motor controller."""
    with patch('src.workers.motor_worker.MotorController') as mock:
        controller = mock.return_value
        controller.start.return_value = True
        controller.get_position.return_value = 0
        controller.set_position.return_value = True
        controller.set_speed.return_value = True
        yield controller


@pytest.fixture
def worker(mock_controller):
    """Create worker with mock controller."""
    worker = MotorWorker(port=1, update_interval=0.01)
    return worker


def test_initialization(worker):
    """Test worker initialization."""
    assert worker.port == 1
    assert worker.update_interval == 0.01
    assert worker._running is False
    assert worker._paused is False
    assert worker._target_position is None
    assert isinstance(worker, QThread)


def test_start_stop(worker, mock_controller):
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


def test_position_monitoring(worker, mock_controller):
    """Test position monitoring and updates."""
    # Setup position sequence
    positions = [0, 10, 20, 30]
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


def test_movement_completion(worker, mock_controller):
    """Test movement completion detection."""
    # Setup position sequence
    positions = [0, 50, 100, 100]  # Last position matches target
    mock_controller.get_position.side_effect = positions

    # Setup signal tracking
    completed = []
    worker.movement_completed.connect(lambda s: completed.append(s))

    # Start worker and move
    worker.start()
    worker.move_to(100)
    time.sleep(0.15)  # Allow movement
    worker.stop()
    worker.wait()

    # Verify completion
    assert True in completed


def test_speed_control(worker, mock_controller):
    """Test speed control."""
    # Start worker
    worker.start()

    # Set speed
    result = worker.set_speed(500)
    time.sleep(0.05)

    # Stop worker
    worker.stop()
    worker.wait()

    # Verify speed control
    assert result is True
    mock_controller.set_speed.assert_called_once_with(500)


def test_homing(worker):
    """Test homing functionality."""
    # Setup signal tracking
    moves = []
    with patch.object(worker, 'move_to') as mock_move:
        worker.home()
        mock_move.assert_called_once_with(0)


def test_pause_resume(worker):
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


def test_connection_failure(mock_controller):
    """Test handling of connection failure."""
    # Setup mock to fail connection
    mock_controller.start.return_value = False

    # Create worker
    worker = MotorWorker(port=1)

    # Setup signal tracking
    errors = []
    worker.error_occurred.connect(lambda e: errors.append(e))

    # Start worker
    worker.start()
    worker.wait()

    # Verify error handling
    assert "Failed to connect to motor" in errors


def test_concurrent_movement_rejection(worker):
    """Test rejection of concurrent movements."""
    # Setup signal tracking
    errors = []
    worker.error_occurred.connect(lambda e: errors.append(e))

    # Start worker
    worker.start()

    # Request first movement
    assert worker.move_to(100) is True

    # Request second movement
    assert worker.move_to(200) is False
    assert "Movement already in progress" in errors

    # Stop worker
    worker.stop()
    worker.wait()
