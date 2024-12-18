"""
File: test_step.py
Description: Unit tests for Step model class
"""

import pytest
from src.models.step import Step


def test_valid_step_creation():
    """Test creating a valid step."""
    step = Step(step_type='d', time_length=1000)
    assert step.step_type == 'd'
    assert step.time_length == 1000
    assert step.motor_position is None


def test_valid_step_with_motor():
    """Test creating a valid step with motor position."""
    step = Step(step_type='b', time_length=2000, motor_position=100)
    assert step.step_type == 'b'
    assert step.time_length == 2000
    assert step.motor_position == 100


def test_invalid_step_type():
    """Test that invalid step types raise ValueError."""
    with pytest.raises(ValueError, match="Invalid step type"):
        Step(step_type='x', time_length=1000)


def test_invalid_time_length():
    """Test that invalid time lengths raise ValueError."""
    with pytest.raises(ValueError, match="Time length must be positive"):
        Step(step_type='d', time_length=0)

    with pytest.raises(ValueError, match="Time length must be positive"):
        Step(step_type='d', time_length=-1000)


def test_invalid_motor_position():
    """Test that invalid motor positions raise ValueError."""
    with pytest.raises(ValueError, match="Motor position must be an integer"):
        Step(step_type='d', time_length=1000, motor_position=3.14)


@pytest.mark.parametrize("step_type", ['d', 'n', 'e', 'b', 's', 'h'])
def test_all_valid_step_types(step_type):
    """Test all valid step types."""
    step = Step(step_type=step_type, time_length=1000)
    assert step.step_type == step_type
