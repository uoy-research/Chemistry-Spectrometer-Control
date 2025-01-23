"""
File: tests/conftest.py
"""

from src.controllers.motor_controller import MotorController
from src.controllers.arduino_controller import ArduinoController
from unittest.mock import Mock
from PyQt6.QtWidgets import QApplication
import pytest
import json
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    app.quit()


@pytest.fixture
def test_config(tmp_path):
    """Create test configuration."""
    config = {
        "arduino": {
            "port": 1,
            "mode": 2  # Test mode
        },
        "motor": {
            "port": 2,
            "mode": 2  # Test mode
        },
        "gui": {
            "update_interval": 100,
            "log_level": "DEBUG"
        }
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    return config_path


@pytest.fixture
def mock_controllers():
    """Create mock controllers."""
    arduino = Mock(spec=ArduinoController)
    motor = Mock(spec=MotorController)

    # Setup default behaviors
    arduino.get_readings.return_value = [1.0, 2.0, 3.0]
    motor.get_position.return_value = 500

    return {
        "arduino": arduino,
        "motor": motor
    }
