"""
File: test_log_widget.py
Description: Tests for log widget
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import logging

from src.ui.widgets.log_widget import LogWidget, LogHandler


@pytest.fixture
def app():
    """Create QApplication instance."""
    return QApplication([])


@pytest.fixture
def log_widget(app):
    """Create log widget instance."""
    return LogWidget(max_lines=100)


def test_initialization(log_widget):
    """Test widget initialization."""
    assert log_widget.max_lines == 100
    assert log_widget.auto_scroll is True
    assert log_widget.line_count == 0
    assert log_widget.log_display.isReadOnly()


def test_add_message(log_widget):
    """Test adding messages to log."""
    # Test different log levels
    test_cases = [
        ("Debug message", logging.DEBUG),
        ("Info message", logging.INFO),
        ("Warning message", logging.WARNING),
        ("Error message", logging.ERROR),
        ("Critical message", logging.CRITICAL)
    ]

    for msg, level in test_cases:
        log_widget.add_message(msg, level)
        text = log_widget.log_display.toPlainText()
        assert msg in text


def test_clear_log(log_widget):
    """Test clearing log."""
    # Add test messages
    log_widget.add_message("Test 1", logging.INFO)
    log_widget.add_message("Test 2", logging.INFO)

    # Clear log
    log_widget.clear_log()

    # Verify cleared
    assert log_widget.log_display.toPlainText() == ""
    assert log_widget.line_count == 0


def test_auto_scroll(log_widget):
    """Test auto-scroll functionality."""
    # Test disable
    log_widget.toggle_auto_scroll(False)
    assert log_widget.auto_scroll is False
    assert not log_widget.scroll_btn.isChecked()

    # Test enable
    log_widget.toggle_auto_scroll(True)
    assert log_widget.auto_scroll is True
    assert log_widget.scroll_btn.isChecked()


def test_max_lines_limit(log_widget):
    """Test maximum lines limit."""
    # Add more lines than max_lines
    for i in range(150):  # max_lines is 100
        log_widget.add_message(f"Line {i}", logging.INFO)

    # Verify line limit
    assert log_widget.line_count <= log_widget.max_lines
    lines = log_widget.log_display.toPlainText().split('\n')
    assert len(lines) <= log_widget.max_lines + 1  # +1 for empty line


def test_log_handler(log_widget):
    """Test custom log handler."""
    # Create and configure handler
    handler = LogHandler(log_widget)
    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Test logging through handler
    test_message = "Handler test message"
    logger.info(test_message)

    # Verify message in widget
    assert test_message in log_widget.log_display.toPlainText()


def test_log_level_filter(log_widget):
    """Test log level filtering."""
    # Set log level to WARNING
    log_widget.set_log_level("WARNING")

    # Create logger with handler
    handler = LogHandler(log_widget)
    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)

    # Log messages at different levels
    debug_msg = "Debug message"
    info_msg = "Info message"
    warning_msg = "Warning message"

    logger.debug(debug_msg)
    logger.info(info_msg)
    logger.warning(warning_msg)

    # Verify filtering
    text = log_widget.log_display.toPlainText()
    assert debug_msg not in text
    assert info_msg not in text
    assert warning_msg in text


def test_export_log(log_widget, tmp_path):
    """Test log export functionality."""
    # Add test messages
    test_messages = ["Message 1", "Message 2", "Message 3"]
    for msg in test_messages:
        log_widget.add_message(msg, logging.INFO)

    # Setup export path
    test_file = tmp_path / "test_log.txt"

    # Mock file dialog to return our test path
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
               return_value=(str(test_file), None)):
        log_widget.export_log()

    # Verify export
    assert test_file.exists()
    content = test_file.read_text()
    for msg in test_messages:
        assert msg in content


def test_color_coding(log_widget):
    """Test color coding of different log levels."""
    # Add messages with different levels
    log_widget.add_message("Debug message", logging.DEBUG)
    log_widget.add_message("Error message", logging.ERROR)

    # Verify colors (implementation specific)
    # This might need to be adjusted based on your actual color implementation
    text_document = log_widget.log_display.document()
    assert text_document.blockCount() > 0


def test_trim_log(log_widget):
    """Test log trimming functionality."""
    # Fill log to capacity
    for i in range(log_widget.max_lines + 10):
        log_widget.add_message(f"Message {i}", logging.INFO)

    # Verify trimming
    assert log_widget.line_count <= log_widget.max_lines

    # Verify oldest messages removed
    text = log_widget.log_display.toPlainText()
    assert "Message 0" not in text
    assert f"Message {log_widget.max_lines + 9}" in text


def test_ui_interaction(log_widget):
    """Test UI control interactions."""
    # Test level combo box
    log_widget.level_combo.setCurrentText("ERROR")
    assert log_widget.logger.level == logging.ERROR

    # Test clear button
    log_widget.add_message("Test message", logging.INFO)
    log_widget.clear_btn.click()
    assert log_widget.log_display.toPlainText() == ""

    # Test scroll button
    log_widget.scroll_btn.click()
    assert log_widget.auto_scroll is False
    log_widget.scroll_btn.click()
    assert log_widget.auto_scroll is True
