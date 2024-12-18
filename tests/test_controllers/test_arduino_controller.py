"""
File: test_arduino_controller.py
Description: Tests for Arduino controller
"""

import pytest
from unittest.mock import Mock, patch
from src.controllers.arduino_controller import ArduinoController


@pytest.fixture
def controller():
    """Create controller in test mode."""
    return ArduinoController(port=1, mode=2, verbose=True)


def test_initialization(controller):
    """Test controller initialization."""
    assert controller.port == "COM1"
    assert controller.mode == 2
    assert controller.verbose is True
    assert controller.running is False


def test_start_stop(controller):
    """Test start and stop functionality."""
    with patch('serial.Serial') as mock_serial:
        assert controller.start() is True
        assert controller.running is True

        controller.stop()
        assert controller.running is False


def test_get_readings_test_mode(controller):
    """Test getting readings in test mode."""
    controller.start()
    readings = controller.get_readings()
    assert readings == [1.0, 2.0, 3.0]


def test_set_valves_test_mode(controller):
    """Test setting valves in test mode."""
    controller.start()
    assert controller.set_valves([0] * 8) is True


def test_depressurize_test_mode(controller):
    """Test depressurize command in test mode."""
    controller.start()
    assert controller.send_depressurise() is True


@pytest.mark.parametrize("response,expected", [
    (b"1.0,2.0,3.0\n", [1.0, 2.0, 3.0]),
    (b"0.0,0.0,0.0\n", [0.0, 0.0, 0.0]),
    (b"", None),  # Empty response
    (b"invalid\n", None),  # Invalid data
])
def test_get_readings_responses(controller, response, expected):
    """Test handling different reading responses."""
    with patch('serial.Serial') as mock_serial:
        instance = mock_serial.return_value
        instance.readline.return_value = response
        controller.start()
        readings = controller.get_readings()
        assert readings == expected


@pytest.mark.parametrize("states,expected", [
    ([0] * 8, True),  # All closed
    ([1] * 8, True),  # All open
    ([2] * 8, True),  # All unchanged
    ([0, 1, 2] * 2 + [0, 1], True),  # Mixed states
    ([0] * 7, False),  # Too few states
    ([0] * 9, False),  # Too many states
    ([3] * 8, False),  # Invalid states
])
def test_set_valves_validation(controller, states, expected):
    """Test valve state validation."""
    controller.start()
    assert controller.set_valves(states) is expected


def test_error_handling(controller):
    """Test error handling for various scenarios."""
    with patch('serial.Serial') as mock_serial:
        instance = mock_serial.return_value
        instance.write.side_effect = Exception("Test error")
        controller.start()

        assert controller.get_readings() is None
        assert controller.set_valves([0] * 8) is False
        assert controller.send_depressurise() is False
