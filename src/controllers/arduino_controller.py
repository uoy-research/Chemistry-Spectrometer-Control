"""
File: src/controllers/arduino_controller.py
Description: Arduino controller using minimalmodbus for valve control and pressure readings
"""

import minimalmodbus
import logging
import time
from typing import List, Optional

class ArduinoController:
    """Arduino controller class using minimalmodbus."""
    
    # Modbus addresses
    VALVE_ADDRESSES = list(range(8))  # Coils 0-7 for valve states
    PRESSURE_ADDRESSES = list(range(4))  # Registers 0-3 for pressure readings
    TTL_ADDRESS = 16  # Coil for TTL control
    RESET_ADDRESS = 17  # Coil for system reset
    DEPRESSURIZE_ADDRESS = 18  # Coil for system depressurization

    def __init__(self, port: int, verbose: bool = False, mode: int = 0):
        """Initialize Arduino controller.
        
        Args:
            port: COM port number
            verbose: Enable verbose logging
            mode: Operating mode (0=manual, 1=sequence, 2=TTL)
        """
        self.port = port
        self.verbose = verbose
        self.mode = mode
        self.running = False
        self.arduino = None
        
        # Setup logging
        self._setup_logging()
        
        # Log mode
        modes = {0: "Manual", 1: "Sequence", 2: "TTL"}
        self.logger.debug(f"Initializing in {modes.get(mode, 'Unknown')} mode")

    def _setup_logging(self):
        """Setup logging configuration."""
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.DEBUG)

        # Add a console handler if none exists
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def start(self) -> bool:
        """Start the Arduino connection.
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Create Modbus instrument
            self.arduino = minimalmodbus.Instrument(f"COM{self.port}", 10)
            self.arduino.serial.baudrate = 9600
            self.arduino.serial.timeout = 3

            # Wait for Arduino to boot
            time.sleep(1)
            
            # Test connection by reading pressure values
            _ = self.arduino.read_registers(0, 4, 4)
            
            # Set TTL mode if needed
            if self.mode == 2:
                self.arduino.write_bit(self.TTL_ADDRESS, 1)
            else:
                self.arduino.write_bit(self.TTL_ADDRESS, 0)
            
            self.running = True
            self.logger.info(f"Connected to Arduino on COM{self.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Arduino: {e}")
            self.running = False
            return False

    def get_readings(self) -> Optional[List[float]]:
        """Get pressure readings from Arduino and convert to standard units.
        
        Returns:
            List of 4 pressure readings in standard units or None if error
        """
        if not self.running:
            return None

        try:
            # Read 4 pressure registers using function code 4
            raw_readings = self.arduino.read_registers(0, 4, 4)
            
            # Convert readings to standard units
            converted_readings = [
                (float(raw) - 203.53) / 0.8248 / 100 
                for raw in raw_readings
            ]
            
            self.logger.debug(f"Raw pressure readings: {raw_readings}")
            self.logger.debug(f"Converted pressure readings: {converted_readings}")
            return converted_readings

        except Exception as e:
            self.logger.error(f"Error getting readings: {e}")
            self.running = False
            return None

    def set_valves(self, states: List[int]) -> bool:
        """Set valve states.
        
        Args:
            states: List of 8 valve states (0 or 1)
            
        Returns:
            bool: True if successful
        """
        if not self.running:
            return False

        if len(states) != 8 or not all(x in [0, 1] for x in states):
            return False

        try:
            # Write all valve states at once
            self.arduino.write_bits(0, states)
            return True

        except Exception as e:
            self.logger.error(f"Error setting valves: {e}")
            self.running = False
            return False

    def stop(self):
        """Stop the Arduino connection."""
        if self.arduino and hasattr(self.arduino, 'serial'):
            try:
                # Disable TTL if enabled
                if self.mode == 2:
                    self.arduino.write_bit(self.TTL_ADDRESS, 0)
                # Close serial connection
                self.arduino.serial.close()
            except Exception as e:
                self.logger.error(f"Error closing Arduino connection: {e}")
        self.running = False

    def reset(self) -> bool:
        """Reset the system.
        
        Returns:
            bool: True if successful
        """
        if not self.running:
            return False
            
        try:
            self.arduino.write_bit(self.RESET_ADDRESS, 1)
            return True
        except Exception as e:
            self.logger.error(f"Error resetting system: {e}")
            return False

    def depressurize(self) -> bool:
        """Depressurize the system.
        
        Returns:
            bool: True if successful
        """
        if not self.running:
            return False
            
        try:
            self.arduino.write_bit(self.DEPRESSURIZE_ADDRESS, 1)
            return True
        except Exception as e:
            self.logger.error(f"Error depressurizing system: {e}")
            return False
