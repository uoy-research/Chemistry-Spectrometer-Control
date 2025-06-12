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
            instance.read_registers.return_value = [
                0, 0]  # Default for all tests
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

    def test_init_normal_mode_success(self, mock_instrument):
        """Test successful initialization in normal mode."""
        controller = MotorController(port=1, mode=1)
        mock_instrument.return_value.write_bit.return_value = None
        mock_instrument.return_value.read_bit.return_value = True
        mock_instrument.return_value.read_registers.return_value = [0, 0]

        assert controller.start() is True
        assert controller.running is True
        assert controller.serial_connected is True
        assert hasattr(controller, '_initial_offset')

    def test_init_normal_mode_fail(self, mock_instrument):
        """Test initialization failure in normal mode."""
        controller = MotorController(port=1, mode=1)
        mock_instrument.return_value.write_bit.side_effect = Exception(
            "Connection error")

        assert controller.start() is False
        assert controller.running is False
        assert controller.serial_connected is False

    def test_get_position_happy(self, controller, mock_instrument):
        """Test successful position reading."""
        controller.start()
        mock_instrument.return_value.read_registers.return_value = [
            0x0001, 0x0000]  # 65536 steps

        position = controller.get_position()
        assert position == 10.24  # 65536/6400.0 - offset

    def test_get_position_error_retry(self, controller, mock_instrument):
        """Test position reading with retries."""
        controller.start()
        mock_instrument.return_value.read_registers.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3"),
            [0x0001, 0x0000]  # Success on 4th try
        ]

        # First three calls should return last known position
        assert controller.get_position() == 0.0
        assert controller.get_position() == 0.0
        assert controller.get_position() == 0.0
        # Fourth call should succeed
        assert controller.get_position() == 10.24

    def test_get_position_critical_error(self, controller, mock_instrument):
        """Test critical error after too many failures."""
        controller.start()
        mock_instrument.return_value.read_registers.side_effect = Exception(
            "Persistent error")

        # Should raise after 5 consecutive errors
        for _ in range(5):
            controller.get_position()

        with pytest.raises(MotorController.MotorCriticalError):
            controller.get_position()

    def test_start_calibration_success(self, controller, mock_instrument):
        """Test successful calibration start."""
        controller.start()
        mock_instrument.return_value.write_register.return_value = None

        assert controller.start_calibration() is True
        mock_instrument.return_value.write_register.assert_called_with(
            2, ord('c'))

    def test_start_calibration_fail(self, controller, mock_instrument):
        """Test calibration start failure."""
        controller.start()
        mock_instrument.return_value.write_register.side_effect = Exception(
            "Write error")

        assert controller.start_calibration() is False

    def test_check_calibrated_false(self, controller, mock_instrument):
        """Test calibration check before completion."""
        controller.start()
        mock_instrument.return_value.read_bit.return_value = False

        assert controller.check_calibrated() is False
        assert not controller._is_calibrated

    def test_check_calibrated_true(self, controller, mock_instrument):
        """Test successful calibration check."""
        controller.start()
        mock_instrument.return_value.read_bit.return_value = True
        mock_instrument.return_value.read_registers.return_value = [
            0x0001, 0x0000]

        assert controller.check_calibrated() is True
        assert controller._is_calibrated
        assert hasattr(controller, '_initial_offset')

    def test_set_position_within_limits(self, controller, mock_instrument):
        """Test setting position within valid range."""
        controller.start()
        position = 50.0

        success, actual_pos = controller.set_position(position)
        assert success is True
        assert actual_pos == position
        mock_instrument.return_value.write_registers.assert_called_once()

    def test_set_position_clamp_above_max(self, controller, mock_instrument):
        """Test position clamping above maximum."""
        controller.start()
        position = controller.POSITION_MAX + 10

        success, actual_pos = controller.set_position(position)
        assert success is True
        assert actual_pos == controller.POSITION_MAX

    def test_set_position_invalid_type(self, controller, mock_instrument):
        """Test setting position with invalid type."""
        controller.start()
        success, actual_pos = controller.set_position("foo")
        assert success is False
        assert actual_pos == "foo"

    def test_stop_motor_success(self, controller, mock_instrument):
        """Test successful motor stop."""
        controller.start()
        mock_instrument.return_value.write_register.return_value = None

        assert controller.stop_motor() is True
        mock_instrument.return_value.write_register.assert_called_with(
            2, ord('e'))

    def test_stop_motor_retry_exhausted(self, controller, mock_instrument):
        """Test motor stop with exhausted retries."""
        controller.start()
        mock_instrument.return_value.write_register.side_effect = Exception(
            "Write error")

        assert controller.stop_motor() is False
        assert not controller.serial_connected

    def test_to_top_and_bottom(self, controller, mock_instrument):
        """Test top and bottom movement commands."""
        controller.start()
        original_timeout = controller.instrument.serial.timeout

        # Test to_top
        assert controller.to_top() is True
        mock_instrument.return_value.write_register.assert_called_with(
            2, ord('t'))
        assert controller.instrument.serial.timeout == original_timeout

        # Test to_bottom
        assert controller.to_bottom() is True
        mock_instrument.return_value.write_register.assert_called_with(
            2, ord('b'))
        assert controller.instrument.serial.timeout == original_timeout

    def test_assemble_disassemble_roundtrip(self, controller):
        """Test assemble/disassemble roundtrip."""
        test_value = 0x12345678
        high, low = controller.disassemble(test_value)
        reassembled = controller.assemble(high, low)
        assert reassembled == test_value

    def test_check_position_valid_toggle(self, controller):
        """Test position validation with limits enabled/disabled."""
        # Test with limits enabled
        controller.set_limits_enabled(True)
        assert controller.check_position_valid(
            controller.POSITION_MAX + 1) is False
        assert controller.check_position_valid(
            controller.POSITION_MIN - 1) is False

        # Test with limits disabled
        controller.set_limits_enabled(False)
        assert controller.check_position_valid(
            controller.POSITION_MAX + 1) is True
        assert controller.check_position_valid(
            controller.POSITION_MIN - 1) is True

    def test_set_speed_valid_invalid(self, controller, mock_instrument):
        """Test speed setting with valid and invalid values."""
        controller.start()

        # Test valid speed
        assert controller.set_speed(1000) is True
        mock_instrument.return_value.write_register.assert_called_with(9, 1000)

        # Test invalid speed
        assert controller.set_speed(controller.SPEED_MAX + 1) is False
        assert controller.set_speed(controller.SPEED_MIN - 1) is False

    def test_set_acceleration_valid_invalid(self, controller, mock_instrument):
        """Test acceleration setting with valid and invalid values."""
        controller.start()

        # Test valid acceleration
        assert controller.set_acceleration(1000) is True
        mock_instrument.return_value.write_register.assert_called_with(
            10, 1000)

        # Test invalid acceleration
        assert controller.set_acceleration(controller.ACCEL_MAX + 1) is False
        assert controller.set_acceleration(controller.ACCEL_MIN - 1) is False

    def test_get_velocity_happy(self, controller, mock_instrument):
        """Test successful velocity reading."""
        controller.start()
        mock_instrument.return_value.read_registers.return_value = [
            0x0001, 0x0000]

        velocity = controller.get_velocity()
        assert velocity == 65536.0

    def test_get_velocity_in_progress(self, controller, mock_instrument):
        """Test velocity reading during command execution."""
        controller.start()
        controller._command_in_progress = True

        assert controller.get_velocity() is None

    def test_get_velocity_error(self, controller, mock_instrument):
        """Test velocity reading error handling."""
        controller.start()
        mock_instrument.return_value.read_registers.side_effect = Exception(
            "Read error")

        assert controller.get_velocity() is None
        assert not controller.serial_connected

    def test_set_position_write_error(self, controller, mock_instrument):
        """Test handling of write errors during position setting."""
        controller.start()
        mock_instrument.return_value.write_registers.side_effect = Exception(
            "Write error")
        position = 50.0

        success, actual_pos = controller.set_position(position)
        assert success is False
        assert actual_pos == position  # Should return the attempted position
        assert not controller.serial_connected  # Should mark connection as lost

    def test_set_position_clamp_below_min(self, controller, mock_instrument):
        """Test position clamping below minimum."""
        controller.start()
        position = controller.POSITION_MIN - 10

        success, actual_pos = controller.set_position(position)
        assert success is True
        assert actual_pos == controller.POSITION_MIN
        mock_instrument.return_value.write_registers.assert_called_once()

    def test_calibration_timeout(self, controller, mock_instrument):
        """Test behavior when calibration takes too long (never completes)."""
        controller.start()
        # Simulate calibration never completes
        mock_instrument.return_value.read_bit.return_value = False
        # Should return False and not set _is_calibrated
        assert controller.check_calibrated() is False
        assert not controller._is_calibrated

    def test_calibration_offset_calculation(self, controller, mock_instrument):
        """Verify the offset calculation is correct after calibration."""
        controller.start()
        # Simulate calibration complete
        mock_instrument.return_value.read_bit.return_value = True
        # Simulate register values for offset calculation
        # Let's say the current position is 100.0mm (steps = 100 * 6400 = 640000)
        # high = 640000 // 65536 = 9, low = 640000 % 65536 = 50176
        mock_instrument.return_value.read_registers.return_value = [9, 50176]
        # POSITION_MAX is 324.05, so offset should be (640000/6400) - 324.05 = 100.0 - 324.05 = -224.05
        expected_offset = (640000 / controller.STEPS_PER_MM) - \
            controller.POSITION_MAX
        assert controller.check_calibrated() is True
        assert controller._is_calibrated
        assert abs(controller._initial_offset - expected_offset) < 1e-5

    def test_position_limits_edge_cases(self, controller, mock_instrument):
        """Test behavior at exact min/max positions."""
        controller.start()

        # Test exact minimum position
        success, actual_pos = controller.set_position(controller.POSITION_MIN)
        assert success is True
        assert actual_pos == controller.POSITION_MIN

        # Test exact maximum position
        success, actual_pos = controller.set_position(controller.POSITION_MAX)
        assert success is True
        assert actual_pos == controller.POSITION_MAX

        # Test just below minimum
        success, actual_pos = controller.set_position(
            controller.POSITION_MIN - 0.001)
        assert success is True
        assert actual_pos == controller.POSITION_MIN

        # Test just above maximum
        success, actual_pos = controller.set_position(
            controller.POSITION_MAX + 0.001)
        assert success is True
        assert actual_pos == controller.POSITION_MAX

    def test_speed_limits_edge_cases(self, controller, mock_instrument):
        """Test behavior at min/max speed values."""
        controller.start()

        # Test minimum speed
        assert controller.set_speed(controller.SPEED_MIN) is True
        mock_instrument.return_value.write_register.assert_called_with(
            9, controller.SPEED_MIN)

        # Test maximum speed
        assert controller.set_speed(controller.SPEED_MAX) is True
        mock_instrument.return_value.write_register.assert_called_with(
            9, controller.SPEED_MAX)

        # Test just below minimum
        assert controller.set_speed(controller.SPEED_MIN - 1) is False

        # Test just above maximum
        assert controller.set_speed(controller.SPEED_MAX + 1) is False

    def test_acceleration_limits_edge_cases(self, controller, mock_instrument):
        """Test behavior at min/max acceleration values."""
        controller.start()

        # Test minimum acceleration
        assert controller.set_acceleration(controller.ACCEL_MIN) is True
        mock_instrument.return_value.write_register.assert_called_with(
            10, controller.ACCEL_MIN)

        # Test maximum acceleration
        assert controller.set_acceleration(controller.ACCEL_MAX) is True
        mock_instrument.return_value.write_register.assert_called_with(
            10, controller.ACCEL_MAX)

        # Test just below minimum
        assert controller.set_acceleration(controller.ACCEL_MIN - 1) is False

        # Test just above maximum
        assert controller.set_acceleration(controller.ACCEL_MAX + 1) is False

    def test_reconnect_after_error(self, controller, mock_instrument):
        """Test reconnection after serial errors."""
        controller.start()

        # Simulate a serial error
        mock_instrument.return_value.read_registers.side_effect = Exception(
            "Serial error")
        controller.get_position()  # This should mark connection as lost

        assert not controller.serial_connected

        # Reset the mock to simulate successful reconnection
        mock_instrument.return_value.read_registers.side_effect = None
        mock_instrument.return_value.read_registers.return_value = [0, 0]

        # Try to reconnect
        assert controller.start() is True
        assert controller.serial_connected

    def test_error_count_reset(self, controller, mock_instrument):
        """Test error handling and recovery after multiple errors."""
        controller.start()

        # Generate some errors
        mock_instrument.return_value.read_registers.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            [0, 0]  # Success on third try
        ]

        # First two calls should return 0.0 on error
        assert controller.get_position() == 0.0  # First error
        assert controller.get_position() == 0.0  # Second error
        assert not controller.serial_connected  # Connection should be marked as lost

        # Reset the mock to simulate successful reconnection
        mock_instrument.return_value.read_registers.side_effect = None
        mock_instrument.return_value.read_registers.return_value = [0, 0]

        # Reconnect
        assert controller.start() is True
        assert controller.serial_connected  # Connection should be restored

        # Verify we can read position after reconnection
        position = controller.get_position()
        assert position is not None

    def test_consecutive_errors_handling(self, controller, mock_instrument):
        """Test handling of different types of consecutive errors."""
        controller.start()

        # Simulate different types of errors
        mock_instrument.return_value.read_registers.side_effect = [
            Exception("Serial error"),
            Exception("Timeout error"),
            Exception("CRC error"),
            [0, 0]  # Success on fourth try
        ]

        # First three calls should return 0.0 on error
        assert controller.get_position() == 0.0  # Serial error
        assert controller.get_position() == 0.0  # Timeout error
        assert controller.get_position() == 0.0  # CRC error

        # Fourth call should succeed
        position = controller.get_position()
        assert position is not None

        # Verify we can still perform operations after errors
        assert controller.set_position(100.0)[0] is True
