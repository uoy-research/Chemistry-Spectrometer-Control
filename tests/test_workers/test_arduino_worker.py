"""
File: test_arduino_worker.py
Description: Tests for Arduino worker thread
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QThread
import time

from src.workers.arduino_worker import ArduinoWorker


@pytest.fixture
def mock_controller():
    """Create mock Arduino controller."""
    with patch('src.workers.arduino_worker.ArduinoController') as mock:
        controller = mock.return_value
        controller.start.return_value = True
        controller.get_readings.return_value = [1.0, 2.0, 3.0]
        controller.set_valves.return_value = True
        controller.send_depressurise.return_value = True
        yield controller


@pytest.fixture
def worker(mock_controller):
    """Create worker with mock controller."""
    worker = ArduinoWorker(port=1, update_interval=0.01)
    return worker


def test_initialization(worker):
    """Test worker initialization."""
    assert worker.port == 1
    assert worker.update_interval == 0.01
    assert worker._running is False
    assert worker._paused is False
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


def test_readings_monitoring(worker, mock_controller):
    """Test pressure readings monitoring."""
    # Setup readings sequence
    readings_sequence = [
        [1.0, 2.0, 3.0],
        [1.5, 2.5, 3.5],
        [2.0, 3.0, 4.0]
    ]
    mock_controller.get_readings.side_effect = readings_sequence

    # Setup signal tracking
    readings_updates = []
    worker.readings_updated.connect(lambda r: readings_updates.append(r))

    # Start worker
    worker.start()
    time.sleep(0.15)  # Allow readings updates
    worker.stop()
    worker.wait()

    # Verify readings updates
    assert readings_updates == readings_sequence


def test_valve_control(worker, mock_controller):
    """Test valve control."""
    # Start worker
    worker.start()

    # Set valve states
    states = [1, 0, 1, 0, 1, 0, 1, 0]
    result = worker.set_valves(states)
    time.sleep(0.05)

    # Stop worker
    worker.stop()
    worker.wait()

    # Verify valve control
    assert result is True
    mock_controller.set_valves.assert_called_once_with(states)


def test_depressurize(worker, mock_controller):
    """Test depressurize command."""
    # Start worker
    worker.start()

    # Send depressurize command
    result = worker.depressurize()
    time.sleep(0.05)

    # Stop worker
    worker.stop()
    worker.wait()

    # Verify depressurize command
    assert result is True
    mock_controller.send_depressurise.assert_called_once()


def test_pause_resume(worker):
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


def test_connection_failure(mock_controller):
    """Test handling of connection failure."""
    # Setup mock to fail connection
    mock_controller.start.return_value = False

    # Create worker
    worker = ArduinoWorker(port=1)

    # Setup signal tracking
    errors = []
    worker.error_occurred.connect(lambda e: errors.append(e))

    # Start worker
    worker.start()
    worker.wait()

    # Verify error handling
    assert "Failed to connect to Arduino" in errors


def test_readings_error_handling(worker, mock_controller):
    """Test handling of readings errors."""
    # Setup mock to return error
    mock_controller.get_readings.return_value = None

    # Setup signal tracking
    errors = []
    worker.error_occurred.connect(lambda e: errors.append(e))

    # Start worker
    worker.start()
    time.sleep(0.05)
    worker.stop()
    worker.wait()

    # Verify error handling
    assert any("Error getting readings" in e for e in errors)
