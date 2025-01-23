"""
File: tests/test_controllers/test_arduino_controller.py
Description: Tests for Arduino controller functionality
"""

import pytest
from unittest.mock import Mock, patch, call
import serial
import logging
from typing import List

from src.controllers.arduino_controller import ArduinoController


class TestArduinoController:
    """Test suite for ArduinoController class."""

    @pytest.fixture
    def mock_serial(self):
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
    def controller(self, mock_serial):
        """Create controller instance with mocked serial."""
        return ArduinoController(port=1, mode=1)

    @pytest.fixture
    def test_mode_controller(self):
        """Create controller in test mode."""
        return ArduinoController(port=1, mode=2)

    @pytest.fixture
    def debug_controller(self, caplog):
        """Create controller with logging for debugging."""
        caplog.set_level(logging.DEBUG)
        controller = ArduinoController(port=1, verbose=True)
        return controller, caplog

    def test_initialization(self):
        """Test controller initialization with various parameters."""
        # Test default initialization
        controller = ArduinoController(port=1)
        assert controller.port == "COM1"
        assert controller.mode == 1
        assert controller.running is False
        assert controller.serial is None
        assert not controller.verbose

        # Test with verbose logging
        verbose_controller = ArduinoController(port=2, verbose=True)
        assert verbose_controller.verbose is True
        assert verbose_controller.logger.level == logging.DEBUG

        # Test with test mode
        test_controller = ArduinoController(port=3, mode=2)
        assert test_controller.mode == 2

    def test_connection_lifecycle(self, controller, mock_serial):
        """Test complete connection lifecycle."""
        # Test successful connection
        assert controller.start() is True
        assert controller.running is True
        mock_serial.assert_called_once_with("COM1", 9600, timeout=1)

        # Test duplicate connection attempt
        assert controller.start() is True  # Should handle gracefully
        assert mock_serial.call_count == 1  # Should not create new connection

        # Test stop
        controller.stop()
        assert controller.running is False
        assert controller.serial is None

        # Test reconnection after stop
        assert controller.start() is True
        assert controller.running is True

    def test_reading_parsing(self, controller, mock_serial):
        """Test parsing of various reading formats."""
        controller.start()
        test_cases = [
            (b"1.0,2.0,3.0\n", [1.0, 2.0, 3.0]),
            (b"0.5,-1.0,2.5\n", [0.5, -1.0, 2.5]),
            (b"1,2,3\n", [1.0, 2.0, 3.0]),
            (b"invalid\n", None),
            (b"1.0,invalid,3.0\n", None),
            (b"", None),
            (b"1.0,2.0\n", None),  # Too few values
            (b"1.0,2.0,3.0,4.0\n", None),  # Too many values
        ]

        for input_data, expected in test_cases:
            mock_serial.return_value.readline.return_value = input_data
            assert controller.get_readings() == expected

    def test_valve_control(self, controller, mock_serial):
        """Test valve control functionality."""
        controller.start()
        mock_serial.return_value.readline.return_value = b"OK\n"

        # Test valid valve states
        valid_states = [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 1, 0, 1, 0, 1, 0]
        ]
        for states in valid_states:
            assert controller.set_valves(states) is True
            expected_command = f"v{''.join(map(str, states))}".encode()
            mock_serial.return_value.write.assert_called_with(expected_command)

        # Test invalid responses
        mock_serial.return_value.readline.return_value = b"ERROR\n"
        assert controller.set_valves([0] * 8) is False

    def test_error_handling(self, controller, mock_serial):
        """Test comprehensive error handling."""
        # Test connection errors
        with patch('serial.Serial', side_effect=serial.SerialException("Port busy")):
            assert controller.start() is False

        # Test various serial errors during operation
        controller.start()
        error_cases = [
            serial.SerialException("Connection lost"),
            TimeoutError("Read timeout"),
            ValueError("Invalid data"),
            Exception("Unknown error")
        ]
        
        for error in error_cases:
            mock_serial.return_value.readline.side_effect = error
            assert controller.get_readings() is None

            mock_serial.return_value.write.side_effect = error
            assert controller.set_valves([0] * 8) is False

    def test_test_mode_behavior(self, test_mode_controller):
        """Test behavior in test mode."""
        # Test connection
        assert test_mode_controller.start() is True
        assert test_mode_controller.running is True

        # Test readings
        readings = test_mode_controller.get_readings()
        assert readings == [1.0, 2.0, 3.0]
        assert len(readings) == 3

        # Test valve control
        assert test_mode_controller.set_valves([0] * 8) is True
        assert test_mode_controller.set_valves([1] * 8) is True

        # Test invalid operations still fail
        assert test_mode_controller.set_valves([2] * 8) is False
        assert test_mode_controller.set_valves([0] * 7) is False

    def test_logging(self, debug_controller, caplog):
        """Test logging functionality."""
        controller, log = debug_controller

        # Test connection logging
        controller.start()
        assert any("Connected to Arduino" in record.message 
                  for record in log.records)

        # Test reading logging
        controller.get_readings()
        assert any("Readings:" in record.message 
                  for record in log.records)

        # Test error logging
        with patch('serial.Serial', side_effect=Exception("Test error")):
            controller.start()
            assert any("Failed to connect" in record.message 
                      for record in log.records)

    def test_concurrent_operations(self, controller, mock_serial):
        """Test rapid sequential operations."""
        controller.start()
        mock_serial.return_value.readline.return_value = b"1.0,2.0,3.0\n"

        # Simulate rapid sequential operations
        for _ in range(100):
            controller.get_readings()
            controller.set_valves([0] * 8)
            assert controller.running is True

    @pytest.mark.parametrize("mode,expected_test_mode", [
        (1, False),
        (2, True),
        (3, False)
    ])
    def test_mode_configuration(self, mode, expected_test_mode):
        """Test different mode configurations."""
        controller = ArduinoController(port=1, mode=mode)
        assert controller.mode == mode
        assert (controller.mode == 2) == expected_test_mode
