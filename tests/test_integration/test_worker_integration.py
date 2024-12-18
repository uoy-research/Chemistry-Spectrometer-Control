"""
File: test_worker_integration.py
Description: Integration tests between workers
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QThread

from src.workers.arduino_worker import ArduinoWorker
from src.workers.motor_worker import MotorWorker
from src.models.valve_macro import MacroManager, ValveMacro


@pytest.fixture
def workers():
    """Create worker instances."""
    arduino = ArduinoWorker(mode=2)  # Test mode
    motor = MotorWorker(mode=2)      # Test mode
    return arduino, motor


def test_worker_initialization(workers):
    """Test worker initialization and interaction."""
    arduino, motor = workers

    # Start workers
    arduino.start()
    motor.start()

    # Verify both running
    assert arduino.running
    assert motor.running

    # Stop workers
    arduino.stop()
    motor.stop()

    # Verify both stopped
    assert not arduino.running
    assert not motor.running


def test_synchronized_operations(workers):
    """Test synchronized operations between workers."""
    arduino, motor = workers
    arduino.start()
    motor.start()

    # Move motor and set valves
    motor.move_to(100)
    arduino.set_valves([1] * 8)

    # Verify operations completed
    assert motor.get_position() == 100
    assert arduino.get_readings() is not None


def test_error_handling_between_workers(workers):
    """Test error handling between workers."""
    arduino, motor = workers
    arduino.start()
    motor.start()

    # Simulate error in arduino
    with patch.object(arduino, 'get_readings', side_effect=Exception("Arduino error")):
        readings = arduino.get_readings()

        # Verify motor still operational
        assert motor.get_position() is not None
        assert readings is None


def test_macro_execution_with_workers(workers, tmp_path):
    """Test macro execution using both workers."""
    arduino, motor = workers
    arduino.start()
    motor.start()

    # Create test macro
    macro_file = tmp_path / "test_macros.json"
    macro_file.write_text("{}")
    manager = MacroManager(macro_file)

    macro = ValveMacro(
        label="Test Macro",
        valve_states=[1] * 8,
        timer=1.0
    )
    manager.macros["test"] = macro

    # Execute macro
    arduino.set_valves(macro.valve_states)
    motor.move_to(100)  # Simultaneous motor movement

    # Verify execution
    assert arduino.get_readings() is not None
    assert motor.get_position() == 100


def test_worker_thread_safety(workers):
    """Test thread safety between workers."""
    arduino, motor = workers
    arduino.start()
    motor.start()

    # Create threads
    arduino_thread = QThread()
    motor_thread = QThread()

    arduino.moveToThread(arduino_thread)
    motor.moveToThread(motor_thread)

    # Start threads
    arduino_thread.start()
    motor_thread.start()

    # Perform operations
    arduino.set_valves([1] * 8)
    motor.move_to(100)

    # Clean up
    arduino_thread.quit()
    motor_thread.quit()
    arduino_thread.wait()
    motor_thread.wait()


def test_worker_state_synchronization(workers):
    """Test state synchronization between workers."""
    arduino, motor = workers

    # Test synchronized start
    arduino.start()
    motor.start()
    assert arduino.running and motor.running

    # Test synchronized stop
    arduino.stop()
    motor.stop()
    assert not arduino.running and not motor.running


def test_worker_data_exchange(workers):
    """Test data exchange between workers."""
    arduino, motor = workers
    arduino.start()
    motor.start()

    # Get readings and position
    readings = arduino.get_readings()
    position = motor.get_position()

    # Verify data exchange
    assert readings is not None
    assert position is not None


def test_emergency_handling(workers):
    """Test emergency situation handling."""
    arduino, motor = workers
    arduino.start()
    motor.start()

    # Simulate emergency
    motor.stop()  # Emergency stop motor
    arduino.depressurize()  # Emergency depressurize

    # Verify safe state
    assert not motor.running
    assert arduino.get_readings() is not None


def test_worker_recovery(workers):
    """Test worker recovery after errors."""
    arduino, motor = workers

    # Simulate failure and recovery
    with patch.object(arduino, 'start', side_effect=[Exception("Start error"), True]):
        assert not arduino.start()  # First attempt fails
        assert arduino.start()      # Second attempt succeeds

    # Verify system still operational
    assert arduino.get_readings() is not None
    assert motor.start()
