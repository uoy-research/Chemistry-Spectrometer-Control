"""
File: tests/test_controllers/test_motor_controller.py
Description: Tests for motor controller functionality
"""

import pytest
from unittest.mock import Mock, patch, call
import minimalmodbus
import time
import logging

from src.controllers.motor_controller import MotorController


class TestMotorController:
    """Test suite for MotorController class."""

    @pytest.fixture
    def mock_instrument(self):
        """Create mock Modbus instrument."""
        with patch('minimalmodbus.Instrument', autospec=True) as mock:
            instance = Mock()
            mock.return_value = instance
            instance.read_register.return_value = 500
            instance.write_register.return_value = None
            instance.serial.baudrate = 9600
            instance.serial.timeout = 1
            yield mock

    @pytest.fixture
    def controller(self, mock_instrument):
        """Create controller with mock instrument."""
        return MotorController(port=1, mode=1)

    @pytest.fixture
    def test_mode_controller(self):
        """Create controller in test mode."""
        return MotorController(port=1, mode=2)

    @pytest.fixture
    def debug_controller(self, caplog):
        """Create controller with debug logging."""
        caplog.set_level(logging.DEBUG)
        return MotorController(port=1, verbose=True), caplog

    def test_initialization(self):
        """Test controller initialization with various parameters."""
        # Test default initialization
        controller = MotorController(port=1)
        assert controller.port == "COM1"
        assert controller.address == 1
        assert controller.mode == 1
        assert not controller.verbose
        assert controller.running is False
        assert controller.instrument is None

        # Test custom parameters
        controller = MotorController(port=2, address=3, verbose=True, mode=2)
        assert controller.port == "COM2"
        assert controller.address == 3
        assert controller.verbose is True
        assert controller.mode == 2

    def test_connection_lifecycle(self, controller, mock_instrument):
        """Test complete connection lifecycle."""
        # Test successful connection
        assert controller.start() is True
        assert controller.running is True
        mock_instrument.assert_called_once_with("COM1", 1)

        # Test duplicate connection
        assert controller.start() is True
        assert mock_instrument.call_count == 1

        # Test stop (implementation needed in MotorController)
        controller.stop()
        assert controller.running is False
        assert controller.instrument is None

    def test_position_control(self, controller, mock_instrument):
        """Test position control functionality."""
        controller.start()

        # Test valid positions
        valid_positions = [0.0, 500.0, 1000.0]
        for pos in valid_positions:
            assert controller.set_position(pos) is True
            mock_instrument.return_value.write_register.assert_called_with(0x0118, int(pos))

        # Test invalid positions
        invalid_positions = [-1.0, 1001.0, float('inf')]
        for pos in invalid_positions:
            assert controller.set_position(pos) is False

    def test_position_reading(self, controller, mock_instrument):
        """Test position reading functionality."""
        controller.start()
        
        # Test successful reading
        mock_instrument.return_value.read_register.return_value = 500
        assert controller.get_position() == 500.0

        # Test reading errors
        mock_instrument.return_value.read_register.side_effect = minimalmodbus.ModbusException
        assert controller.get_position() is None

    def test_wait_for_position(self, controller, mock_instrument):
        """Test waiting for position completion."""
        controller.start()
        target_position = 500.0

        # Mock position updates
        positions = [0.0, 100.0, 300.0, 500.0]
        mock_instrument.return_value.read_register.side_effect = positions

        with patch('time.sleep') as mock_sleep:
            assert controller.set_position(target_position, wait=True) is True
            assert mock_sleep.call_count > 0

    def test_error_handling(self, controller, mock_instrument):
        """Test comprehensive error handling."""
        # Test connection errors
        with patch('minimalmodbus.Instrument', side_effect=Exception("Port error")):
            assert controller.start() is False

        # Test operation errors
        controller.start()
        error_cases = [
            minimalmodbus.ModbusException("Communication error"),
            minimalmodbus.InvalidResponseError("Invalid response"),
            ValueError("Invalid value"),
            Exception("Unknown error")
        ]

        for error in error_cases:
            mock_instrument.return_value.read_register.side_effect = error
            assert controller.get_position() is None

            mock_instrument.return_value.write_register.side_effect = error
            assert controller.set_position(500.0) is False

    def test_test_mode_behavior(self, test_mode_controller):
        """Test behavior in test mode."""
        # Test connection
        assert test_mode_controller.start() is True
        assert test_mode_controller.running is True

        # Test position control
        assert test_mode_controller.set_position(500.0) is True
        assert test_mode_controller.get_position() == 500.0

        # Test position limits
        assert test_mode_controller.set_position(-1.0) is False
        assert test_mode_controller.set_position(1001.0) is False

    def test_logging(self, debug_controller, caplog):
        """Test logging functionality."""
        controller, log = debug_controller

        # Test connection logging
        controller.start()
        assert any("Connected to motor" in record.message 
                  for record in log.records)

        # Test position logging
        controller.set_position(500.0)
        assert any("position" in record.message.lower() 
                  for record in log.records)

        # Test error logging
        with patch('minimalmodbus.Instrument', side_effect=Exception("Test error")):
            controller.start()
            assert any("Failed to connect" in record.message 
                      for record in log.records)

    def test_emergency_stop(self, controller, mock_instrument):
        """Test emergency stop functionality."""
        controller.start()
        
        # Test successful stop
        assert controller.stop_motor() is True
        
        # Test stop when not running
        controller.running = False
        assert controller.stop_motor() is False

        # Test stop with communication error
        controller.running = True
        mock_instrument.return_value.write_register.side_effect = Exception
        assert controller.stop_motor() is False

    @pytest.mark.parametrize("input_pos,expected_pos", [
        (0, 0.0),
        (500, 500.0),
        (1000, 1000.0),
        ("500", 500.0),  # Test string conversion
        (500.5, 500.5),  # Test float handling
    ])
    def test_position_conversion(self, controller, mock_instrument, input_pos, expected_pos):
        """Test position value conversion and handling."""
        controller.start()
        assert controller.set_position(input_pos) is True
        assert isinstance(controller.get_position(), float)

    def test_concurrent_operations(self, controller, mock_instrument):
        """Test rapid sequential operations."""
        controller.start()
        
        # Simulate rapid position changes
        for pos in range(0, 1000, 100):
            assert controller.set_position(float(pos)) is True
            assert controller.get_position() is not None
            assert controller.running is True
