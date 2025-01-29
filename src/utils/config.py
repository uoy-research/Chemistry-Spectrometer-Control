"""
File: src/utils/config.py
"""

import json
from pathlib import Path
import sys
import logging

CONFIG_FILE = "config.json"


class Config:
    def __init__(self):
        self.arduino_port = 1
        self.motor_port = 1
        self.macro_file = "macros.json"
        self.log_level = "INFO"
        self.update_interval = 100
        self.max_data_points = 1000
        self.load()

    def get_app_path(self):
        """Get the application base path."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return Path(sys.executable).parent
        else:
            # Running from source
            return Path(__file__).parent.parent.parent

    def load(self):
        """Load configuration from file."""
        try:
            # Use path relative to executable/source
            config_path = self.get_app_path() / 'config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        setattr(self, key, value)
            else:
                self.default_config = {
                    'arduino_port': self.arduino_port,
                    'motor_port': self.motor_port,
                    'macro_file': self.macro_file,
                    'log_level': self.log_level,
                    'update_interval': self.update_interval,
                    'max_data_points': self.max_data_points
                }
                self.save()
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self._config = self.default_config

    def save(self):
        """Save configuration to file."""
        data = {
            'arduino_port': self.arduino_port,
            'motor_port': self.motor_port,
            'macro_file': self.macro_file,
            'log_level': self.log_level,
            'update_interval': self.update_interval,
            'max_data_points': self.max_data_points
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
