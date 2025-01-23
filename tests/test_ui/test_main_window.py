"""
File: test_main_window.py
Description: Tests for main application window
"""

import pytest
from unittest.mock import Mock, patch, mock_open, call
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from pathlib import Path
import json

from src.ui.main_window import MainWindow
from src.models.step import Step


@pytest.fixture
def app(qapp):
    """Use the qapp fixture from conftest."""
    return qapp


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    with patch('src.utils.config.Config') as mock:
        config = mock.return_value
        config.arduino_port = 1
        config.motor_port = 2
        config.macro_file = "test_macros.json"
        config.max_data_points = 1000
        config.update_interval = 100
        yield config


@pytest.fixture
def mock_workers():
    """Create mock workers."""
    with patch('src.workers.arduino_worker.ArduinoWorker') as mock_arduino, \
         patch('src.workers.motor_worker.MotorWorker') as mock_motor:
        
        arduino = mock_arduino.return_value
        arduino.running = False
        arduino.controller.mode = 0
        motor = mock_motor.return_value
        motor.running = False
        
        yield arduino, motor


@pytest.fixture
def window(app, mock_config, mock_workers):
    """Create main window instance with test mode enabled."""
    with patch('src.ui.main_window.PlotWidget'), \
         patch('src.ui.main_window.LogWidget'):
        window = MainWindow(test_mode=True)
        yield window


def test_initialization(window, mock_workers):
    """Test window initialization."""
    arduino_worker, motor_worker = mock_workers
    
    assert window.windowTitle() == "SSBubble Control"
    assert window.test_mode is True
    assert hasattr(window, 'arduino_worker')
    assert hasattr(window, 'motor_worker')


def test_load_sequence_valid(window, tmp_path):
    """Test loading a valid sequence file."""
    sequence_file = tmp_path / "sequence.txt"
    sequence_content = "d100m500\nC:/test/path\n"
    
    with patch('builtins.open', mock_open(read_data=sequence_content)):
        with patch('pathlib.Path.exists', return_value=True):
            assert window.load_sequence() is True
            assert len(window.steps) == 1
            assert window.steps[0].step_type == 'd'
            assert window.steps[0].time_length == 100
            assert window.steps[0].motor_position == 500


def test_load_sequence_invalid(window):
    """Test loading an invalid sequence file."""
    with patch('builtins.open', mock_open(read_data="invalid sequence")):
        assert window.load_sequence() is False
        assert len(window.steps) == 0


def test_execute_step(window, mock_workers):
    """Test executing a sequence step."""
    arduino_worker, motor_worker = mock_workers
    
    step = Step(step_type='b', time_length=100, motor_position=500)
    window.execute_step(step)
    
    # Verify valve states for bubble step
    arduino_worker.set_valves.assert_called_once()
    if window.motor_flag:
        motor_worker.move_to.assert_called_with(500)


def test_emergency_stop(window, mock_workers):
    """Test emergency stop functionality."""
    arduino_worker, motor_worker = mock_workers
    
    window.emergency_stop()
    
    motor_worker.stop.assert_called_once()
    arduino_worker.depressurize.assert_called_once()


def test_valve_controls(window, mock_workers):
    """Test valve control functionality."""
    arduino_worker, _ = mock_workers
    
    # Test enabling controls
    window.toggle_valve_controls(True)
    for button in window.valve_buttons:
        assert button.isEnabled()
    
    # Test disabling controls
    window.toggle_valve_controls(False)
    for button in window.valve_buttons:
        assert not button.isEnabled()


def test_handle_sequence_file(window, tmp_path):
    """Test sequence file handling."""
    sequence_path = tmp_path / "sequence.txt"
    prospa_path = tmp_path / "prospa.txt"
    
    with patch('pathlib.Path') as mock_path:
        mock_path.return_value = sequence_path
        window.handle_sequence_file(True)
        
        # Verify prospa file written with success status
        assert prospa_path.exists()


def test_close_event(window, mock_workers):
    """Test application shutdown."""
    arduino_worker, motor_worker = mock_workers
    
    # Create mock event
    event = Mock()
    
    # Trigger close
    window.closeEvent(event)
    
    # Verify cleanup
    arduino_worker.stop.assert_called_once()
    motor_worker.stop.assert_called_once()
    event.accept.assert_called_once()


def test_start_sequence(window, mock_workers):
    """Test sequence start functionality."""
    arduino_worker, motor_worker = mock_workers
    arduino_worker.running = True
    
    # Setup test sequence
    window.steps = [
        Step('p', 1000),  # Pressurize for 1 second
        Step('v', 500)    # Vent for 0.5 seconds
    ]
    
    with patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
        window.start_sequence()
        
        # Verify first step execution
        assert len(window.steps) == 2
        arduino_worker.set_valves.assert_called_once()
        mock_timer.assert_called_once_with(1000, window.next_step)


def test_next_step(window, mock_workers):
    """Test sequence step progression."""
    arduino_worker, _ = mock_workers
    arduino_worker.running = True
    
    # Setup test sequence
    window.steps = [
        Step('v', 500),    # Vent for 0.5 seconds
        Step('d', 1000)    # Delay for 1 second
    ]
    
    with patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
        window.next_step()
        
        # Verify step progression
        assert len(window.steps) == 1
        assert window.steps[0].step_type == 'd'
        arduino_worker.set_valves.assert_called_once()


def test_sequence_completion(window, mock_workers):
    """Test sequence completion handling."""
    arduino_worker, _ = mock_workers
    arduino_worker.running = True
    
    # Setup final step
    window.steps = [Step('d', 1000)]
    window.saving = True
    window.step_timer = Mock()
    
    with patch.object(window.plot_widget, 'stop_recording') as mock_stop_recording:
        window.next_step()
        
        # Verify cleanup
        assert len(window.steps) == 0
        assert not window.saving
        window.step_timer.stop.assert_called_once()
        mock_stop_recording.assert_called_once()


def test_load_valve_macro(window):
    """Test valve macro loading."""
    mock_macro_data = [
        {
            "Macro No.": "Macro 1",
            "Label": "Test Macro",
            "Valves": ["Open", "Closed", "Open", "Closed", "Closed"],
            "Timer": 2.0
        }
    ]
    
    with patch('builtins.open', mock_open(read_data=json.dumps(mock_macro_data))), \
         patch('pathlib.Path.exists', return_value=True):
        macro = window.load_valve_macro(1)
        
        assert macro is not None
        assert macro["Label"] == "Test Macro"
        assert macro["Timer"] == 2.0


def test_execute_valve_macro(window, mock_workers):
    """Test valve macro execution."""
    arduino_worker, _ = mock_workers
    arduino_worker.running = True
    
    mock_macro = {
        "Macro No.": "Macro 1",
        "Label": "Test Macro",
        "Valves": ["Open", "Closed", "Open", "Closed", "Closed"],
        "Timer": 0.5
    }
    
    with patch.object(window, 'load_valve_macro', return_value=mock_macro), \
         patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
        window.on_valveMacroButton_clicked(1)
        
        # Verify valve states set
        arduino_worker.set_valves.assert_called_once_with([1, 0, 1, 0, 0, 0, 0, 0])
        # Verify timer setup for auto-reset
        mock_timer.assert_called_once()


def test_load_motor_macro(window):
    """Test motor macro loading."""
    mock_macro_data = [
        {
            "Macro No.": "Macro 1",
            "Label": "Position 1",
            "Position": 500,
            "Description": "Test position"
        }
    ]
    
    with patch('builtins.open', mock_open(read_data=json.dumps(mock_macro_data))), \
         patch('pathlib.Path.exists', return_value=True):
        macro = window.load_motor_macro(1)
        
        assert macro is not None
        assert macro["Label"] == "Position 1"
        assert macro["Position"] == 500


def test_execute_motor_macro(window, mock_workers):
    """Test motor macro execution."""
    _, motor_worker = mock_workers
    motor_worker.running = True
    
    mock_macro = {
        "Macro No.": "Macro 1",
        "Label": "Position 1",
        "Position": 500
    }
    
    with patch.object(window, 'load_motor_macro', return_value=mock_macro), \
         patch('PyQt6.QtCore.QTimer') as mock_timer:
        window.on_motorMacroButton_clicked(1)
        
        # Verify motor movement
        motor_worker.move_to.assert_called_once_with(500)
        # Verify position check timer setup
        mock_timer.assert_called_once()


def test_save_path_selection(window):
    """Test save path selection dialog."""
    mock_path = "/test/path/data.csv"
    
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', 
              return_value=(mock_path, "CSV Files (*.csv)")):
        window.on_selectSavePathButton_clicked()
        
        assert window.savePathEdit.text() == mock_path


def test_begin_save_with_custom_path(window):
    """Test data saving with custom path."""
    mock_path = "/test/path/data.csv"
    window.savePathEdit.setText(mock_path)
    
    with patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch.object(window.plot_widget, 'start_recording', return_value=True):
        window.on_beginSaveButton_clicked(True)
        
        assert window.saving is True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_sequence_file_cleanup(window):
    """Test sequence file cleanup operations."""
    with patch('pathlib.Path.unlink') as mock_unlink, \
         patch('builtins.open', mock_open()) as mock_file:
        window.handle_sequence_file(True)
        
        # Verify prospa.txt written with success status
        mock_file.assert_called_with(Path(r"C:\ssbubble\prospa.txt"), 'w')
        mock_file().write.assert_called_once_with('1')
        
        # Verify sequence file deletion (not in test mode)
        if not window.test_mode:
            mock_unlink.assert_called_once()
