"""
File: tests/test_integration/test_widget_integration.py
Description: Integration tests for UI widgets
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
import time
import json
from pathlib import Path

from src.ui.main_window import MainWindow
from src.ui.widgets.plot_widget import PlotWidget
from src.ui.widgets.log_widget import LogWidget
from src.ui.dialogs.valve_macro_editor import ValveMacroEditor
from src.ui.dialogs.motor_macro_editor import MotorMacroEditor


@pytest.mark.usefixtures("qapp")
class TestWidgetIntegration:
    """Test suite for widget integration."""

    @pytest.fixture
    def main_window(self):
        """Create main window with test configuration."""
        with patch('src.workers.arduino_worker.ArduinoWorker'), \
             patch('src.workers.motor_worker.MotorWorker'):
            window = MainWindow(test_mode=True)
            return window

    def test_plot_log_integration(self, qtbot, main_window):
        """Test integration between plot and log widgets."""
        qtbot.addWidget(main_window)

        # Track log messages
        messages = []
        main_window.log_widget.add_message = lambda msg, level=None: messages.append(msg)

        # Update plot with test data
        test_data = [1.0, 2.0, 3.0, 4.0]
        main_window.plot_widget.update_plot(test_data)
        
        # Verify log shows plot update
        assert any("readings" in msg.lower() for msg in messages)

        # Test plot controls affect logging
        main_window.plot_widget.clear_data()
        assert any("cleared" in msg.lower() for msg in messages)

    def test_log_level_integration(self, qtbot, main_window):
        """Test log level changes affect both widgets."""
        qtbot.addWidget(main_window)

        # Change log level
        main_window.log_widget.level_combo.setCurrentText("DEBUG")
        
        # Verify plot widget receives debug messages
        test_data = [1.0, 2.0, 3.0, 4.0]
        main_window.plot_widget.update_plot(test_data)
        
        log_text = main_window.log_widget.toPlainText()
        assert "DEBUG" in log_text

    def test_data_recording_integration(self, qtbot, main_window, tmp_path):
        """Test data recording integration between widgets."""
        qtbot.addWidget(main_window)

        # Setup test file
        test_file = tmp_path / "test_data.csv"
        
        # Start recording
        main_window.plot_widget.start_recording(str(test_file))
        
        # Generate test data
        test_data = [1.0, 2.0, 3.0, 4.0]
        main_window.plot_widget.update_plot(test_data)
        
        # Stop recording
        main_window.plot_widget.stop_recording()
        
        # Verify log shows recording events
        log_text = main_window.log_widget.toPlainText()
        assert any("recording" in line.lower() for line in log_text.split('\n'))
        
        # Verify file was created
        assert test_file.exists()

    def test_error_propagation(self, qtbot, main_window):
        """Test error propagation between widgets."""
        qtbot.addWidget(main_window)

        # Simulate plot error
        with patch.object(main_window.plot_widget, 'update_plot', 
                         side_effect=Exception("Plot error")):
            main_window.plot_widget.update_plot([1.0, 2.0, 3.0, 4.0])

        # Verify error appears in log
        log_text = main_window.log_widget.toPlainText()
        assert "ERROR" in log_text
        assert "Plot error" in log_text

    def test_widget_synchronization(self, qtbot, main_window):
        """Test widget state synchronization."""
        qtbot.addWidget(main_window)

        # Test auto-scroll synchronization
        main_window.log_widget.toggle_auto_scroll(False)
        
        # Generate multiple updates
        for i in range(10):
            main_window.plot_widget.update_plot([float(i)] * 4)
            
        # Verify log position stayed at top
        scrollbar = main_window.log_widget.log_display.verticalScrollBar()
        assert scrollbar.value() < scrollbar.maximum()

    def test_plot_controls_integration(self, qtbot, main_window):
        """Test plot control integration with other widgets."""
        qtbot.addWidget(main_window)

        # Test toolbar actions affect both widgets
        main_window.plot_widget.toolbar.actions()[0].trigger()  # Home action
        
        log_text = main_window.log_widget.toPlainText()
        assert any("view" in line.lower() for line in log_text.split('\n'))

    def test_data_export_integration(self, qtbot, main_window, tmp_path):
        """Test data export functionality integration."""
        qtbot.addWidget(main_window)

        # Generate test data
        test_data = [1.0, 2.0, 3.0, 4.0]
        main_window.plot_widget.update_plot(test_data)

        # Mock file dialog
        test_file = tmp_path / "export_data.csv"
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', 
                  return_value=(str(test_file), "CSV Files (*.csv)")):
            # Export data
            main_window.plot_widget.export_data()

        # Verify export logged
        log_text = main_window.log_widget.toPlainText()
        assert "exported" in log_text.lower()
        assert test_file.exists()

    def test_real_time_updates(self, qtbot, main_window):
        """Test real-time updates between widgets."""
        qtbot.addWidget(main_window)

        # Setup counters
        plot_updates = []
        log_updates = []
        
        # Track updates
        main_window.plot_widget.canvas.draw = lambda: plot_updates.append(1)
        main_window.log_widget.add_message = lambda msg, level=None: log_updates.append(msg)

        # Simulate real-time data
        for i in range(5):
            main_window.plot_widget.update_plot([float(i)] * 4)
            time.sleep(0.01)

        # Verify both widgets updated
        assert len(plot_updates) > 0
        assert len(log_updates) > 0

    @pytest.fixture
    def mock_macro_files(self, tmp_path):
        """Create mock macro files."""
        valve_data = [
            {
                "Macro No.": "Macro 1",
                "Label": "Test Valve Macro",
                "Valves": ["Open", "Closed", "Open", "Closed", "Ignore", "Closed", "Closed", "Closed"],
                "Timer": 1.5
            }
        ]
        motor_data = [
            {
                "Macro No.": "Macro 1",
                "Label": "Test Motor Macro",
                "Position": 500
            }
        ]

        valve_file = tmp_path / "valve_macro_data.json"
        motor_file = tmp_path / "motor_macro_data.json"
        
        valve_file.write_text(json.dumps(valve_data))
        motor_file.write_text(json.dumps(motor_data))
        
        return valve_file, motor_file

    def test_valve_macro_editor_integration(self, qtbot, main_window, tmp_path):
        """Test valve macro editor integration."""
        qtbot.addWidget(main_window)

        # Mock macro file path
        test_file = tmp_path / "valve_macro_data.json"
        with patch('pathlib.Path', return_value=test_file):
            # Open macro editor
            editor = ValveMacroEditor(main_window)
            qtbot.addWidget(editor)

            # Edit macro values
            editor.table.item(0, 1).setText("New Valve Macro")  # Set label
            combo = editor.table.cellWidget(0, 2)  # First valve state
            combo.setCurrentText("Open")
            
            # Close editor to trigger save
            editor.close()

            # Verify changes reflected in main window
            assert main_window.valveMacro1Button.text() == "New Valve Macro"
            
            # Verify log shows update
            log_text = main_window.log_widget.toPlainText()
            assert any("macro" in line.lower() for line in log_text.split('\n'))

    def test_motor_macro_editor_integration(self, qtbot, main_window, tmp_path):
        """Test motor macro editor integration."""
        qtbot.addWidget(main_window)

        # Mock macro file path
        test_file = tmp_path / "motor_macro_data.json"
        with patch('pathlib.Path', return_value=test_file):
            # Open macro editor
            editor = MotorMacroEditor(main_window)
            qtbot.addWidget(editor)

            # Edit macro values
            editor.table.item(0, 1).setText("New Motor Macro")  # Set label
            spinbox = editor.table.cellWidget(0, 2)  # Position
            spinbox.setValue(1000)
            
            # Close editor to trigger save
            editor.close()

            # Verify changes reflected in main window
            assert main_window.motor_macro1_button.text() == "New Motor Macro"
            
            # Verify log shows update
            log_text = main_window.log_widget.toPlainText()
            assert any("macro" in line.lower() for line in log_text.split('\n'))

    def test_macro_editor_file_handling(self, qtbot, main_window, mock_macro_files):
        """Test macro editor file handling."""
        valve_file, motor_file = mock_macro_files
        qtbot.addWidget(main_window)

        with patch('pathlib.Path', side_effect=[valve_file, motor_file]):
            # Test valve macro loading
            valve_editor = ValveMacroEditor(main_window)
            assert valve_editor.table.item(0, 1).text() == "Test Valve Macro"
            
            # Test motor macro loading
            motor_editor = MotorMacroEditor(main_window)
            assert motor_editor.table.item(0, 1).text() == "Test Motor Macro"

    def test_macro_execution_logging(self, qtbot, main_window):
        """Test macro execution logging integration."""
        qtbot.addWidget(main_window)

        # Track log messages
        messages = []
        main_window.log_widget.add_message = lambda msg, level=None: messages.append(msg)

        # Execute valve macro
        main_window.on_valveMacroButton_clicked(1)
        assert any("valve macro" in msg.lower() for msg in messages)

        # Execute motor macro
        main_window.on_motorMacroButton_clicked(1)
        assert any("motor macro" in msg.lower() for msg in messages)

    def test_macro_error_handling(self, qtbot, main_window, tmp_path):
        """Test macro error handling integration."""
        qtbot.addWidget(main_window)

        # Test invalid file handling
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("invalid json")

        with patch('pathlib.Path', return_value=invalid_file):
            # Open editors with invalid file
            valve_editor = ValveMacroEditor(main_window)
            motor_editor = MotorMacroEditor(main_window)

            # Verify default values loaded
            assert valve_editor.table.item(0, 1).text() == "Valve Macro 1"
            assert motor_editor.table.item(0, 1).text() == "Motor Macro 1"

            # Verify error logged
            log_text = main_window.log_widget.toPlainText()
            assert any("error" in line.lower() for line in log_text.split('\n'))

    def test_macro_editor_ui_sync(self, qtbot, main_window):
        """Test macro editor UI synchronization."""
        qtbot.addWidget(main_window)

        # Open both editors
        valve_editor = ValveMacroEditor(main_window)
        motor_editor = MotorMacroEditor(main_window)
        qtbot.addWidget(valve_editor)
        qtbot.addWidget(motor_editor)

        # Make changes in both editors
        valve_editor.table.item(0, 1).setText("Synced Valve Macro")
        motor_editor.table.item(0, 1).setText("Synced Motor Macro")

        # Close editors
        valve_editor.close()
        motor_editor.close()

        # Verify main window updates
        assert main_window.valveMacro1Button.text() == "Synced Valve Macro"
        assert main_window.motor_macro1_button.text() == "Synced Motor Macro"

        # Verify log captures both updates
        log_text = main_window.log_widget.toPlainText()
        assert "valve macro" in log_text.lower()
        assert "motor macro" in log_text.lower()
