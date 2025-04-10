import os
import yaml
from typing import Dict, Optional, Literal

ValveState = Literal['open', 'close', 'ignore']

class ConfigManager:
    """
    Manages configuration settings for the application.
    """
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        self.valve_config_path = os.path.join(self.config_dir, 'valve_config.yaml')
        self.valve_config = self._load_valve_config()

    def _load_valve_config(self) -> Dict:
        """
        Load valve configuration from YAML file.
        """
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
            
            if not os.path.exists(self.valve_config_path):
                return {}

            with open(self.valve_config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading valve configuration: {e}")
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
                return None
                
            valves = step_config.get('valves', {})
            
            # Validate all valve states
            for valve_num, state in valves.items():
                if not self._validate_valve_state(state):
                    print(f"Warning: Invalid valve state '{state}' for valve {valve_num} in step type {step_type}")
                    return None
                    
            return valves
        except Exception as e:
            print(f"Error getting valve states for step type {step_type}: {e}")
            return None

    def reload_config(self):
        """
        Reload configuration from files.
        """
        self.valve_config = self._load_valve_config() 