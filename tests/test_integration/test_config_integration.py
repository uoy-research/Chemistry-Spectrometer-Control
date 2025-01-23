"""
File: test_config_integration.py
Description: Integration tests for configuration with other components
"""

import pytest
from unittest.mock import patch, Mock
import json
from pathlib import Path
import logging

from src.utils.config import Config, CONFIG_FILE
from src.ui.main_window import MainWindow
from src.workers.arduino_worker import ArduinoWorker
from src.workers.motor_worker import MotorWorker


class TestConfigIntegration:
    """Test suite for configuration integration."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create temporary config file."""
        config_file = tmp_path / "test_config.json"
        test_config = {
            "arduino_port": 1,
            "motor_port": 2,
            "log_level": "INFO",
            "update_interval": 100,
            "max_data_points": 1000
        }
        config_file.write_text(json.dumps(test_config))
        return config_file

    @pytest.fixture
    def config(self, temp_config_file):
        """Create config instance."""
        with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
            return Config()

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        yield
        # Ensure all workers are stopped after each test
        if hasattr(self, 'window'):
            if hasattr(self.window, 'arduino_worker'):
                self.window.arduino_worker.stop()
                self.window.arduino_worker.wait()  # Wait for thread to finish
            if hasattr(self.window, 'motor_worker'):
                self.window.motor_worker.stop()
                self.window.motor_worker.wait()  # Wait for thread to finish
            self.window.close()

    def test_main_window_config_integration(self, qtbot, config):
        """Test main window initialization with config."""
        with patch('src.ui.main_window.Config', return_value=config):
            self.window = MainWindow(test_mode=True)
            qtbot.addWidget(self.window)
            
            # Verify config values applied
            assert self.window.plot_widget.update_interval == config.update_interval
            assert self.window.plot_widget.max_points == config.max_data_points
            assert self.window.arduino_worker.port == config.arduino_port
            assert self.window.motor_worker.port == config.motor_port

    def test_worker_config_integration(self, config):
        """Test worker initialization with config."""
        workers = []
        try:
            # Test Arduino worker
            with patch('src.workers.arduino_worker.Config', return_value=config):
                arduino_worker = ArduinoWorker(port=1, mock=True)
                workers.append(arduino_worker)
                assert arduino_worker.port == config.arduino_port
                assert arduino_worker.update_interval == config.update_interval

            # Test Motor worker
            with patch('src.workers.motor_worker.Config', return_value=config):
                motor_worker = MotorWorker(port=1, mock=True)
                workers.append(motor_worker)
                assert motor_worker.port == config.motor_port
        finally:
            for worker in workers:
                worker.stop()
                worker.wait()

    def test_logging_config_integration(self, config, caplog):
        """Test logging configuration integration."""
        with patch('src.ui.main_window.Config', return_value=config):
            # Set log level in config
            config.log_level = "DEBUG"
            
            # Create window with logging
            window = MainWindow(test_mode=True)
            
            # Verify log level applied
            assert window.logger.level == logging.DEBUG
            assert window.log_widget.logger.level == logging.DEBUG

    def test_config_update_propagation(self, qtbot, config, temp_config_file):
        """Test configuration updates propagating to components."""
        with patch('src.ui.main_window.Config', return_value=config):
            window = MainWindow(test_mode=True)
            qtbot.addWidget(window)

            # Update config
            config.update_interval = 200
            config.save()

            # Load new config
            new_config = Config()
            assert new_config.update_interval == 200

            # Verify components updated
            assert window.plot_widget.update_interval == 200
            assert window.arduino_worker.update_interval == 200

    def test_config_validation(self, config):
        """Test config validation across components."""
        # Test invalid values
        invalid_configs = [
            ("update_interval", -100),
            ("arduino_port", 0),
            ("motor_port", -1),
            ("max_data_points", 0),
            ("log_level", "INVALID")
        ]

        for param, value in invalid_configs:
            with pytest.raises((ValueError, AttributeError)):
                setattr(config, param, value)

    def test_config_persistence(self, temp_config_file):
        """Test config persistence across component restarts."""
        with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
            # First instance
            config1 = Config()
            config1.update_interval = 300
            config1.save()

            # Second instance should load saved values
            config2 = Config()
            assert config2.update_interval == 300

            # Test with components
            window = MainWindow(test_mode=True)
            assert window.plot_widget.update_interval == 300

    def test_config_file_handling(self, tmp_path):
        """Test config file handling scenarios."""
        # Test with missing config file
        nonexistent_file = tmp_path / "nonexistent.json"
        with patch('src.utils.config.CONFIG_FILE', str(nonexistent_file)):
            config = Config()
            assert config.arduino_port == 1  # Default value
            assert config.motor_port == 1    # Default value

        # Test with corrupted config file
        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("invalid json")
        with patch('src.utils.config.CONFIG_FILE', str(corrupt_file)):
            config = Config()
            assert config.arduino_port == 1  # Default value

    def test_config_component_error_handling(self, qtbot, config):
        """Test component error handling with invalid config."""
        with patch('src.ui.main_window.Config', return_value=config):
            # Set invalid config value
            config.update_interval = 0

            # Components should handle invalid config gracefully
            window = MainWindow(test_mode=True)
            qtbot.addWidget(window)
            
            # Should use default values
            assert window.plot_widget.update_interval > 0
            assert window.arduino_worker.update_interval > 0

    def test_config_multi_component_sync(self, qtbot, config):
        """Test configuration synchronization across multiple components."""
        windows = []
        try:
            with patch('src.ui.main_window.Config', return_value=config):
                window1 = MainWindow(test_mode=True)
                window2 = MainWindow(test_mode=True)
                windows = [window1, window2]
                qtbot.addWidget(window1)
                qtbot.addWidget(window2)

                # Update config
                config.update_interval = 250
                config.save()

                # Verify all components updated
                assert window1.plot_widget.update_interval == 250
                assert window2.plot_widget.update_interval == 250
        finally:
            # Clean up windows and workers
            for window in windows:
                if hasattr(window, 'arduino_worker'):
                    window.arduino_worker.stop()
                    window.arduino_worker.wait()
                if hasattr(window, 'motor_worker'):
                    window.motor_worker.stop()
                    window.motor_worker.wait()
                window.close()


def test_config_persistence_integration(temp_config_file):
    """Test config persistence across component restarts."""
    worker = None
    try:
        with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
            # First instance
            config1 = Config()
            config1.update_interval = 300
            config1.save()

            # Create components with new config instance
            config2 = Config()
            worker = ArduinoWorker(port=1, mock=True)  # Use mock mode for testing
            assert worker.update_interval == 300
    finally:
        if worker:
            worker.stop()
            worker.wait()


def test_config_error_handling_integration(qtbot, tmp_path):
    """Test error handling in components with invalid config."""
    window = None
    try:
        invalid_config_file = tmp_path / "invalid_config.json"
        invalid_config_file.write_text("invalid json")

        with patch('src.utils.config.CONFIG_FILE', str(invalid_config_file)):
            window = MainWindow(test_mode=True)
            qtbot.addWidget(window)
            assert window.plot_widget.update_interval == 100  # Default value
    finally:
        if window:
            if hasattr(window, 'arduino_worker'):
                window.arduino_worker.stop()
                window.arduino_worker.wait()
            if hasattr(window, 'motor_worker'):
                window.motor_worker.stop()
                window.motor_worker.wait()
            window.close()
