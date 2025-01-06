"""Base controller interface and mock implementations."""
from abc import ABC, abstractmethod
from typing import List, Optional
import random
import time
import logging

class BaseController(ABC):
    @abstractmethod
    def start(self) -> bool:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

class MockArduinoController(BaseController):
    """Mock Arduino controller for testing."""
    def __init__(self, port: int, verbose: bool = False, mode: int = 1):
        self.port = f"COM{port}"
        self.mode = mode
        self.running = False
        self.valve_states = [0] * 8
        self.pressure_values = [0.0] * 4
        self._last_update = time.time()

    def start(self) -> bool:
        self.running = True
        return True

    def stop(self) -> None:
        self.running = False

    def get_readings(self) -> Optional[List[float]]:
        """Simulate pressure readings with some noise."""
        if not self.running:
            return None

        current_time = time.time()
        dt = current_time - self._last_update
        
        # Add some random walk to the pressure values
        for i in range(len(self.pressure_values)):
            # Make each sensor behave slightly differently
            base_change = random.uniform(-0.1, 0.1) * dt
            if i == 0:  # First sensor (main pressure)
                change = base_change * 2
                self.pressure_values[i] = max(0, min(10, self.pressure_values[i] + change))
            elif i == 1:  # Second sensor (reference)
                change = base_change * 0.5
                self.pressure_values[i] = max(0, min(5, self.pressure_values[i] + change))
            elif i == 2:  # Third sensor (differential)
                change = base_change
                self.pressure_values[i] = max(-2, min(2, self.pressure_values[i] + change))
            else:  # Fourth sensor (atmospheric)
                change = base_change * 0.1
                self.pressure_values[i] = max(0.9, min(1.1, 1.0 + change))
                
        self._last_update = current_time
        return self.pressure_values.copy()

    def set_valves(self, states: List[int]) -> bool:
        """Simulate valve state changes."""
        if not self.running or len(states) != 8:
            return False
        
        self.valve_states = states.copy()
        return True

class MockMotorController(BaseController):
    """Mock motor controller for testing."""
    SPEED_MAX = 1000
    SPEED_MIN = 0
    POSITION_MAX = 1000
    POSITION_MIN = 0

    def __init__(self, port: int, address: int = 1, verbose: bool = False, mode: int = 1):
        self.port = f"COM{port}"
        self._running = False
        self.current_position = 500
        self.target_position = 500
        self._last_update = time.time()
        self.speed = 100  # positions per second
        self.logger = logging.getLogger(__name__)

    def start(self) -> bool:
        self._running = True
        return True

    def stop(self) -> None:
        self._running = False

    @property
    def running(self) -> bool:
        """Get running state."""
        return self._running

    @running.setter
    def running(self, value: bool):
        """Set running state."""
        self._running = value

    def get_position(self) -> Optional[int]:
        """Simulate motor movement."""
        if not self._running:
            return None

        current_time = time.time()
        dt = current_time - self._last_update
        
        if self.current_position != self.target_position:
            # Calculate movement direction and distance
            direction = 1 if self.target_position > self.current_position else -1
            distance = min(abs(self.target_position - self.current_position), 
                         self.speed * dt)
            
            # Update position
            self.current_position += direction * distance
            
        self._last_update = current_time
        return round(self.current_position)

    def set_position(self, position: int, wait: bool = False) -> bool:
        """Set target position."""
        if not self._running:
            return False

        if not self.POSITION_MIN <= position <= self.POSITION_MAX:
            return False

        self.target_position = position
        
        if wait:
            while self.get_position() != position:
                time.sleep(0.1)
        
        return True 

    def stop_motor(self) -> bool:
        """Stop motor movement."""
        self._running = False
        return True 