"""
File: test_motor_controller.py
Description: Tests for motor controller
"""

import pytest
from unittest.mock import Mock, patch
from src.controllers.motor_controller import MotorController


@pytest.fixture
def controller():
    """Create controller in test mode."""
    return MotorController(port=1, mode=2, verbose=True)


def test_initialization(controller):
    """Test controller initialization."""
    assert controller.port == "COM1"
    assert controller.mode == 2
    assert controller.verbose is True
    assert controller.running is False
    assert controller.address == 1


def test_start_stop(controller):
    """Test start and stop functionality."""
    with patch('minimalmodbus.Instrument') as mock_instrument:
        # Configure mock
        instance = mock_instrument.return_value
        instance.read_register.return_value = 0

        # Test start
        assert controller.start() is True
        assert controller.running is True

        # Verify instrument configuration
        mock_instrument.assert_called_once_with("COM1", 1)
        assert instance.serial.baudrate == 9600
        assert instance.serial.timeout == 1

        # Test stop
        controller.stop()
        assert controller.running is False
        instance.serial.close.assert_called_once()


def test_get_position_test_mode(controller):
    """Test getting position in test mode."""
    controller.start()
    position = controller.get_position()
    assert position == 500  # Test mode returns mock position


def test_set_position_test_mode(controller):
    """Test setting position in test mode."""
    controller.start()
    assert controller.set_position(100) is True
    assert controller.set_position(2000) is False  # Out of range


def test_set_speed_test_mode(controller):
    """Test setting speed in test mode."""
    controller.start()
    assert controller.set_speed(500) is True
    assert controller.set_speed(2000) is False  # Out of range


def test_home_test_mode(controller):
    """Test homing function in test mode."""
    controller.start()
    assert controller.home() is True


@pytest.mark.parametrize("position,valid", [
    (0, True),
    (500, True),
    (1000, True),
    (-1, False),
    (1001, False),
])
def test_position_validation(controller, position, valid):
    """Test position validation with various values."""
    controller.start()
    assert controller.set_position(position) is valid


@pytest.mark.parametrize("speed,valid", [
    (0, True),
    (500, True),
    (1000, True),
    (-1, False),
    (1001, False),
])
def test_speed_validation(controller, speed, valid):
    """Test speed validation with various values."""
    controller.start()
    assert controller.set_speed(speed) is valid


def test_not_running_operations(controller):
    """Test operations when controller is not running."""
    assert controller.get_position() is None
    assert controller.set_position(100) is False
    assert controller.set_speed(500) is False
    assert controller.home() is False


@pytest.mark.parametrize("method_name,args", [
    ("get_position", []),
    ("set_position", [100]),
    ("set_speed", [500]),
    ("home", []),
])
def test_error_handling(controller, method_name, args):
    """Test error handling for various methods."""
    with patch('minimalmodbus.Instrument') as mock_instrument:
        # Configure mock to raise exception
        instance = mock_instrument.return_value
        method = getattr(instance, "read_register" if method_name ==
                         "get_position" else "write_register")
        method.side_effect = Exception("Test error")

        # Start controller with real instrument
        controller.mode = 1  # Switch to real mode
        controller.start()

        # Test method
        method = getattr(controller, method_name)
        if method_name == "set_position":
            assert method(*args, wait=False) is False
        else:
            assert method(*args) is False or method(*args) is None


def test_position_wait(controller):
    """Test waiting for position movement to complete."""
    with patch('minimalmodbus.Instrument') as mock_instrument:
        # Configure mock
        instance = mock_instrument.return_value

        # Mock position readings that simulate movement
        positions = [0, 25, 50, 75, 100]
        instance.read_register.side_effect = positions

        # Start controller with real instrument
        controller.mode = 1  # Switch to real mode
        controller.start()

        # Test setting position with wait
        assert controller.set_position(100, wait=True) is True

        # Verify all positions were read
        assert instance.read_register.call_count == len(positions)


def test_position_boundaries(controller):
    """Test position boundary conditions."""
    controller.start()

    # Test exact boundaries
    assert controller.set_position(controller.POSITION_MIN) is True
    assert controller.set_position(controller.POSITION_MAX) is True

    # Test just outside boundaries
    assert controller.set_position(controller.POSITION_MIN - 1) is False
    assert controller.set_position(controller.POSITION_MAX + 1) is False


def test_speed_boundaries(controller):
    """Test speed boundary conditions."""
    controller.start()

    # Test exact boundaries
    assert controller.set_speed(controller.SPEED_MIN) is True
    assert controller.set_speed(controller.SPEED_MAX) is True

    # Test just outside boundaries
    assert controller.set_speed(controller.SPEED_MIN - 1) is False
    assert controller.set_speed(controller.SPEED_MAX + 1) is False


def test_logging(controller, caplog):
    """Test logging functionality."""
    controller.start()

    # Perform operations that should log
    controller.get_position()
    controller.set_position(100, wait=False)
    controller.set_speed(500)

    # Verify log messages
    assert any("position" in msg.lower() for msg in caplog.messages)
