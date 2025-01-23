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
import time

from src.ui.main_window import MainWindow
from src.models.step import Step


class TestApplicationWorkflow:
    """Test suite for application workflows."""

    @pytest.fixture
    def mock_hardware(self):
        """Mock hardware controllers."""
        with patch('src.controllers.arduino_controller.ArduinoController') as arduino_mock, \
             patch('src.controllers.motor_controller.MotorController') as motor_mock:

            # Setup Arduino mock
            arduino = arduino_mock.return_value
            arduino.start.return_value = True
            arduino.get_readings.return_value = [1.0, 2.0, 3.0]
            arduino.set_valves.return_value = True
            arduino.running = True

            # Setup Motor mock
            motor = motor_mock.return_value
            motor.start.return_value = True
            motor.get_position.return_value = 500
            motor.set_position.return_value = True
            motor.running = True

            yield arduino, motor

    @pytest.fixture
    def setup_environment(self, tmp_path):
        """Setup test environment with necessary files."""
        # Create directories
        data_dir = tmp_path / "ssbubble" / "data"
        data_dir.mkdir(parents=True)
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # Create sequence file
        sequence_file = tmp_path / "ssbubble" / "sequence.txt"
        sequence_file.parent.mkdir(exist_ok=True)
        sequence_file.write_text("Md1000m500p2000m-200b1000m0v1000\nC:/test/data.csv")

        # Create config
        config = {
            "arduino_port": 1,
            "motor_port": 2,
            "log_level": "DEBUG",
            "update_interval": 100,
            "max_data_points": 1000
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        return {
            "data_dir": data_dir,
            "log_dir": log_dir,
            "sequence_file": sequence_file,
            "config_file": config_file
        }

    @pytest.fixture
    def app_window(self, qtbot, setup_environment, mock_hardware):
        """Create main application window with mocked hardware."""
        with patch('src.utils.logger.LOG_DIR', setup_environment["log_dir"]), \
             patch.dict('os.environ', {'SSBUBBLE_DATA': str(setup_environment["data_dir"])}):
            
            window = MainWindow(test_mode=True)
            window.show()
            qtbot.addWidget(window)
            qtbot.waitExposed(window)
            return window

    def test_startup_workflow(self, app_window, qtbot):
        """Test complete startup workflow."""
        # Verify initial state
        assert not app_window.arduino_worker.running
        assert not app_window.motor_worker.running

        # Connect hardware
        qtbot.mouseClick(app_window.arduino_connect_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(app_window.motor_connect_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(100)

        # Verify connections and UI state
        assert app_window.arduino_worker.running
        assert app_window.motor_worker.running
        assert "Connected" in app_window.log_widget.toPlainText()
        assert app_window.dev_checkbox.isEnabled()

    def test_sequence_execution_workflow(self, app_window, qtbot, setup_environment):
        """Test complete sequence execution workflow."""
        # Start workers
        app_window.arduino_worker.start()
        app_window.motor_worker.start()
        qtbot.wait(100)

        # Load and start sequence
        sequence_text = "p1000v1000b1000"  # Simple test sequence
        with patch('pathlib.Path.read_text', return_value=sequence_text):
            app_window.load_sequence()
            app_window.start_sequence()
            qtbot.wait(3500)  # Wait for sequence completion

        # Verify sequence execution
        assert len(app_window.steps) == 0  # Sequence completed
        log_text = app_window.log_widget.toPlainText()
        assert "Sequence execution completed" in log_text

    def test_data_recording_workflow(self, app_window, qtbot, setup_environment):
        """Test data recording workflow."""
        # Start recording
        test_file = setup_environment["data_dir"] / "test_data.csv"
        app_window.savePathEdit.setText(str(test_file))
        qtbot.mouseClick(app_window.beginSaveButton, Qt.MouseButton.LeftButton)
        
        # Generate some data
        for _ in range(5):
            app_window.handle_pressure_readings([1.0, 2.0, 3.0, 4.0])
            qtbot.wait(50)

        # Stop recording
        qtbot.mouseClick(app_window.beginSaveButton, Qt.MouseButton.LeftButton)
        
        # Verify data saved
        assert test_file.exists()
        assert test_file.stat().st_size > 0

    def test_error_recovery_workflow(self, app_window, qtbot, mock_hardware):
        """Test error recovery workflow."""
        arduino_mock, motor_mock = mock_hardware
        
        # Simulate connection error
        arduino_mock.start.side_effect = [Exception("Connection failed"), True]
        
        # First attempt fails
        qtbot.mouseClick(app_window.arduino_connect_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(100)
        assert not app_window.arduino_worker.running
        assert "Connection failed" in app_window.log_widget.toPlainText()
        
        # Second attempt succeeds
        qtbot.mouseClick(app_window.arduino_connect_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(100)
        assert app_window.arduino_worker.running

    def test_emergency_handling_workflow(self, app_window, qtbot):
        """Test emergency handling workflow."""
        # Start normal operation
        app_window.arduino_worker.start()
        app_window.motor_worker.start()
        app_window.steps = [Step('p', 1000), Step('v', 1000)]
        app_window.start_sequence()
        qtbot.wait(100)

        # Trigger emergency stop
        qtbot.mouseClick(app_window.motor_stop_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(100)

        # Verify emergency handling
        assert not app_window.motor_worker.running
        assert len(app_window.steps) == 0  # Sequence aborted
        assert "emergency" in app_window.log_widget.toPlainText().lower()

    def test_shutdown_workflow(self, app_window, qtbot):
        """Test complete shutdown workflow."""
        # Start components
        app_window.arduino_worker.start()
        app_window.motor_worker.start()
        app_window.plot_widget.start_recording("test.csv")
        qtbot.wait(100)

        # Close application
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            app_window.close()
            qtbot.wait(100)

        # Verify cleanup
        assert not app_window.arduino_worker.running
        assert not app_window.motor_worker.running
        assert not app_window.plot_widget.recording
        assert "Shutdown complete" in app_window.log_widget.toPlainText()
