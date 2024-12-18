"""
File: test_main_window.py
Description: Tests for main application window
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from src.ui.main_window import MainWindow
from src.models.valve_macro import MacroManager


@pytest.fixture
def app():
    """Create QApplication instance."""
    return QApplication([])


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    with patch('src.utils.config.Config') as mock:
        config = mock.return_value
        config.arduino_port = 1
        config.motor_port = 2
        config.macro_file = "test_macros.json"
        yield config


@pytest.fixture
def mock_workers():
    """Create mock workers."""
    with patch('src.workers.arduino_worker.ArduinoWorker') as mock_arduino, \
            patch('src.workers.motor_worker.MotorWorker') as mock_motor:

        arduino = mock_arduino.return_value
        motor = mock_motor.return_value

        yield arduino, motor


@pytest.fixture
def window(app, mock_config, mock_workers):
    """Create main window instance."""
    return MainWindow()


def test_initialization(window, mock_workers):
    """Test window initialization."""
    arduino_worker, motor_worker = mock_workers

    assert window.windowTitle() == "SSBubble Control"
    assert hasattr(window, 'arduino_worker')
    assert hasattr(window, 'motor_worker')

    # Verify workers started
    arduino_worker.start.assert_called_once()
    motor_worker.start.assert_called_once()


def test_arduino_connection(window, mock_workers):
    """Test Arduino connection handling."""
    arduino_worker, _ = mock_workers

    # Test connect
    window.handle_arduino_connection()
    arduino_worker.start.assert_called()

    # Test disconnect
    window.handle_arduino_connection()
    arduino_worker.stop.assert_called()


def test_motor_connection(window, mock_workers):
    """Test motor connection handling."""
    _, motor_worker = mock_workers

    # Test connect
    window.handle_motor_connection()
    motor_worker.start.assert_called()

    # Test disconnect
    window.handle_motor_connection()
    motor_worker.stop.assert_called()


def test_macro_editor(window):
    """Test macro editor dialog."""
    with patch('src.ui.dialogs.macro_editor.MacroEditor') as mock_editor:
        # Configure mock
        editor_instance = mock_editor.return_value
        editor_instance.exec.return_value = True

        # Show editor
        window.show_macro_editor()

        # Verify editor created and shown
        mock_editor.assert_called_once()
        editor_instance.exec.assert_called_once()


def test_run_macro(window, mock_workers):
    """Test running macro."""
    arduino_worker, _ = mock_workers

    # Add test macro
    test_macro = Mock()
    test_macro.valve_states = [0] * 8
    test_macro.label = "Test Macro"

    with patch.object(window.macro_manager, 'get_macro', return_value=test_macro):
        # Run macro
        window.run_macro()

        # Verify valve states sent
        arduino_worker.set_valves.assert_called_with([0] * 8)


def test_stop_macro(window, mock_workers):
    """Test stopping macro."""
    arduino_worker, _ = mock_workers

    # Stop macro
    window.stop_macro()

    # Verify all valves closed
    arduino_worker.set_valves.assert_called_with([0] * 8)


def test_motor_controls(window, mock_workers):
    """Test motor control functions."""
    _, motor_worker = mock_workers

    # Test move to position
    window.position_spin.setValue(100)
    window.move_motor()
    motor_worker.move_to.assert_called_with(100)

    # Test home
    window.home_motor()
    motor_worker.home.assert_called_once()

    # Test speed
    window.speed_spin.setValue(500)
    window.set_motor_speed()
    motor_worker.set_speed.assert_called_with(500)


def test_emergency_stop(window, mock_workers):
    """Test emergency stop functionality."""
    arduino_worker, motor_worker = mock_workers

    with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
        # Trigger emergency stop
        window.emergency_stop()

        # Verify actions
        motor_worker.stop.assert_called_once()
        arduino_worker.depressurize.assert_called_once()
        mock_warning.assert_called_once()


def test_close_event(window, mock_workers):
    """Test application shutdown."""
    arduino_worker, motor_worker = mock_workers

    # Create mock event
    event = Mock()

    # Trigger close
    window.closeEvent(event)

    # Verify workers stopped
    arduino_worker.stop.assert_called_once()
    motor_worker.stop.assert_called_once()
    event.accept.assert_called_once()


def test_error_handling(window):
    """Test error handling."""
    with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_critical:
        # Trigger error
        window.handle_error("Test error")
        mock_critical.assert_called_once()


@pytest.mark.parametrize("readings", [
    [1.0, 2.0, 3.0],
    [0.0, 0.0, 0.0],
    [-1.0, 1.0, -1.0],
])
def test_pressure_updates(window, readings):
    """Test pressure reading updates."""
    # Mock plot widget
    window.plot_widget.update_plot = Mock()

    # Send readings
    window.handle_pressure_readings(readings)

    # Verify plot updated
    window.plot_widget.update_plot.assert_called_with(readings)


def test_status_updates(window):
    """Test status message handling."""
    # Mock log widget
    window.log_widget.add_message = Mock()

    # Send status
    test_message = "Test status"
    window.handle_status_message(test_message)

    # Verify log updated
    window.log_widget.add_message.assert_called()


def test_worker_error_handling(window):
    """Test worker error handling."""
    with patch.object(window, 'handle_error') as mock_handle:
        # Send error from worker
        test_error = "Worker error"
        window.handle_worker_error(test_error)

        # Verify error handled
        mock_handle.assert_called_with(test_error)
