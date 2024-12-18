"""
File: test_config.py
Description: Tests for configuration management
"""

import pytest
import json
import os
from unittest.mock import mock_open, patch
from pathlib import Path

from src.utils.config import Config


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file."""
    config_file = tmp_path / "test_config.json"
    test_config = {
        "arduino_port": 1,
        "motor_port": 2,
        "macro_file": "macros.json",
        "log_level": "INFO",
        "update_interval": 100,
        "max_data_points": 1000
    }
    config_file.write_text(json.dumps(test_config))
    return config_file


@pytest.fixture
def config(temp_config_file):
    """Create config instance with test file."""
    with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
        return Config()


def test_initialization(config):
    """Test config initialization."""
    assert isinstance(config.arduino_port, int)
    assert isinstance(config.motor_port, int)
    assert isinstance(config.macro_file, str)
    assert isinstance(config.log_level, str)
    assert isinstance(config.update_interval, int)
    assert isinstance(config.max_data_points, int)


def test_default_values():
    """Test default configuration values."""
    with patch('pathlib.Path.exists', return_value=False):
        config = Config()
        assert config.arduino_port == 1  # Verify default values
        assert config.motor_port == 1
        assert config.log_level == "INFO"
        assert config.update_interval == 100
        assert config.max_data_points == 1000


def test_load_config(temp_config_file):
    """Test loading configuration from file."""
    with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
        config = Config()
        assert config.arduino_port == 1
        assert config.motor_port == 2
        assert config.macro_file == "macros.json"


def test_save_config(config, temp_config_file):
    """Test saving configuration to file."""
    # Modify config
    config.arduino_port = 3
    config.motor_port = 4
    config.save()

    # Read saved config
    with open(temp_config_file) as f:
        saved_config = json.load(f)

    assert saved_config["arduino_port"] == 3
    assert saved_config["motor_port"] == 4


def test_invalid_config_file():
    """Test handling of invalid config file."""
    with patch('pathlib.Path.exists', return_value=True), \
            patch('builtins.open', mock_open(read_data="invalid json")):
        config = Config()
        # Should use default values when config file is invalid
        assert config.arduino_port == 1
        assert config.motor_port == 1


def test_missing_config_file():
    """Test handling of missing config file."""
    with patch('pathlib.Path.exists', return_value=False):
        config = Config()
        # Should create new file with default values
        assert config.arduino_port == 1
        assert config.motor_port == 1


@pytest.mark.parametrize("attr,value,expected", [
    ("arduino_port", 5, 5),
    ("motor_port", 3, 3),
    ("log_level", "DEBUG", "DEBUG"),
    ("update_interval", 200, 200),
    ("max_data_points", 2000, 2000),
])
def test_attribute_setting(config, attr, value, expected):
    """Test setting configuration attributes."""
    setattr(config, attr, value)
    assert getattr(config, attr) == expected


def test_config_validation(config):
    """Test configuration validation."""
    # Test invalid port numbers
    with pytest.raises(ValueError):
        config.arduino_port = -1
    with pytest.raises(ValueError):
        config.motor_port = 0

    # Test invalid log level
    with pytest.raises(ValueError):
        config.log_level = "INVALID"

    # Test invalid intervals
    with pytest.raises(ValueError):
        config.update_interval = -100
    with pytest.raises(ValueError):
        config.max_data_points = 0


def test_config_persistence(temp_config_file):
    """Test configuration persistence across instances."""
    with patch('src.utils.config.CONFIG_FILE', str(temp_config_file)):
        # First instance
        config1 = Config()
        config1.arduino_port = 5
        config1.save()

        # Second instance
        config2 = Config()
        assert config2.arduino_port == 5


def test_config_file_permissions(tmp_path):
    """Test handling of file permission issues."""
    config_file = tmp_path / "readonly_config.json"
    config_file.touch()
    config_file.chmod(0o444)  # Read-only

    with patch('src.utils.config.CONFIG_FILE', str(config_file)):
        config = Config()
        # Should not raise exception, but log error
        config.save()
