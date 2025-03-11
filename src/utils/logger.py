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


def setup_logging(debug=False):
    """Set up logging configuration.
    
    Args:
        debug: If True, set log level to DEBUG, otherwise INFO
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Create logger
    logger = logging.getLogger('SSBubble')
    logger.setLevel(log_level)
    
    # Log startup message
    logger.info("=== Starting SSBubble application ===")
    if debug:
        logger.debug("Debug logging enabled")
    
    return logger
