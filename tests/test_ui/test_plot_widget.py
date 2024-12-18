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


def test_add_message(log_widget):
    """Test adding messages to log."""
    # Add test message
    log_widget.add_message("Test message", logging.INFO)

    # Verify message added
    text = log_widget.log_display.toPlainText()
    assert "Test message" in text
    assert log_widget.line_count == 1


def test_clear_log(log_widget):
    """Test clearing log."""
    # Add messages
    log_widget.add_message("Test 1")
    log_widget.add_message("Test 2")

    # Clear log
    log_widget.clear_log()

    # Verify cleared
    assert log_widget.log_display.toPlainText() == ""
    assert log_widget.line_count == 0


def test_auto_scroll(log_widget):
    """Test auto-scroll functionality."""
    # Disable auto-scroll
    log_widget.toggle_auto_scroll(False)
    assert log_widget.auto_scroll is False

    # Enable auto-scroll
    log_widget.toggle_auto_scroll(True)
    assert log_widget.auto_scroll is True


def test_log_levels(log_widget):
    """Test different log levels."""
    levels = [
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL
    ]

    # Test each level
    for level in levels:
        log_widget.add_message(f"Test {level}", level)

    # Verify all messages added
    text = log_widget.log_display.toPlainText()
    assert text.count('\n') == len(levels)


def test_max_lines_limit(log_widget):
    """Test maximum lines limit."""
    # Add more lines than max_lines
    for i in range(150):  # max_lines is 100
        log_widget.add_message(f"Line {i}")

    # Verify line limit
    assert log_widget.line_count <= log_widget.max_lines
    lines = log_widget.log_display.toPlainText().split('\n')
    assert len(lines) <= log_widget.max_lines + 1  # +1 for empty line


def test_export_log(log_widget, tmp_path):
    """Test log export functionality."""
    # Add test messages
    log_widget.add_message("Test message 1")
    log_widget.add_message("Test message 2")

    # Mock file dialog
    test_file = tmp_path / "test_log.txt"
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
               return_value=(str(test_file), None)):
        log_widget.export_log()

    # Verify exported file
    assert test_file.exists()
    content = test_file.read_text()
    assert "Test message 1" in content
    assert "Test message 2" in content


def test_log_handler(log_widget):
    """Test custom log handler."""
    handler = LogHandler(log_widget)
    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)

    # Log test message
    logger.info("Handler test")

    # Verify message in widget
    assert "Handler test" in log_widget.log_display.toPlainText()


def test_log_level_filter(log_widget):
    """Test log level filtering."""
    # Set log level to WARNING
    log_widget.set_log_level("WARNING")

    # Create logger with handler
    handler = LogHandler(log_widget)
    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)

    # Log messages at different levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")

    # Verify only WARNING and above shown
    text = log_widget.log_display.toPlainText()
    assert "Debug message" not in text
    assert "Info message" not in text
    assert "Warning message" in text


@pytest.mark.parametrize("message,level", [
    ("Test debug", logging.DEBUG),
    ("Test info", logging.INFO),
    ("Test warning", logging.WARNING),
    ("Test error", logging.ERROR),
    ("Test critical", logging.CRITICAL),
])
def test_message_formatting(log_widget, message, level):
    """Test message formatting for different levels."""
    log_widget.add_message(message, level)
    assert message in log_widget.log_display.toPlainText()


def test_concurrent_logging(log_widget):
    """Test concurrent logging operations."""
    # Simulate concurrent logging
    for i in range(100):
        log_widget.add_message(f"Message {i}", logging.INFO)

    # Verify all messages processed
    text = log_widget.log_display.toPlainText()
    assert text.count('\n') <= log_widget.max_lines + 1
