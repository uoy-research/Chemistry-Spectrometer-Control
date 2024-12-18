"""
File: test_valve_macro.py
Description: Unit tests for ValveMacro and MacroManager classes
"""

import pytest
import json
from pathlib import Path
from src.models.valve_macro import ValveMacro, MacroManager


def test_valid_valve_macro():
    """Test creating a valid valve macro."""
    macro = ValveMacro(
        label="Test Macro",
        valve_states=[0, 1, 2, 0, 1, 2, 0, 1],
        timer=1.5
    )
    assert macro.label == "Test Macro"
    assert len(macro.valve_states) == 8
    assert macro.timer == 1.5


def test_invalid_valve_states_length():
    """Test that wrong number of valve states raises ValueError."""
    with pytest.raises(ValueError, match="Must specify exactly 8 valve states"):
        ValveMacro(
            label="Invalid",
            valve_states=[0, 1, 2],  # Too few states
            timer=1.0
        )


def test_invalid_valve_states_values():
    """Test that invalid valve states raise ValueError."""
    with pytest.raises(ValueError, match="Invalid valve states"):
        ValveMacro(
            label="Invalid",
            valve_states=[0, 1, 2, 3, 0, 1, 2, 0],  # 3 is invalid
            timer=1.0
        )


def test_invalid_timer():
    """Test that invalid timer values raise ValueError."""
    with pytest.raises(ValueError, match="Timer must be positive"):
        ValveMacro(
            label="Invalid",
            valve_states=[0] * 8,
            timer=0.0
        )


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_file = tmp_path / "test_macros.json"
    return config_file


@pytest.fixture
def macro_manager(temp_config_file):
    """Create a MacroManager instance with temporary config."""
    return MacroManager(temp_config_file)


def test_create_default_macros(macro_manager):
    """Test creation of default macros."""
    macro_manager._create_default_macros()
    assert len(macro_manager.macros) == 4
    assert "1" in macro_manager.macros
    assert macro_manager.macros["1"].label == "Macro 1"


def test_save_and_load_macros(macro_manager, temp_config_file):
    """Test saving and loading macros."""
    # Create and save test macro
    test_macro = ValveMacro(
        label="Test Macro",
        valve_states=[0, 1, 2, 0, 1, 2, 0, 1],
        timer=1.5
    )
    macro_manager.macros["test"] = test_macro
    macro_manager.save_macros()

    # Create new manager and load macros
    new_manager = MacroManager(temp_config_file)
    new_manager.load_macros()

    # Verify loaded macro matches original
    loaded_macro = new_manager.macros["test"]
    assert loaded_macro.label == test_macro.label
    assert loaded_macro.valve_states == test_macro.valve_states
    assert loaded_macro.timer == test_macro.timer


def test_get_nonexistent_macro(macro_manager):
    """Test that getting nonexistent macro raises KeyError."""
    with pytest.raises(KeyError, match="Macro not found"):
        macro_manager.get_macro("nonexistent")


def test_invalid_config_file(temp_config_file):
    """Test handling of invalid config file."""
    # Write invalid JSON
    temp_config_file.write_text("invalid json")

    manager = MacroManager(temp_config_file)
    with pytest.raises(ValueError, match="Invalid macro configuration file"):
        manager.load_macros()
