"""
File: test_widget_integration.py
Description: Integration tests between UI widgets
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.widgets.plot_widget import PlotWidget
from src.ui.widgets.log_widget import LogWidget
from src.ui.dialogs.macro_editor import MacroEditor
from src.models.valve_macro import MacroManager


@pytest.fixture
def app():
    """Create QApplication instance."""
    return QApplication([])


@pytest.fixture
def widgets(app, tmp_path):
    """Create widget instances."""
    plot = PlotWidget()
    log = LogWidget()
    macro_file = tmp_path / "test_macros.json"
    macro_file.write_text("{}")
    macro_manager = MacroManager(macro_file)
    editor = MacroEditor(macro_manager)
    return plot, log, editor


def test_plot_log_integration(widgets):
    """Test integration between plot and log widgets."""
    plot, log, _ = widgets

    # Connect plot signals to log
    plot.status_message.connect(log.add_message)

    # Trigger plot actions that generate logs
    plot.clear_data()
    plot.set_max_points(500)

    # Verify logs generated
    log_text = log.log_display.toPlainText()
    assert "cleared" in log_text.lower()
    assert "max points" in log_text.lower()


def test_macro_editor_log_integration(widgets, qtbot):
    """Test integration between macro editor and log widget."""
    _, log, editor = widgets

    # Connect editor signals to log
    editor.status_message.connect(log.add_message)

    # Create new macro
    editor.create_macro()
    editor.label_edit.setText("Test Macro")
    editor.apply_changes()

    # Verify logs
    log_text = log.log_display.toPlainText()
    assert "macro" in log_text.lower()
    assert "Test Macro" in log_text


def test_plot_macro_integration(widgets):
    """Test integration between plot widget and macro editor."""
    plot, _, editor = widgets

    # Create macro with valve states
    editor.create_macro()
    editor.set_valve_states([1] * 8)
    editor.apply_changes()

    # Update plot based on macro execution
    plot.update_plot([1.0, 2.0, 3.0])

    # Verify plot updated
    for curve in plot.curves:
        assert curve.getData()[0] is not None


def test_widget_state_synchronization(widgets):
    """Test state synchronization between widgets."""
    plot, log, editor = widgets

    # Simulate busy state
    plot.setEnabled(False)
    log.setEnabled(False)
    editor.setEnabled(False)

    # Verify all widgets disabled
    assert not plot.isEnabled()
    assert not log.isEnabled()
    assert not editor.isEnabled()


def test_data_flow_between_widgets(widgets):
    """Test data flow between widgets."""
    plot, log, editor = widgets

    # Create test data
    test_data = [1.0, 2.0, 3.0]

    # Update plot
    plot.update_plot(test_data)

    # Export plot data
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
               return_value=("test.csv", None)):
        plot.export_data()

    # Verify export logged
    assert "exported" in log.log_display.toPlainText().lower()


def test_error_propagation(widgets):
    """Test error handling between widgets."""
    plot, log, editor = widgets

    # Simulate error in plot
    with patch.object(plot, 'update_plot', side_effect=Exception("Plot error")):
        plot.update_plot([1.0, 2.0, 3.0])

    # Verify error logged
    assert "error" in log.log_display.toPlainText().lower()


def test_concurrent_widget_operations(widgets):
    """Test concurrent operations between widgets."""
    plot, log, editor = widgets

    # Perform multiple operations
    plot.update_plot([1.0, 2.0, 3.0])
    editor.create_macro()
    log.add_message("Test message")

    # Verify all operations completed
    assert plot.curves[0].getData()[0] is not None
    assert editor.macro_combo.count() > 0
    assert "Test message" in log.log_display.toPlainText()
