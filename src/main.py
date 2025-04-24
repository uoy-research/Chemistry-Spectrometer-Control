"""
File: main.py
Description: Main entry point for the SSBubble application
"""

# Set matplotlib backend BEFORE any other matplotlib imports
from utils.logger import setup_logging
from utils.config import Config
from ui.main_window import MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import argparse
from pathlib import Path
import logging
import sys
import matplotlib
matplotlib.use('QtAgg')

# System imports

# Qt imports

# Internal imports - these should come after matplotlib.use()


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
    """Main entry point for the application."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description='SSBubble Control Application')
        parser.add_argument('--config', type=str, help='Path to config file')
        parser.add_argument('--debug', action='store_true',
                            help='Enable debug mode')
        parser.add_argument('--timing', action='store_true',
                            help='Enable timing mode')
        parser.add_argument('--test', action='store_true',
                            help='Use mock controllers for testing')
        parser.add_argument('--keep-sequence', action='store_true',
                            help='Keep sequence file after processing')
        args = parser.parse_args()

        # Set up logging (without debug parameter)
        setup_logging()

        # If debug mode is enabled, set log level to DEBUG
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Debug logging enabled")

        # Create application
        app = QApplication(sys.argv)

        # Create main window with args
        window = MainWindow(
            test_mode=args.test,
            keep_sequence=args.keep_sequence,
            timing_mode=args.timing,
            args=args  # Pass all args to the window
        )

        # Show window
        window.show()

        # Run application
        return app.exec()

    except Exception as e:
        logging.error(f"Application error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
