from PyQt6 import QtWidgets, QtCore
import json
import os
from pathlib import Path


class MotorMacroEditor(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setWindowTitle("Motor Macro Editor")
        self.setGeometry(100, 100, 300, 230)
        self.setFixedSize(300, 230)

        # Create a table widget
        self.table = QtWidgets.QTableWidget(self)
        self.table.setRowCount(6)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            ["Macro No.", "Label", "Position"])

        # Set layout
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addWidget(self.table)
        self.setLayout(self.mainLayout)

        # Load data from JSON file if it exists
        self.load_data()

        # Resize all columns to fit
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 130)  # Label column

    def load_data(self):
        json_path = Path("C:/ssbubble/motor_macro_data.json")
        if json_path.exists():
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                for i, macro in enumerate(data):
                    # Macro No.
                    item = QtWidgets.QTableWidgetItem(macro["Macro No."])
                    item.setFlags(item.flags() & ~
                                  QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, 0, item)
                    # Label
                    label_text = macro.get("Label", "")
                    label_item = QtWidgets.QTableWidgetItem(label_text)
                    self.table.setItem(i, 1, label_item)
                    # Position SpinBox
                    position_spinbox = QtWidgets.QSpinBox()
                    position_spinbox.setRange(0, 2500000)
                    position_val = macro.get("Position", 0)
                    position_spinbox.setValue(position_val)
                    self.table.setCellWidget(i, 2, position_spinbox)
            except Exception:
                self.set_default_values()
        else:
            self.set_default_values()

    def set_default_values(self):
        for i in range(6):
            # Macro No.
            item = QtWidgets.QTableWidgetItem(f"Macro {i+1}")
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, item)
            # Label
            label_item = QtWidgets.QTableWidgetItem(f"Motor Macro {i+1}")
            self.table.setItem(i, 1, label_item)
            # Position SpinBox
            position_spinbox = QtWidgets.QSpinBox()
            position_spinbox.setRange(0, 2500000)
            position_spinbox.setValue(0)
            self.table.setCellWidget(i, 2, position_spinbox)

    def get_macro_data(self):
        data = []
        for row in range(self.table.rowCount()):
            macro_number = self.table.item(row, 0).text()
            label_text = self.table.item(row, 1).text()
            position_spinbox = self.table.cellWidget(row, 2)
            position_value = position_spinbox.value() if position_spinbox else 0
            data.append({
                "Macro No.": macro_number,
                "Label": label_text,
                "Position": position_value
            })
        return data

    def closeEvent(self, event):
        # Save data to JSON
        data = self.get_macro_data()
        json_path = Path("C:/ssbubble/motor_macro_data.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Update the main window's buttons with the new labels
        for i in range(6):
            macro_data = data[i]
            button = getattr(self.parent, f'motor_macro{i+1}_button')
            button.setText(macro_data['Label'])

        super().closeEvent(event)
