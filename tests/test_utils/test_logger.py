"""
File: test_logger.py
Description: Tests for logging configuration
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import patch, Mock

from src.utils.logger import setup_logging, LogFormatter


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


def test_log_formatter():
    """Test custom log formatter."""
    formatter = LogFormatter()

    # Create test record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )

    # Format record
    output = formatter.format(record)
    assert "Test message" in output
    assert record.levelname in output
    assert "test" in output


def test_setup_logging(temp_log_dir):
    """Test logging setup."""
    with patch('src.utils.logger.LOG_DIR', str(temp_log_dir)):
        logger = setup_logging()

        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0


def test_log_file_creation(temp_log_dir):
    """Test log file creation."""
    with patch('src.utils.logger.LOG_DIR', str(temp_log_dir)):
        logger = setup_logging()

        # Log test message
        test_message = "Test log message"
        logger.info(test_message)

        # Check log file
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1

        # Verify message in file
        log_content = log_files[0].read_text()
        assert test_message in log_content


def test_log_rotation(temp_log_dir):
    """Test log file rotation."""
    with patch('src.utils.logger.LOG_DIR', str(temp_log_dir)):
        logger = setup_logging(max_bytes=100, backup_count=3)

        # Generate enough logs to trigger rotation
        for i in range(100):
            logger.info("X" * 10)

        # Check rotated files
        log_files = list(temp_log_dir.glob("*.log*"))
        assert 1 <= len(log_files) <= 4  # Main log + backups


@pytest.mark.parametrize("level_name,level_const", [
    ("DEBUG", logging.DEBUG),
    ("INFO", logging.INFO),
    ("WARNING", logging.WARNING),
    ("ERROR", logging.ERROR),
    ("CRITICAL", logging.CRITICAL),
])
def test_log_levels(temp_log_dir, level_name, level_const):
    """Test different logging levels."""
    with patch('src.utils.logger.LOG_DIR', str(temp_log_dir)):
        logger = setup_logging(level=level_name)
        assert logger.level == level_const


def test_invalid_log_level(temp_log_dir):
    """Test handling of invalid log level."""
    with patch('src.utils.logger.LOG_DIR', str(temp_log_dir)):
        logger = setup_logging(level="INVALID")
        assert logger.level == logging.INFO  # Should default to INFO


def test_log_directory_creation():
    """Test log directory creation."""
    with patch('pathlib.Path.mkdir') as mock_mkdir:
        setup_logging()
        mock_mkdir.assert_called()


def test_multiple_logger_instances():
    """Test getting same logger instance."""
    logger1 = setup_logging()
    logger2 = setup_logging()
    assert logger1 is logger2


def test_log_formatting():
    """Test log message formatting."""
    formatter = LogFormatter()

    # Test different message types
    test_cases = [
        (logging.INFO, "Simple message"),
        (logging.ERROR, "Error with\nmultiple\nlines"),
        (logging.DEBUG, "Message with spaces  and tabs\t"),
    ]

    for level, msg in test_cases:
        record = logging.LogRecord(
            name="test",
            level=level,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert msg in formatted
        assert record.levelname in formatted


def test_exception_logging(temp_log_dir):
    """Test logging of exceptions."""
    with patch('src.utils.logger.LOG_DIR', str(temp_log_dir)):
        logger = setup_logging()

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Error occurred")

        # Check log file
        log_files = list(temp_log_dir.glob("*.log"))
        log_content = log_files[0].read_text()
        assert "Test exception" in log_content
        assert "Traceback" in log_content
