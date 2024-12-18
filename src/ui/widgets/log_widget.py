"""
File: log_widget.py
Description: Widget for displaying and managing application logs
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QComboBox, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
import logging
from typing import Dict, Optional
import os


class LogHandler(logging.Handler):
    """Custom logging handler that emits signals for GUI updates."""

    def __init__(self, widget: 'LogWidget'):
        """Initialize handler."""
        super().__init__()
        self.widget = widget
        self.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )

    def emit(self, record):
        """Emit log record to widget."""
        msg = self.format(record)
        self.widget.add_message(msg, record.levelno)


class LogWidget(QWidget):
    """
    Widget for displaying and managing application logs.

    Attributes:
        max_lines (int): Maximum number of lines to display
        auto_scroll (bool): Enable automatic scrolling
    """

    # Color scheme for different log levels
    COLORS: Dict[int, QColor] = {
        logging.DEBUG: QColor(128, 128, 128),  # Gray
        logging.INFO: QColor(0, 0, 0),         # Black
        logging.WARNING: QColor(255, 165, 0),   # Orange
        logging.ERROR: QColor(255, 0, 0),       # Red
        logging.CRITICAL: QColor(139, 0, 0)     # Dark Red
    }

    def __init__(self, max_lines: int = 1000):
        """Initialize log widget."""
        super().__init__()

        self.max_lines = max_lines
        self.auto_scroll = True
        self.line_count = 0

        self.setup_ui()
        self.setup_logging()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Create log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Create control panel
        control_panel = QHBoxLayout()

        # Log level filter
        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        ])
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self.set_log_level)

        # Auto-scroll toggle
        self.scroll_btn = QPushButton("Auto-scroll")
        self.scroll_btn.setCheckable(True)
        self.scroll_btn.setChecked(True)
        self.scroll_btn.toggled.connect(self.toggle_auto_scroll)

        # Clear and export buttons
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_log)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_log)

        # Add widgets to control panel
        control_panel.addWidget(QLabel("Log Level:"))
        control_panel.addWidget(self.level_combo)
        control_panel.addStretch()
        control_panel.addWidget(self.scroll_btn)
        control_panel.addWidget(self.clear_btn)
        control_panel.addWidget(self.export_btn)

        # Add widgets to main layout
        layout.addWidget(self.log_display)
        layout.addLayout(control_panel)

    def setup_logging(self):
        """Setup logging configuration."""
        self.logger = logging.getLogger()
        self.handler = LogHandler(self)
        self.logger.addHandler(self.handler)
        self.set_log_level(self.level_combo.currentText())

    def add_message(self, message: str, level: Optional[int] = None):
        """
        Add message to log display.

        Args:
            message: Log message
            level: Logging level (determines text color)
        """
        try:
            # Create text format with appropriate color
            format = QTextCharFormat()
            if level is not None and level in self.COLORS:
                format.setForeground(self.COLORS[level])

            # Add message to display
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(message + '\n', format)

            # Manage line count
            self.line_count += 1
            if self.line_count > self.max_lines:
                self.trim_log()

            # Auto-scroll if enabled
            if self.auto_scroll:
                self.log_display.verticalScrollBar().setValue(
                    self.log_display.verticalScrollBar().maximum()
                )

        except Exception as e:
            print(f"Error adding log message: {e}")

    def trim_log(self):
        """Remove oldest lines when max_lines is exceeded."""
        try:
            # Get all text
            text = self.log_display.toPlainText()
            lines = text.split('\n')

            # Keep only the most recent lines
            kept_lines = lines[-self.max_lines:]

            # Update display
            self.log_display.clear()
            self.log_display.setPlainText('\n'.join(kept_lines))
            self.line_count = len(kept_lines)

        except Exception as e:
            print(f"Error trimming log: {e}")

    def clear_log(self):
        """Clear log display."""
        self.log_display.clear()
        self.line_count = 0

    def toggle_auto_scroll(self, enabled: bool):
        """Toggle auto-scroll functionality."""
        self.auto_scroll = enabled
        self.scroll_btn.setChecked(enabled)

    def set_log_level(self, level: str):
        """Set logging level filter."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        self.logger.setLevel(level_map[level])

    def export_log(self):
        """Export log contents to file."""
        try:
            # Get current timestamp for filename
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss")
            default_name = f"log_{timestamp}.txt"

            # Get save location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Log",
                default_name,
                "Text Files (*.txt);;All Files (*.*)"
            )

            if filename:
                # Write log contents to file
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_display.toPlainText())

                self.add_message(
                    f"Log exported to {filename}",
                    logging.INFO
                )

        except Exception as e:
            self.add_message(
                f"Error exporting log: {e}",
                logging.ERROR
            )

    def set_max_lines(self, max_lines: int):
        """Set maximum number of displayed lines."""
        self.max_lines = max_lines
        if self.line_count > max_lines:
            self.trim_log()
2