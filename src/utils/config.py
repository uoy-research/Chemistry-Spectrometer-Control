"""
File: src/utils/config.py
"""

import json
import os
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
        self.motor_update_interval = 0.1  # Default 100ms update interval
        self.dev_password = "DanT"  # Add default dev password
        self.load()

    def get_app_path(self):
        """Get the application base path."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return Path(sys.executable).parent
        else:
            # Running from source
            return Path(__file__).parent.parent.parent

    def get_config_dir(self):
        """Get the configuration directory path."""
        base_path = self.get_app_path()
        config_dir = base_path / 'SSBubble' / 'config'

        # Create the directory if it doesn't exist
        if not config_dir.exists():
            try:
                config_dir.mkdir(parents=True, exist_ok=True)
                logging.info(f"Created config directory: {config_dir}")
            except Exception as e:
                logging.error(f"Error creating config directory: {e}")
                # Fall back to base path if we can't create the config directory
                return base_path

        return config_dir

    def load(self):
        """Load configuration from file."""
        try:
            # First check if config.json exists in the old location (base directory)
            old_config_path = self.get_app_path() / CONFIG_FILE
            new_config_path = self.get_config_dir() / CONFIG_FILE

            # If config exists in old location but not in new location, migrate it
            if old_config_path.exists() and not new_config_path.exists():
                try:
                    with open(old_config_path, 'r') as f:
                        data = json.load(f)

                    # Save to new location
                    with open(new_config_path, 'w') as f:
                        json.dump(data, f, indent=4)

                    logging.info(
                        f"Migrated config.json from {old_config_path} to {new_config_path}")

                    # Optionally delete the old file
                    # old_config_path.unlink()
                    # logging.info(f"Deleted old config file: {old_config_path}")
                except Exception as e:
                    logging.error(f"Error migrating config file: {e}")

            # Use the new config path
            config_path = new_config_path
            if config_path.exists():
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        setattr(self, key, value)
                    self.motor_update_interval = data.get(
                        'motor_update_interval', 0.1)
                    # Load password with default
                    self.dev_password = data.get('dev_password', 'DanT')
            else:
                self.default_config = {
                    'arduino_port': self.arduino_port,
                    'motor_port': self.motor_port,
                    'macro_file': self.macro_file,
                    'log_level': self.log_level,
                    'update_interval': self.update_interval,
                    'max_data_points': self.max_data_points,
                    'motor_update_interval': self.motor_update_interval,
                    'dev_password': self.dev_password  # Add to defaults
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
            'max_data_points': self.max_data_points,
            'motor_update_interval': self.motor_update_interval,
            'dev_password': self.dev_password  # Add to save data
        }
        try:
            config_path = self.get_config_dir() / CONFIG_FILE
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=4)
                logging.info(f"Saved configuration to {config_path}")
        except Exception as e:
            logging.error(f"Error saving config: {e}")
