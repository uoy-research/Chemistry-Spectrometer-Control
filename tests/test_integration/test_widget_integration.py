"""
File: tests/test_integration/test_widget_integration.py
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest


@pytest.mark.usefixtures("qapp")
class TestWidgetIntegration:
    def test_plot_log_integration(self, qtbot, mock_controllers):
        """Test integration between plot and log widgets."""
        main_window = MainWindow(config={"test_mode": True})
        qtbot.addWidget(main_window)

        # Trigger some actions
        main_window.plot_widget.update_data([1.0, 2.0, 3.0])

        # Verify log shows update
        assert "Plot updated" in main_window.log_widget.toPlainText()

    def test_macro_editor_log_integration(self, qtbot, mock_controllers):
        """Test integration between macro editor and log."""
        main_window = MainWindow(config={"test_mode": True})
        qtbot.addWidget(main_window)

        # Edit macro
        main_window.macro_editor.setText("move_to(100)")

        # Verify log shows update
        assert "Macro updated" in main_window.log_widget.toPlainText()
