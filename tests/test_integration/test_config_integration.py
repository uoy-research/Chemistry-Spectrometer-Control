"""
File: test_config_integration.py
Description: Integration tests for configuration with other components
"""

import pytest
from unittest.mock import patch
import json
from pathlib import Path

from src.utils.config import Config
from src.ui.main_window import MainWindow
from src.workers.arduino_worker import ArduinoWorker
from src.workers.motor_worker import MotorWorker
from src.models.valve_macro import MacroManager


@pytest.fixture
def temp_config_file(tmp_path):
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
def config(temp_config_file):
    """Create config instance."""
    with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
        return Config()


def test_main_window_config_integration(qtbot, config):
    """Test main window initialization with config."""
    with patch('src.ui.main_window.Config', return_value=config):
        window = MainWindow()
        qtbot.addWidget(window)

        # Verify config values applied
        assert window.plot_widget.update_interval == config.update_interval
        assert window.plot_widget.max_points == config.max_data_points


def test_arduino_worker_config_integration(config):
    """Test Arduino worker initialization with config."""
    with patch('src.workers.arduino_worker.Config', return_value=config):
        worker = ArduinoWorker()

        assert worker.port == f"COM{config.arduino_port}"
        assert worker.update_interval == config.update_interval


def test_motor_worker_config_integration(config):
    """Test motor worker initialization with config."""
    with patch('src.workers.motor_worker.Config', return_value=config):
        worker = MotorWorker()

        assert worker.port == f"COM{config.motor_port}"


def test_macro_manager_config_integration(config, tmp_path):
    """Test macro manager initialization with config."""
    # Create test macro file
    macro_file = tmp_path / "macros.json"
    macro_file.write_text("{}")

    with patch('src.models.valve_macro.Config', return_value=config):
        manager = MacroManager()
        assert str(manager.macro_file) == str(macro_file)


def test_config_update_propagation(qtbot, config):
    """Test configuration updates propagating to components."""
    with patch('src.ui.main_window.Config', return_value=config):
        window = MainWindow()
        qtbot.addWidget(window)

        # Update config
        config.update_interval = 200
        config.save()

        # Verify components updated
        assert window.plot_widget.update_interval == 200
        assert window.arduino_worker.update_interval == 200


def test_config_validation_integration(config):
    """Test config validation across components."""
    with pytest.raises(ValueError):
        config.update_interval = -100  # Invalid interval

    with pytest.raises(ValueError):
        config.arduino_port = 0  # Invalid port


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
