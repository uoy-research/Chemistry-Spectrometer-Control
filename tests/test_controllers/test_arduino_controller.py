"""
File: tests/test_controllers/test_arduino_controller.py
"""

import pytest
from unittest.mock import Mock, patch
import serial
import logging

from src.controllers.arduino_controller import ArduinoController

# ===== Fixtures =====


@pytest.fixture
def mock_serial():
    """Create mock serial connection."""
    with patch('serial.Serial', autospec=True) as mock:
        instance = Mock()
        mock.return_value = instance
        instance.readline.return_value = b"1.0,2.0,3.0\n"
        instance.write.return_value = None
        instance.is_open = True
        instance.port = "COM1"
        instance.baudrate = 9600
        instance.timeout = 1
        yield mock


@pytest.fixture
def controller(mock_serial):
    """Create controller instance with mocked serial."""
    return ArduinoController(port=1, mode=1)


@pytest.fixture
def test_mode_controller():
    """Create controller in test mode."""
    return ArduinoController(port=1, mode=2)


@pytest.fixture
def debug_controller(caplog):
    """Create controller with logging for debugging."""
    caplog.set_level(logging.DEBUG)
    controller = ArduinoController(port=1, verbose=True)
    return controller, caplog

# ===== Test Cases =====


def test_initialization():
    """Test controller initialization."""
    controller = ArduinoController(port=1)
    assert controller.port == "COM1"
    assert controller.mode == 1
    assert controller.running is False
    assert controller.serial is None


def test_start_stop(controller, mock_serial):
    """Test start/stop functionality."""
    # Test start
    assert controller.start() is True
    assert controller.running is True
    mock_serial.assert_called_once_with("COM1", 9600, timeout=1)

    # Test stop
    controller.stop()
    assert controller.running is False
    assert controller.serial is None


def test_get_readings_test_mode(test_mode_controller):
    """Test readings in test mode."""
    test_mode_controller.start()
    readings = test_mode_controller.get_readings()
    assert readings == [1.0, 2.0, 3.0]  # Default test mode values


@pytest.mark.parametrize("response,expected", [
    (b"1.0,2.0,3.0\n", [1.0, 2.0, 3.0]),
    (b"0.0,0.0,0.0\n", [0.0, 0.0, 0.0]),
    (b"", None),
    (b"invalid\n", None)
])
def test_get_readings_responses(controller, mock_serial, response, expected):
    """Test different reading responses."""
    controller.start()
    mock_serial.return_value.readline.return_value = response
    assert controller.get_readings() == expected


@pytest.mark.parametrize("states,expected", [
    ([1, 1, 1, 1, 1, 1, 1, 1], True),
    ([0, 0, 0, 0, 0, 0, 0, 0], True),
    ([1, 0, 1, 0, 1, 0, 1, 0], True),
    ([0, 1, 0, 1, 0, 1, 0, 1], True),
    ([2, 2, 2, 2, 2, 2, 2, 2], False),  # Invalid states
    ([1, 1, 1, 1, 1, 1, 1], False),     # Wrong length
    ([1, 1, 1, 1, 1, 1, 1, 1, 1], False)  # Wrong length
])
def test_set_valves_validation(controller, mock_serial, states, expected):
    """Test valve state validation."""
    controller.start()
    mock_serial.return_value.readline.return_value = b"OK\n"
    assert controller.set_valves(states) is expected


def test_error_handling(controller):
    """Test error handling."""
    # Test serial error
    with patch('serial.Serial', side_effect=serial.SerialException):
        assert controller.start() is False

    # Test reading error
    controller.running = True
    with patch.object(controller.serial, 'readline', side_effect=Exception):
        assert controller.get_readings() is None


def test_depressurize_test_mode(test_mode_controller):
    """Test depressurize in test mode."""
    test_mode_controller.start()
    assert test_mode_controller.depressurize() is True
