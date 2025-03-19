"""
File: src/utils/logger.py
"""

import logging
from pathlib import Path
import threading
from queue import Queue
import time

LOG_DIR = Path("logs")

# Add a thread-safe logging queue
_log_queue = Queue()
_log_thread = None
_log_thread_running = False

class LogFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

class ThreadSafeHandler(logging.Handler):
    """A handler that queues log records for processing in the main thread."""
    
    def __init__(self, target_handler):
        super().__init__()
        self.target_handler = target_handler
        
    def emit(self, record):
        # Put the record in the queue instead of directly emitting
        _log_queue.put(record)

def _process_log_queue():
    """Process log records from the queue."""
    global _log_thread_running
    
    while _log_thread_running:
        try:
            # Get records with a timeout to allow thread to exit
            while not _log_queue.empty():
                record = _log_queue.get(block=True, timeout=0.2)
                # Process the record with the actual handlers
                for handler in logging.getLogger().handlers:
                    if not isinstance(handler, ThreadSafeHandler):
                        handler.emit(record)
                _log_queue.task_done()
        except Exception:
            # Timeout or other error, just continue
            pass
        time.sleep(0.1)  # Small sleep to prevent CPU hogging

def setup_logging(debug=False):
    """Set up logging configuration.
    
    Args:
        debug: If True, set log level to DEBUG, otherwise INFO
    """
    global _log_thread, _log_thread_running
    
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create a stream handler for console output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(LogFormatter())
    
    # Create a thread-safe wrapper for the console handler
    thread_safe_handler = ThreadSafeHandler(console_handler)
    thread_safe_handler.setLevel(log_level)
    
    # Add the thread-safe handler to the root logger
    root_logger.addHandler(thread_safe_handler)
    root_logger.addHandler(console_handler)
    
    # Create logger
    logger = logging.getLogger('SSBubble')
    logger.setLevel(log_level)
    
    # Start the log processing thread if not already running
    if _log_thread is None or not _log_thread.is_alive():
        _log_thread_running = True
        _log_thread = threading.Thread(target=_process_log_queue, daemon=True)
        _log_thread.start()
    
    # Log startup message
    logger.info("=== Starting SSBubble application ===")
    if debug:
        logger.debug("Debug logging enabled")
    
    return logger

def shutdown_logging():
    """Shutdown logging system cleanly."""
    global _log_thread_running
    
    # Signal the thread to stop
    _log_thread_running = False
    
    # Wait for the queue to be processed
    if not _log_queue.empty():
        _log_queue.join()
    
    # Wait for the thread to exit (with timeout)
    if _log_thread and _log_thread.is_alive():
        _log_thread.join(timeout=1.0)
