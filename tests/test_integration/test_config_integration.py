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
from src.models.valve_macro import MacroManager


class TestConfigIntegration:
    """Test suite for configuration integration."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create temporary config file."""
        config_file = tmp_path / "test_config.json"
        test_config = {
            "arduino_port": 1,
            "motor_port": 2,
            "macro_file": str(tmp_path / "macros.json"),
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

    def test_main_window_config_integration(self, qtbot, config):
        """Test main window initialization with config."""
        with patch('src.ui.main_window.Config', return_value=config):
            window = MainWindow(test_mode=True)
            qtbot.addWidget(window)

            # Verify config values applied
            assert window.plot_widget.update_interval == config.update_interval
            assert window.plot_widget.max_points == config.max_data_points
            assert window.arduino_worker.port == config.arduino_port
            assert window.motor_worker.port == config.motor_port

    def test_worker_config_integration(self, config):
        """Test worker initialization with config."""
        # Test Arduino worker
        with patch('src.workers.arduino_worker.Config', return_value=config):
            arduino_worker = ArduinoWorker()
            assert arduino_worker.port == config.arduino_port
            assert arduino_worker.update_interval == config.update_interval

        # Test Motor worker
        with patch('src.workers.motor_worker.Config', return_value=config):
            motor_worker = MotorWorker()
            assert motor_worker.port == config.motor_port

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
        with patch('src.ui.main_window.Config', return_value=config):
            # Create multiple components
            window1 = MainWindow(test_mode=True)
            window2 = MainWindow(test_mode=True)
            qtbot.addWidget(window1)
            qtbot.addWidget(window2)

            # Update config
            config.update_interval = 250
            config.save()

            # Verify all components updated
            assert window1.plot_widget.update_interval == 250
            assert window2.plot_widget.update_interval == 250


def test_macro_manager_config_integration(config, tmp_path):
    """Test macro manager initialization with config."""
    # Create test macro file
    macro_file = tmp_path / "macros.json"
    macro_file.write_text("{}")

    with patch('src.models.valve_macro.Config', return_value=config):
        manager = MacroManager()
        assert str(manager.macro_file) == str(macro_file)


def test_config_persistence_integration(temp_config_file):
    """Test config persistence across component restarts."""
    with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
        # First instance
        config1 = Config()
        config1.update_interval = 300
        config1.save()

        # Create components with new config instance
        config2 = Config()
        worker = ArduinoWorker()
        assert worker.update_interval == 300


def test_config_error_handling_integration(qtbot, tmp_path):
    """Test error handling in components with invalid config."""
    invalid_config_file = tmp_path / "invalid_config.json"
    invalid_config_file.write_text("invalid json")

    with patch('src.utils.config.CONFIG_FILE', str(invalid_config_file)):
        # Should use default values
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.plot_widget.update_interval == 100  # Default value
