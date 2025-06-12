import os
import yaml
import json
import sys
import logging
from typing import Dict, Optional, Literal

ValveState = Literal['open', 'close', 'ignore']


class ConfigManager:
    """
    Manages configuration settings for the application.
    """

    def __init__(self):
        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Get the base directory (where the executable is located)
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle (executable)
            self.base_dir = os.path.dirname(sys.executable)
            #self.logger.info(
            #    "Running as executable, base directory: %s", self.base_dir)
        else:
            # If the application is run from a Python interpreter
            self.base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(__file__)))
            #self.logger.info(
            #    "Running from Python interpreter, base directory: %s", self.base_dir)

        # Look for config in the executable directory first
        self.config_dir = os.path.join(self.base_dir, 'SSBubble/config')
        self.valve_config_path = os.path.join(
            self.config_dir, 'valve_config.yaml')
        self.motor_macros_path = os.path.join(
            self.config_dir, 'motor_macros.json')
        self.valve_macros_path = os.path.join(
            self.config_dir, 'valve_macros.json')
        #self.logger.info("Looking for valve config at: %s",
        #                 self.valve_config_path)

        # If not found, try the src/config directory
        if not os.path.exists(self.valve_config_path):
            #self.logger.warning(
            #    "Valve config not found in executable directory")
            self.config_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 'config')
            self.valve_config_path = os.path.join(
                self.config_dir, 'valve_config.yaml')
            self.motor_macros_path = os.path.join(
                self.config_dir, 'motor_macros.json')
            self.valve_macros_path = os.path.join(
                self.config_dir, 'valve_macros.json')
            #self.logger.info(
            #    "Looking for valve config in source directory: %s", self.valve_config_path)

        self.valve_config = self._load_valve_config()
        self.motor_macros = self._load_motor_macros()
        self.valve_macros = self._load_valve_macros()

    def _load_motor_macros(self) -> Dict:
        """
        Load motor macros from JSON file.
        """
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)

            if not os.path.exists(self.motor_macros_path):
                # Create default motor macros if file doesn't exist
                default_macros = {
                    str(i): {
                        "Label": f"Motor Macro {i}",
                        "Position": 0
                    } for i in range(1, 5)
                }
                with open(self.motor_macros_path, 'w') as f:
                    json.dump(default_macros, f, indent=4)
                return default_macros

            with open(self.motor_macros_path, 'r') as f:
                macros = json.load(f)
                # Filter out macros 5 and 6 if they exist
                return {k: v for k, v in macros.items() if int(k) <= 4}
        except Exception as e:
            self.logger.error(f"Error loading motor macros: {e}")
            return {}

    def _load_valve_macros(self) -> Dict:
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
            if not os.path.exists(self.valve_macros_path):
                default_macros = {
                    str(i): {
                        "Label": f"Macro {i}",
                        "Valves": [0, 0, 0, 0, 0, 0, 0, 0],
                        "Timer": 1.0
                    } for i in range(1, 5)
                }
                with open(self.valve_macros_path, 'w') as f:
                    json.dump(default_macros, f, indent=4)
                return default_macros
            with open(self.valve_macros_path, 'r') as f:
                macros = json.load(f)
                return macros
        except Exception as e:
            self.logger.error(f"Error loading valve macros: {e}")
            return {}

    def _load_valve_config(self) -> Dict:
        """
        Load valve configuration from YAML file.
        """
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
                #self.logger.info(
                #    "Created config directory: %s", self.config_dir)

            if not os.path.exists(self.valve_config_path):
                #self.logger.error(
                #    "Valve configuration file not found at: %s", self.valve_config_path)
                return {}

            with open(self.valve_config_path, 'r') as f:
                config = yaml.safe_load(f)
                #self.logger.info(
                #    "Successfully loaded valve configuration from: %s", self.valve_config_path)
                return config
        except Exception as e:
            self.logger.error("Error loading valve configuration: %s", str(e))
            return {}

    def _validate_valve_state(self, state: str) -> bool:
        """
        Validate that a valve state is one of the allowed values.

        Args:
            state: The valve state to validate

        Returns:
            bool: True if the state is valid, False otherwise
        """
        return state in ('open', 'close', 'ignore')

    def get_step_valve_states(self, step_type: str) -> Optional[Dict[int, ValveState]]:
        """
        Get valve states for a specific step type.

        Args:
            step_type: Single character step type identifier ('p', 'v', 'b', etc.)

        Returns:
            Dictionary mapping valve numbers to their states ('open', 'close', or 'ignore')
            or None if step type is not found
        """
        try:
            # Find the step type configuration by matching the 'type' field
            step_config = next(
                (config for config in self.valve_config.get('step_types', {}).values()
                 if config.get('type') == step_type),
                None
            )

            if step_config is None:
                self.logger.warning(
                    "No configuration found for step type: %s", step_type)
                return None

            valves = step_config.get('valves', {})

            # Validate all valve states
            for valve_num, state in valves.items():
                if not self._validate_valve_state(state):
                    self.logger.error("Invalid valve state '%s' for valve %s in step type %s",
                                      state, valve_num, step_type)
                    return None

            self.logger.debug(
                "Retrieved valve states for step type %s: %s", step_type, valves)
            return valves
        except Exception as e:
            self.logger.error(
                "Error getting valve states for step type %s: %s", step_type, str(e))
            return None

    def reload_config(self):
        """
        Reload configuration from files.
        """
        self.logger.info("Reloading configurations...")
        self.valve_config = self._load_valve_config()
        self.motor_macros = self._load_motor_macros()
        self.valve_macros = self._load_valve_macros()

    def update_valve_macro(self, macro_num: int, macro_data: dict):
        """
        Update a valve macro in the config.
        Args:
            macro_num: The macro number (1-4)
            macro_data: Dictionary containing the macro data
        """
        try:
            self.valve_macros[str(macro_num)] = {
                'Label': macro_data.get('Label', f'Macro {macro_num}'),
                'Valves': macro_data.get('Valves', [0] * 8),
                'Timer': macro_data.get('Timer', 1.0)
            }
            with open(self.valve_macros_path, 'w') as f:
                json.dump(self.valve_macros, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error updating valve macro {macro_num}: {e}")

    def update_motor_macro(self, macro_num: int, macro_data: dict):
        """
        Update a motor macro in the config.
        Args:
            macro_num: The macro number (1-6)
            macro_data: Dictionary containing the macro data
        """
        try:
            self.motor_macros[str(macro_num)] = {
                'Label': macro_data.get('Label', f'Motor Macro {macro_num}'),
                'Position': macro_data.get('Position', 0)
            }
            # Save the updated motor macros
            with open(self.motor_macros_path, 'w') as f:
                json.dump(self.motor_macros, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error updating motor macro {macro_num}: {e}")

    def save_config(self):
        """Save the current configuration to file."""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
            with open(self.valve_config_path, 'w') as f:
                yaml.dump(self.valve_config, f, default_flow_style=False)
            #self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
