"""
File: step.py
Description: Defines the Step class for sequence control operations.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Step:
    """
    Represents a single step in a control sequence.
    
    Attributes:
        step_type: Type of step ('d' - Delay, 'p' - Pressurize, 'v' - Vent, 
                               'b' - Bubble, 'f' - Flow, 'e' - Evacuate)
        time_length: Duration of step in milliseconds
        motor_position: Optional motor position for the step
    """
    step_type: str
    time_length: int
    motor_position: Optional[int] = None

    def __post_init__(self):
        """Validate step attributes after initialization."""
        self._validate_step_type()
        self._validate_time_length()
        self._validate_motor_position()

    def _validate_step_type(self):
        """Ensure step_type is valid."""
        valid_types = {'d', 'p', 'v', 'b', 'f', 'e'}  # Updated to match MainWindow
        if self.step_type not in valid_types:
            raise ValueError(f"Invalid step type: {self.step_type}. "
                           f"Must be one of: {valid_types}")

    def _validate_time_length(self):
        """Ensure time_length is positive."""
        if self.time_length <= 0:
            raise ValueError("Time length must be positive, got: "
                           f"{self.time_length}")

    def _validate_motor_position(self):
        """Ensure motor_position is valid if provided."""
        if self.motor_position is not None:
            if not isinstance(self.motor_position, int):
                raise ValueError("Motor position must be an integer, got: "
                               f"{type(self.motor_position)}")
