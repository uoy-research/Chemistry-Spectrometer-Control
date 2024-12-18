"""
File: test_macro_editor.py
Description: Tests for macro editor dialog
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication, QComboBox
from PyQt6.QtCore import Qt

from src.ui.dialogs.macro_editor import MacroEditor
from src.models.valve_macro import MacroManager, ValveMacro

# Required for Qt tests


@pytest.fixture
def app():
    """Create QApplication instance."""
    return QApplication([])


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file."""
    config_file = tmp_path / "test_macros.json"
    config_file.write_text("{}")
    return config_file


@pytest.fixture
def macro_manager(temp_config_file):
    """Create macro manager with test data."""
    manager = MacroManager(temp_config_file)

    # Add test macros
    manager.macros["1"] = ValveMacro(
        label="Test Macro 1",
        valve_states=[0, 1, 2, 0, 1, 2, 0, 1],
        timer=1.0
    )
    manager.macros["2"] = ValveMacro(
        label="Test Macro 2",
        valve_states=[1, 1, 1, 1, 1, 1, 1, 1],
        timer=2.0
    )

    return manager


@pytest.fixture
def editor(app, macro_manager):
    """Create macro editor instance."""
    return MacroEditor(macro_manager)


def test_initialization(editor, macro_manager):
    """Test editor initialization."""
    assert editor.macro_manager == macro_manager
    assert editor.current_macro is not None
    assert editor.macro_combo.count() == 2


def test_load_macro(editor, macro_manager):
    """Test loading macro into editor."""
    # Select first macro
    editor.macro_combo.setCurrentIndex(0)
    macro = macro_manager.macros["1"]

    # Verify properties loaded
    assert editor.label_edit.text() == macro.label
    assert editor.timer_spin.value() == int(macro.timer * 1000)

    # Verify valve states
    for col, state in enumerate(macro.valve_states):
        combo = editor.valve_table.cellWidget(0, col)
        assert combo.currentIndex() == state


def test_create_macro(editor):
    """Test creating new macro."""
    initial_count = editor.macro_combo.count()

    # Create new macro
    editor.create_macro()

    # Verify macro added
    assert editor.macro_combo.count() == initial_count + 1
    assert "New Macro" in editor.macro_combo.currentText()


def test_delete_macro(editor, monkeypatch):
    """Test deleting macro."""
    initial_count = editor.macro_combo.count()

    # Mock QMessageBox.question to return Yes
    monkeypatch.setattr('PyQt6.QtWidgets.QMessageBox.question',
                        lambda *args: Qt.StandardButton.Yes)

    # Delete current macro
    editor.delete_macro()

    # Verify macro removed
    assert editor.macro_combo.count() == initial_count - 1


def test_quick_set(editor):
    """Test quick set buttons."""
    # Test setting all closed
    editor.quick_set(0)
    states = editor.get_valve_states()
    assert all(state == 0 for state in states)

    # Test setting all open
    editor.quick_set(1)
    states = editor.get_valve_states()
    assert all(state == 1 for state in states)

    # Test setting all unchanged
    editor.quick_set(2)
    states = editor.get_valve_states()
    assert all(state == 2 for state in states)


def test_apply_changes(editor):
    """Test applying changes to macro."""
    # Make changes
    new_label = "Updated Macro"
    new_timer = 2000  # 2 seconds in ms
    editor.label_edit.setText(new_label)
    editor.timer_spin.setValue(new_timer)
    editor.quick_set(1)  # Set all valves open

    # Apply changes
    editor.apply_changes()

    # Verify changes in manager
    macro = editor.macro_manager.macros[editor.current_macro]
    assert macro.label == new_label
    assert macro.timer == new_timer / 1000.0
    assert all(state == 1 for state in macro.valve_states)


def test_save_changes(editor, macro_manager):
    """Test saving changes to file."""
    # Make changes
    editor.label_edit.setText("Saved Macro")
    editor.timer_spin.setValue(3000)

    # Save changes
    with patch.object(macro_manager, 'save_macros') as mock_save:
        editor.save_changes()
        mock_save.assert_called_once()


def test_valve_state_editing(editor):
    """Test editing individual valve states."""
    # Change each valve state
    test_states = [0, 1, 2, 0, 1, 2, 0, 1]
    for col, state in enumerate(test_states):
        combo = editor.valve_table.cellWidget(0, col)
        combo.setCurrentIndex(state)

    # Verify states
    states = editor.get_valve_states()
    assert states == test_states


def test_error_handling(editor, caplog):
    """Test error handling."""
    # Test invalid macro operation
    with patch.object(editor.macro_manager, 'save_macros',
                      side_effect=Exception("Test error")):
        editor.save_changes()
        assert "Error saving changes" in caplog.text


def test_cancel_operation(editor, macro_manager):
    """Test canceling changes."""
    # Store original macro state
    original_macro = macro_manager.macros["1"]
    original_label = original_macro.label

    # Make changes
    editor.label_edit.setText("Changed Label")

    # Cancel changes
    editor.reject()

    # Verify no changes saved
    assert macro_manager.macros["1"].label == original_label


@pytest.mark.parametrize("timer_value", [
    0,      # Minimum
    5000,   # Middle
    10000,  # Maximum
])
def test_timer_range(editor, timer_value):
    """Test timer value range."""
    editor.timer_spin.setValue(timer_value)
    editor.apply_changes()

    macro = editor.macro_manager.macros[editor.current_macro]
    assert macro.timer == timer_value / 1000.0


def test_duplicate_macro(editor):
    """Test handling duplicate macro creation."""
    # Create initial macro
    editor.create_macro()
    initial_count = editor.macro_combo.count()

    # Create another macro
    editor.create_macro()

    # Verify unique naming
    assert editor.macro_combo.count() == initial_count + 1
    assert editor.macro_combo.currentText() != editor.macro_combo.itemText(0)


def test_ui_state_consistency(editor):
    """Test UI state consistency after operations."""
    # Test after creation
    editor.create_macro()
    assert editor.apply_btn.isEnabled()
    assert editor.save_btn.isEnabled()

    # Test after deletion
    with patch('PyQt6.QtWidgets.QMessageBox.question',
               return_value=Qt.StandardButton.Yes):
        editor.delete_macro()
        if editor.macro_combo.count() == 0:
            assert not editor.delete_btn.isEnabled()
