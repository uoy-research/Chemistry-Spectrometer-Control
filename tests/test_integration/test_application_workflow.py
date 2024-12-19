"""
File: tests/test_integration/test_application_workflow.py
Description: Integration tests for complete application workflows
"""

import pytest
from unittest.mock import Mock, patch, PropertyMock
import json
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMessageBox
import logging

from src.ui.main_window import MainWindow
from src.models.valve_macro import MacroManager
from src.models.step import Step

# ===== Fixtures =====


@pytest.fixture
def mock_hardware():
    """Mock hardware controllers."""
    with patch('src.controllers.arduino_controller.ArduinoController') as arduino_mock, \
            patch('src.controllers.motor_controller.MotorController') as motor_mock:

        # Setup Arduino mock
        arduino = arduino_mock.return_value
        arduino.start.return_value = True
        arduino.get_readings.return_value = [1.0, 2.0, 3.0]
        arduino.set_valves.return_value = True

        # Setup Motor mock
        motor = motor_mock.return_value
        motor.start.return_value = True
        motor.get_position.return_value = 500
        motor.set_position.return_value = True

        yield arduino, motor


@pytest.fixture
def setup_environment(tmp_path):
    """Setup test environment with necessary files."""
    # Create config
    config = {
        "arduino_port": 1,
        "motor_port": 2,
        "macro_file": str(tmp_path / "macros.json"),
        "log_level": "DEBUG",  # Changed to DEBUG for better test output
        "update_interval": 100,
        "max_data_points": 1000
    }

    # Create files
    config_file = tmp_path / "config.json"
    macro_file = tmp_path / "macros.json"
    log_dir = tmp_path / "logs"

    config_file.write_text(json.dumps(config))
    macro_file.write_text("{}")
    log_dir.mkdir()

    return {
        "config_file": config_file,
        "macro_file": macro_file,
        "log_dir": log_dir,
        "config": config
    }


@pytest.fixture
def app_window(qtbot, setup_environment, mock_hardware):
    """Create main application window with mocked hardware."""
    env = setup_environment

    with patch('src.utils.config.CONFIG_FILE', str(env["config_file"])), \
            patch('src.utils.logger.LOG_DIR', str(env["log_dir"])), \
            patch('src.controllers.arduino_controller.ArduinoController'), \
            patch('src.controllers.motor_controller.MotorController'):

        window = MainWindow()
        window.show()  # Important for Qt signals
        qtbot.addWidget(window)
        qtbot.waitExposed(window)  # Wait for window to be shown

        return window

# ===== Test Cases =====


def test_startup_workflow(app_window, qtbot):
    """Test complete startup workflow."""
    # Verify initial state
    assert not app_window.arduino_worker.running
    assert not app_window.motor_worker.running

    # Connect hardware
    qtbot.mouseClick(app_window.arduino_connect_btn, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(app_window.motor_connect_btn, Qt.MouseButton.LeftButton)

    qtbot.wait(100)  # Wait for connections

    # Verify connections
    assert app_window.arduino_worker.running
    assert app_window.motor_worker.running
    assert "Connected" in app_window.log_widget.toPlainText()


def test_measurement_workflow(app_window, qtbot, mock_hardware):
    """Test complete measurement workflow."""
    arduino_mock, _ = mock_hardware

    # Setup mock readings
    readings = [1.0, 2.0, 3.0]
    arduino_mock.get_readings.return_value = readings

    # Start measurement
    qtbot.mouseClick(app_window.arduino_connect_btn, Qt.MouseButton.LeftButton)
    qtbot.wait(200)  # Wait for readings

    # Verify plot updated
    assert len(app_window.plot_widget.timestamps) > 0
    assert all(len(data) > 0 for data in app_window.plot_widget.pressure_data)

    # Test data export
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
               return_value=("test.csv", "CSV Files (*.csv)")):
        qtbot.mouseClick(app_window.plot_widget.export_btn,
                         Qt.MouseButton.LeftButton)
        qtbot.wait(100)
        assert "Data exported" in app_window.log_widget.toPlainText()


def test_error_recovery_workflow(app_window, qtbot, mock_hardware):
    """Test error recovery workflow."""
    arduino_mock, _ = mock_hardware
    
    # Modify the mock to ensure the error propagates through the worker
    error_msg = "Connection failed"
    app_window.arduino_worker.start = lambda: exec('raise Exception("' + error_msg + '")')
    
    # Try connection
    qtbot.mouseClick(app_window.arduino_connect_btn, Qt.MouseButton.LeftButton)
    qtbot.wait(200)
    
    # Verify error state
    assert not app_window.arduino_worker.running
    assert error_msg in app_window.log_widget.toPlainText()


def test_shutdown_workflow(app_window, qtbot):
    """Test complete shutdown workflow."""
    # Start components
    qtbot.mouseClick(app_window.arduino_connect_btn, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(app_window.motor_connect_btn, Qt.MouseButton.LeftButton)
    qtbot.wait(100)

    # Simulate close with save
    with patch.object(QMessageBox, 'question',
                      return_value=QMessageBox.StandardButton.Yes):
        app_window.close()
        qtbot.wait(100)

    # Verify cleanup
    assert not app_window.arduino_worker.running
    assert not app_window.motor_worker.running
    assert "Shutdown complete" in app_window.log_widget.toPlainText()
