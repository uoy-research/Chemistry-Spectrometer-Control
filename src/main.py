"""
File: main.py
Description: Main entry point for the SSBubble application
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Use relative imports since we're inside the package
from ui.main_window import MainWindow
from utils.config import Config
from utils.logger import setup_logging


def setup_exception_handling(app):
    """Setup global exception handler."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle keyboard interrupt
            app.quit()
            return

        logging.error("Uncaught exception", exc_info=(
            exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


def main():
    """Main application entry point."""
    # Initialize logging first, before any other operations
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger('SSBubble')
    
    # Log that we're starting
    logger.info("=== Starting SSBubble application ===")
    
    try:
        # Log Python path for debugging
        logger.debug(f"Python path: {sys.path}")
        logger.debug(f"Current working directory: {Path.cwd()}")

        # Create Qt application
        logger.debug("Creating QApplication")
        app = QApplication(sys.argv)
        app.setApplicationName("SSBubble")

        # Set up exception handling
        logger.debug("Setting up exception handling")
        setup_exception_handling(app)

        # Load configuration
        logger.debug("Loading configuration")
        config = Config()

        # Check for --test flag
        test_mode = "--test" in sys.argv
        logger.info(f"Test mode: {test_mode}")
        
        # Create and show main window
        logger.debug("Creating main window")
        window = MainWindow(test_mode=test_mode)
        logger.debug("Showing main window")
        window.show()

        # Start Qt event loop
        logger.debug("Starting Qt event loop")
        exit_code = app.exec()

        # Clean up
        logger.info("Application shutting down")
        return exit_code

    except ImportError as e:
        logging.error(f"Import error: {e}", exc_info=True)
        logging.error(f"Module name: {getattr(e, 'name', 'unknown')}")
        logging.error(f"Module path: {getattr(e, 'path', 'unknown')}")
        return 1
    except Exception as e:
        logging.error(f"Failed to start application: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
