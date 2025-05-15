"""
File: tests/test_controllers/test_arduino_controller.py
Description: Tests for Arduino controller functionality
"""

import pytest
from unittest.mock import Mock, patch
import minimalmodbus
import logging
from src.controllers.arduino_controller import ArduinoController


class TestArduinoController:
    """Test suite for ArduinoController class."""

    @pytest.fixture
    def mock_instrument(self):
        """Create mock Modbus instrument."""
        with patch('minimalmodbus.Instrument', autospec=True) as mock:
            instance = Mock()
            mock.return_value = instance
            instance.read_registers.return_value = [
                0, 0, 0, 0]  # Default pressure readings
            instance.read_bits.return_value = [0] * 8  # Default valve states
            instance.write_bit.return_value = None
            instance.write_bits.return_value = None
            instance.serial.baudrate = 9600
            instance.serial.timeout = 0.05
            yield mock

    @pytest.fixture
    def controller(self, mock_instrument):
        """Create controller with mock instrument."""
        return ArduinoController(port=1)

    @pytest.fixture
    def ttl_controller(self):
        """Create controller in TTL mode."""
        return ArduinoController(port=1, mode=2)

    @pytest.fixture
    def debug_controller(self, caplog):
        """Create controller with debug logging."""
        caplog.set_level(logging.DEBUG)
        return ArduinoController(port=1, verbose=True), caplog

    def test_init_normal_mode_success(self, mock_instrument):
        """Test successful initialization in normal mode."""
        controller = ArduinoController(port=1)
        assert controller.start() is True
        assert controller.running is True
        assert controller.mode == 0
        assert len(controller._valve_states) == 8
        assert all(v == 0 for v in controller._valve_states)

    def test_init_ttl_mode_success(self, mock_instrument):
        """Test successful initialization in TTL mode."""
        controller = ArduinoController(port=1, mode=2)
        assert controller.start() is True
        assert controller.running is True
        assert controller.mode == 2
        mock_instrument.return_value.write_bit.assert_called_with(
            16, 1)  # TTL_ADDRESS

    def test_init_fail(self, mock_instrument):
        """Test initialization failure."""
        controller = ArduinoController(port=1)
        mock_instrument.return_value.read_registers.side_effect = Exception(
            "Connection error")
        assert controller.start() is False
        assert controller.running is False

    def test_get_readings_success(self, controller, mock_instrument):
        """Test successful pressure readings."""
        controller.start()
        mock_instrument.return_value.read_registers.return_value = [
            1000, 2000, 3000, 4000]

        readings = controller.get_readings()
        assert readings is not None
        assert len(readings) == 4
        # Verify conversion formula: (raw - 203.53) / 0.8248 / 100
        expected = [(1000 - 203.53) / 0.8248 / 100]
        assert abs(readings[0] - expected[0]) < 0.01

    def test_get_readings_error(self, controller, mock_instrument):
        """Test pressure readings error handling."""
        controller.start()
        mock_instrument.return_value.read_registers.side_effect = Exception(
            "Read error")

        readings = controller.get_readings()
        assert readings is None
        assert not controller.running

    def test_get_readings_boundary_values(self, controller, mock_instrument):
        """Test pressure readings with boundary values."""
        controller.start()
        # Test minimum possible value (0)
        mock_instrument.return_value.read_registers.return_value = [0, 0, 0, 0]
        readings = controller.get_readings()
        assert readings is not None
        assert all(r < 0 for r in readings)  # Should be negative due to offset

        # Test maximum possible value (65535)
        mock_instrument.return_value.read_registers.return_value = [
            65535, 65535, 65535, 65535]
        readings = controller.get_readings()
        assert readings is not None
        assert all(r > 0 for r in readings)

    def test_set_valves_success(self, controller, mock_instrument):
        """Test successful valve state setting."""
        controller.start()
        new_states = [1, 0, 1, 0, 1, 0, 1, 0]

        assert controller.set_valves(new_states) is True
        mock_instrument.return_value.write_bits.assert_called_with(
            0, new_states)
        assert controller._valve_states == new_states

    def test_set_valves_invalid_states(self, controller):
        """Test valve state setting with invalid input."""
        controller.start()

        # Test wrong length
        assert controller.set_valves([1, 0, 1]) is False

        # Test invalid values
        assert controller.set_valves([1, 2, 0, 1, 0, 1, 0, 1]) is False

    def test_set_valves_error(self, controller, mock_instrument):
        """Test valve state setting error handling."""
        controller.start()
        mock_instrument.return_value.write_bits.side_effect = Exception(
            "Write error")

        assert controller.set_valves([1] * 8) is False
        assert not controller.running

    def test_set_valves_partial_update(self, controller, mock_instrument):
        """Test setting only some valves while keeping others unchanged."""
        controller.start()
        # Set initial state
        initial_states = [1, 0, 1, 0, 1, 0, 1, 0]
        controller.set_valves(initial_states)

        # Update only some valves
        new_states = [0, 0, 1, 1, 1, 0, 1, 0]
        assert controller.set_valves(new_states) is True
        assert controller._valve_states == new_states

    def test_consecutive_valve_operations(self, controller, mock_instrument):
        """Test multiple valve operations in sequence."""
        controller.start()
        states_sequence = [
            [1, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 0, 0, 0, 0, 0]
        ]

        for states in states_sequence:
            assert controller.set_valves(states) is True
            assert controller._valve_states == states

    def test_error_recovery_after_read_failure(self, controller, mock_instrument):
        """Test recovery after pressure reading failure."""
        controller.start()
        # Simulate initial failure
        mock_instrument.return_value.read_registers.side_effect = Exception(
            "Read error")
        assert controller.get_readings() is None
        assert not controller.running

        # Reset mock and try to recover
        mock_instrument.return_value.read_registers.side_effect = None
        mock_instrument.return_value.read_registers.return_value = [
            1000, 1000, 1000, 1000]
        assert controller.start() is True
        readings = controller.get_readings()
        assert readings is not None

    def test_reset_success(self, controller, mock_instrument):
        """Test successful system reset."""
        controller.start()
        assert controller.reset() is True
        mock_instrument.return_value.write_bit.assert_called_with(
            17, 1)  # RESET_ADDRESS
        assert all(v == 0 for v in controller._valve_states)

    def test_depressurize_success(self, controller, mock_instrument):
        """Test successful system depressurization."""
        controller.start()
        assert controller.depressurize() is True
        mock_instrument.return_value.write_bit.assert_called_with(
            18, 1)  # DEPRESSURIZE_ADDRESS
        assert all(v == 0 for v in controller._valve_states)

    def test_get_valve_states(self, controller):
        """Test getting current valve states."""
        controller.start()
        states = controller.get_valve_states()
        assert len(states) == 8
        assert all(v == 0 for v in states)

    def test_verify_valve_states_match(self, controller, mock_instrument):
        """Test valve state verification when states match."""
        controller.start()
        mock_instrument.return_value.read_bits.return_value = [0] * 8

        controller._verify_valve_states()
        assert controller._valve_states == [0] * 8

    def test_verify_valve_states_mismatch(self, controller, mock_instrument):
        """Test valve state verification when states don't match."""
        controller.start()
        mock_instrument.return_value.read_bits.return_value = [1] * 8

        controller._verify_valve_states()
        assert controller._valve_states == [1] * 8

    def test_valve_verification_timer(self, controller, mock_instrument):
        """Test valve state verification timer functionality."""
        controller.start()
        assert controller.valve_check_timer.isActive()
        assert controller.valve_check_timer.interval() == 1000  # 1 second interval

        # Simulate state mismatch
        mock_instrument.return_value.read_bits.return_value = [1] * 8
        controller._verify_valve_states()
        assert controller._valve_states == [1] * 8

    def test_stop_cleanup(self, controller, mock_instrument):
        """Test proper cleanup on stop."""
        controller.start()
        controller.stop()

        assert not controller.running
        assert not controller.valve_check_timer.isActive()
        mock_instrument.return_value.serial.close.assert_called_once()

    def test_stop_ttl_mode(self, ttl_controller, mock_instrument):
        """Test proper cleanup in TTL mode."""
        ttl_controller.start()
        ttl_controller.stop()

        mock_instrument.return_value.write_bit.assert_called_with(
            16, 0)  # Disable TTL
        assert not ttl_controller.running

    def test_multiple_reset_operations(self, controller, mock_instrument):
        """Test multiple reset operations in sequence."""
        controller.start()
        # Set some valve states
        controller.set_valves([1] * 8)
        assert any(v == 1 for v in controller._valve_states)

        # Perform multiple resets
        for _ in range(3):
            assert controller.reset() is True
            assert all(v == 0 for v in controller._valve_states)

    def test_depressurize_after_valve_operations(self, controller, mock_instrument):
        """Test depressurization after valve operations."""
        controller.start()
        # Set some valves
        controller.set_valves([1, 0, 1, 0, 1, 0, 1, 0])
        assert any(v == 1 for v in controller._valve_states)

        # Depressurize
        assert controller.depressurize() is True
        assert all(v == 0 for v in controller._valve_states)

    def test_ttl_mode_transition(self, controller, mock_instrument):
        """Test transitioning between TTL and normal modes."""
        controller.start()
        # Switch to TTL mode
        controller.mode = 2
        assert controller.start() is True
        mock_instrument.return_value.write_bit.assert_called_with(16, 1)

        # Switch back to normal mode
        controller.mode = 0
        assert controller.start() is True
        mock_instrument.return_value.write_bit.assert_called_with(16, 0)

    def test_serial_connection_parameters(self, controller, mock_instrument):
        """Test serial connection parameters are set correctly."""
        controller.start()
        assert mock_instrument.return_value.serial.baudrate == 9600
        assert mock_instrument.return_value.serial.timeout == 0.05

    def test_valve_state_consistency(self, controller, mock_instrument):
        """Test that valve state remains consistent after operations."""
        controller.start()
        states1 = [1, 0, 1, 0, 1, 0, 1, 0]
        controller.set_valves(states1)
        assert controller.get_valve_states() == states1
        states2 = [0, 1, 0, 1, 0, 1, 0, 1]
        controller.set_valves(states2)
        assert controller.get_valve_states() == states2
        controller.reset()
        assert controller.get_valve_states() == [0] * 8
        controller.set_valves([1] * 8)
        controller.depressurize()
        assert controller.get_valve_states() == [0] * 8

    def test_set_valves_invalid_length(self, controller):
        """Test set_valves with invalid length input."""
        controller.start()
        # Too short
        assert controller.set_valves([1, 0, 1]) is False
        # Too long
        assert controller.set_valves([1] * 9) is False
        # Empty
        assert controller.set_valves([]) is False

    def test_set_valves_invalid_values(self, controller):
        """Test set_valves with invalid values."""
        controller.start()
        # Value not 0 or 1
        assert controller.set_valves([1, 0, 2, 0, 1, 0, 1, 0]) is False
        assert controller.set_valves([1, 0, -1, 0, 1, 0, 1, 0]) is False
        # Non-integer
        assert controller.set_valves([1, 0, 0.5, 0, 1, 0, 1, 0]) is False
        assert controller.set_valves([1, 0, 'a', 0, 1, 0, 1, 0]) is False

    def test_multiple_start_stop_cycles(self, controller, mock_instrument):
        """Test multiple start/stop cycles do not cause errors."""
        for _ in range(3):
            assert controller.start() is True
            assert controller.running is True
            controller.stop()
            assert controller.running is False

    def test_ttl_mode_transitions(self, mock_instrument):
        """Test TTL mode transitions send correct Modbus commands."""
        controller = ArduinoController(port=1, mode=0)
        assert controller.start() is True
        mock_instrument.return_value.write_bit.assert_called_with(16, 0)
        controller.stop()
        controller = ArduinoController(port=1, mode=2)
        assert controller.start() is True
        mock_instrument.return_value.write_bit.assert_called_with(16, 1)
        controller.stop()

    def test_reset_and_depressurize_close_valves(self, controller, mock_instrument):
        """Test reset and depressurize always close all valves."""
        controller.start()
        controller.set_valves([1] * 8)
        assert any(v == 1 for v in controller.get_valve_states())
        controller.reset()
        assert all(v == 0 for v in controller.get_valve_states())
        controller.set_valves([1] * 8)
        controller.depressurize()
        assert all(v == 0 for v in controller.get_valve_states())

    def test_pressure_conversion_edge_cases(self, controller, mock_instrument):
        """Test get_readings with extreme and negative raw values."""
        controller.start()
        # Negative value
        mock_instrument.return_value.read_registers.return_value = [
            -100, -100, -100, -100]
        readings = controller.get_readings()
        assert readings is not None
        assert all(isinstance(r, float) for r in readings)
        # Very large value
        mock_instrument.return_value.read_registers.return_value = [
            100000, 100000, 100000, 100000]
        readings = controller.get_readings()
        assert readings is not None
        assert all(isinstance(r, float) for r in readings)

    def test_timer_thread_safety(self, controller, mock_instrument):
        """Test that stopping the controller stops the timer without error."""
        controller.start()
        assert controller.valve_check_timer.isActive()
        controller.stop()
        assert not controller.valve_check_timer.isActive()
