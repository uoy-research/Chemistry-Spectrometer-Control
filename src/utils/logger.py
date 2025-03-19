"""
File: src/utils/logger.py
"""

import logging
from pathlib import Path
import threading
from queue import Queue, Empty
import time

LOG_DIR = Path("logs")

# Add a thread-safe logging queue
_log_queue = Queue(maxsize=1000)  # Limit queue size to prevent memory issues
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
        try:
            # Only queue if the thread is running
            if _log_thread_running:
                try:
                    _log_queue.put(record, block=False)  # Non-blocking put
                except Exception:
                    # If queue is full or any other error, emit directly
                    self.target_handler.emit(record)
            else:
                # If thread isn't running, emit directly
                self.target_handler.emit(record)
        except Exception:
            # Last resort - ignore errors
            pass

def _process_log_queue():
    """Process log records from the queue."""
    global _log_thread_running
    
    while _log_thread_running:
        try:
            # Get records with a timeout to allow thread to exit
            try:
                record = _log_queue.get(block=True, timeout=0.2)
                # Process the record with the actual handlers
                for handler in logging.getLogger().handlers:
                    if not isinstance(handler, ThreadSafeHandler):
                        try:
                            handler.emit(record)
                        except Exception:
                            pass  # Ignore handler errors
                _log_queue.task_done()
            except Empty:
                # Timeout or queue empty, just continue
                pass
        except Exception:
            # Catch any other exceptions to keep thread alive
            pass
        
        # Small sleep to prevent CPU hogging
        time.sleep(0.05)

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
    
    # Add ONLY the thread-safe handler to the root logger
    root_logger.addHandler(thread_safe_handler)
    
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
    global _log_thread_running, _log_thread
    
    if _log_thread is None or not _log_thread.is_alive():
        return  # Nothing to do if thread isn't running
    
    # Signal the thread to stop
    _log_thread_running = False
    
    # Process any remaining items in the queue directly
    try:
        # Only try to process remaining items with a short timeout
        timeout = 0.5  # Half second timeout for queue processing
        start_time = time.time()
        
        while not _log_queue.empty() and (time.time() - start_time) < timeout:
            try:
                record = _log_queue.get(block=False)  # Non-blocking get
                # Process directly without using thread-safe handlers
                for handler in logging.getLogger().handlers:
                    if not isinstance(handler, ThreadSafeHandler):
                        try:
                            handler.emit(record)
                        except Exception:
                            pass  # Ignore errors during shutdown
                _log_queue.task_done()
            except Exception:
                break  # Break on any error
    except Exception:
        pass  # Ignore any errors during shutdown
    
    # Wait for the thread to exit (with short timeout)
    if _log_thread and _log_thread.is_alive():
        _log_thread.join(timeout=0.5)  # Shorter timeout to prevent hanging
        
    # If thread is still alive after timeout, we'll just let it be (it's a daemon thread)
    _log_thread = None
