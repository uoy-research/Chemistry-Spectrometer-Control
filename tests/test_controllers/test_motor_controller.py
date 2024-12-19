"""
File: tests/test_controllers/test_motor_controller.py
Description: Tests for motor controller
"""

import pytest
from unittest.mock import Mock, patch
import minimalmodbus

from src.controllers.motor_controller import MotorController


@pytest.fixture
def mock_instrument():
    """Create mock Modbus instrument."""
    with patch('minimalmodbus.Instrument') as mock:
        instance = Mock()
        mock.return_value = instance
        instance.read_register.return_value = 500
        instance.write_register.return_value = None
        instance.serial.baudrate = 9600
        instance.serial.timeout = 1
        yield mock


@pytest.fixture
def controller(mock_instrument):
    """Create controller with mock instrument."""
    controller = MotorController(port=1, mode=1)
    return controller
