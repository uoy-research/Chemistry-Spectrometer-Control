"""
File: src/utils/logger.py
"""

import logging
from pathlib import Path

LOG_DIR = Path("logs")


class LogFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(level="INFO"):
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create handlers
    file_handler = logging.FileHandler(LOG_DIR / 'app.log', mode='w')
    console_handler = logging.StreamHandler()

    # Create formatter
    formatter = LogFormatter()

    # Set formatter for handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Create and return application logger
    logger = logging.getLogger('SSBubble')
    return logger
