"""Centralized timing logger configuration."""

import logging
from pathlib import Path
import time

# Global timing logger instance
_timing_logger = None

def setup_timing_logger(enabled: bool = False):
    """Setup the timing logger.
    
    Args:
        enabled: Whether timing logging is enabled
    
    Returns:
        logging.Logger: Configured timing logger
    """
    global _timing_logger
    
    if not enabled:
        return None
        
    if _timing_logger is None:
        # Create logs directory
        log_dir = Path("C:/ssbubble/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timing logger
        _timing_logger = logging.getLogger('timing')
        _timing_logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not _timing_logger.handlers:
            # Create log filename with timestamp
            log_file = log_dir / f"timing_{time.strftime('%Y%m%d_%H%M%S')}.log"
            
            # Setup handler
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(message)s', 
                                       datefmt='%Y-%m-%d %H:%M:%S')
            handler.setFormatter(formatter)
            _timing_logger.addHandler(handler)
            
            # Prevent propagation to root logger
            _timing_logger.propagate = False
    
    return _timing_logger

def get_timing_logger():
    """Get the timing logger instance."""
    return _timing_logger 