"""
File: macro_editor.py
Description: Dialog for editing valve macros
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox,
    QComboBox, QMessageBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
import logging
from typing import List, Dict, Optional

from models.valve_macro import MacroManager, ValveMacro


class MacroEditor(QDialog):
    """
    Dialog for editing valve macros.

    Attributes:
        macro_manager: Manager for valve macros
        current_macro: Currently selected macro
    """

    def __init__(self, macro_manager: MacroManager, parent=None):
        """Initialize macro editor."""
        super().__init__(parent)

        self.macro_manager = macro_manager
        self.current_macro: Optional[str] = None
        self.logger = logging.getLogger(__name__)

        self.setup_ui()
        self.load_macros()

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("Macro Editor")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Create macro selection group
        selection_group = QGroupBox("Macro Selection")
        selection_layout = QHBoxLayout(selection_group)

        self.macro_combo = QComboBox()
        self.macro_combo.currentIndexChanged.connect(self.load_macro)

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self.create_macro)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_macro)

        selection_layout.addWidget(QLabel("Macro:"))
        selection_layout.addWidget(self.macro_combo, 1)
        selection_layout.addWidget(self.new_btn)
        selection_layout.addWidget(self.delete_btn)

        # Create macro properties group
        properties_group = QGroupBox("Macro Properties")
        properties_layout = QGridLayout(properties_group)

        self.label_edit = QLineEdit()
        self.timer_spin = QSpinBox()
        self.timer_spin.setRange(0, 10000)
        self.timer_spin.setSuffix(" ms")

        properties_layout.addWidget(QLabel("Label:"), 0, 0)
        properties_layout.addWidget(self.label_edit, 0, 1)
        properties_layout.addWidget(QLabel("Timer:"), 1, 0)
        properties_layout.addWidget(self.timer_spin, 1, 1)

        # Create valve states group
        valves_group = QGroupBox("Valve States")
        valves_layout = QVBoxLayout(valves_group)

        # Create valve state table
        self.valve_table = QTableWidget(1, 8)
        self.valve_table.setHorizontalHeaderLabels(
            [f"V{i+1}" for i in range(8)])
        self.valve_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # Create valve state combo delegate
        for col in range(8):
            combo = QComboBox()
            combo.addItems(["Closed", "Open", "Unchanged"])
            self.valve_table.setCellWidget(0, col, combo)

        valves_layout.addWidget(self.valve_table)

        # Create quick set buttons
        quick_layout = QHBoxLayout()

        self.all_closed_btn = QPushButton("All Closed")
        self.all_closed_btn.clicked.connect(lambda: self.quick_set(0))

        self.all_open_btn = QPushButton("All Open")
        self.all_open_btn.clicked.connect(lambda: self.quick_set(1))

        self.all_unchanged_btn = QPushButton("All Unchanged")
        self.all_unchanged_btn.clicked.connect(lambda: self.quick_set(2))

        quick_layout.addWidget(self.all_closed_btn)
        quick_layout.addWidget(self.all_open_btn)
        quick_layout.addWidget(self.all_unchanged_btn)

        valves_layout.addLayout(quick_layout)

        # Create button box
        button_layout = QHBoxLayout()

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_changes)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_changes)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        # Add all groups to main layout
        layout.addWidget(selection_group)
        layout.addWidget(properties_group)
        layout.addWidget(valves_group)
        layout.addLayout(button_layout)

    def load_macros(self):
        """Load macros into combo box."""
        try:
            self.macro_combo.clear()

            for key, macro in self.macro_manager.macros.items():
                self.macro_combo.addItem(macro.label, key)

            if self.macro_combo.count() > 0:
                self.current_macro = self.macro_combo.currentData()

        except Exception as e:
            self.logger.error(f"Error loading macros: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load macros: {e}")

    def load_macro(self):
        """Load selected macro into editor."""
        try:
            key = self.macro_combo.currentData()
            if not key:
                return

            macro = self.macro_manager.get_macro(key)

            # Update properties
            self.label_edit.setText(macro.label)
            self.timer_spin.setValue(int(macro.timer * 1000))  # Convert to ms

            # Update valve states
            for col, state in enumerate(macro.valve_states):
                combo = self.valve_table.cellWidget(0, col)
                combo.setCurrentIndex(state)

            self.current_macro = key

        except Exception as e:
            self.logger.error(f"Error loading macro: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load macro: {e}")

    def get_valve_states(self) -> List[int]:
        """Get current valve states from table."""
        states = []
        for col in range(8):
            combo = self.valve_table.cellWidget(0, col)
            states.append(combo.currentIndex())
        return states

    def create_macro(self):
        """Create new macro."""
        try:
            # Find next available key
            existing_keys = set(self.macro_manager.macros.keys())
            key = "1"
            counter = 1
            while key in existing_keys:
                counter += 1
                key = str(counter)

            # Create new macro
            macro = ValveMacro(
                label=f"New Macro {counter}",
                valve_states=[2] * 8,  # All unchanged
                timer=1.0
            )

            # Add to manager
            self.macro_manager.macros[key] = macro

            # Update UI
            self.macro_combo.addItem(macro.label, key)
            self.macro_combo.setCurrentIndex(self.macro_combo.count() - 1)

        except Exception as e:
            self.logger.error(f"Error creating macro: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create macro: {e}")

    def delete_macro(self):
        """Delete current macro."""
        try:
            if not self.current_macro:
                return

            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                "Are you sure you want to delete this macro?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Remove from manager
                del self.macro_manager.macros[self.current_macro]

                # Update UI
                self.macro_combo.removeItem(self.macro_combo.currentIndex())

        except Exception as e:
            self.logger.error(f"Error deleting macro: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete macro: {e}")

    def quick_set(self, state: int):
        """Set all valve states to specified value."""
        try:
            for col in range(8):
                combo = self.valve_table.cellWidget(0, col)
                combo.setCurrentIndex(state)

        except Exception as e:
            self.logger.error(f"Error setting valve states: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to set valve states: {e}")

    def apply_changes(self):
        """Apply changes to current macro."""
        try:
            if not self.current_macro:
                return

            # Create updated macro
            macro = ValveMacro(
                label=self.label_edit.text(),
                valve_states=self.get_valve_states(),
                timer=self.timer_spin.value() / 1000.0  # Convert from ms
            )

            # Update manager
            self.macro_manager.macros[self.current_macro] = macro

            # Update combo box text
            index = self.macro_combo.currentIndex()
            self.macro_combo.setItemText(index, macro.label)

            self.logger.info(f"Applied changes to macro: {macro.label}")

        except Exception as e:
            self.logger.error(f"Error applying changes: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to apply changes: {e}")

    def save_changes(self):
        """Save changes and close dialog."""
        try:
            # Apply current changes
            self.apply_changes()

            # Save to file
            self.macro_manager.save_macros()

            self.logger.info("Saved all macro changes")
            self.accept()

        except Exception as e:
            self.logger.error(f"Error saving changes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")
