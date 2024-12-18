"""
File: valve_macro.py
Description: Defines the ValveMacro class for storing valve macro configurations.
"""

from dataclasses import dataclass
from typing import List
import json
from pathlib import Path


@dataclass
class ValveMacro:
    """Represents a valve macro configuration."""
    label: str
    valve_states: List[int]
    timer: float

    def __post_init__(self):
        """Validate macro attributes after initialization."""
        self._validate_valve_states()
        self._validate_timer()

    def _validate_valve_states(self):
        """Ensure valve states are valid."""
        if len(self.valve_states) != 8:
            raise ValueError("Must specify exactly 8 valve states")

        valid_states = {0, 1, 2}  # closed, open, unchanged
        invalid_states = [
            s for s in self.valve_states if s not in valid_states]
        if invalid_states:
            raise ValueError(f"Invalid valve states: {invalid_states}. "
                             f"Must be one of: {valid_states}")

    def _validate_timer(self):
        """Ensure timer value is valid."""
        if self.timer <= 0:
            raise ValueError(f"Timer must be positive, got: {self.timer}")


class MacroManager:
    """Manages saving and loading of valve macros."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.macros = {}

    def load_macros(self) -> None:
        """Load macros from configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            self.macros = {
                key: ValveMacro(
                    label=macro_data["Label"],
                    valve_states=macro_data["Valves"],
                    timer=macro_data["Timer"]
                )
                for key, macro_data in data.items()
            }
        except FileNotFoundError:
            self._create_default_macros()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid macro configuration file: {e}")

    def save_macros(self) -> None:
        """Save current macros to configuration file."""
        data = {
            key: {
                "Label": macro.label,
                "Valves": macro.valve_states,
                "Timer": macro.timer
            }
            for key, macro in self.macros.items()
        }

        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=4)

    def _create_default_macros(self) -> None:
        """Create and save default macro configurations."""
        self.macros = {
            str(i): ValveMacro(
                label=f"Macro {i}",
                valve_states=[2] * 8,
                timer=1.0
            )
            for i in range(1, 5)
        }
        self.save_macros()

    def get_macro(self, key: str) -> ValveMacro:
        """Get a specific macro by key."""
        if key not in self.macros:
            raise KeyError(f"Macro not found: {key}")
        return self.macros[key]
