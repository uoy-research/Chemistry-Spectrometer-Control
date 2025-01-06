from PyQt6 import QtWidgets, QtCore
import json
from pathlib import Path


class ValveMacroEditor(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setWindowTitle("Valve Macro Editor")
        self.setGeometry(100, 100, 650, 190)
        self.setFixedSize(623, 170)

        # Create a table widget
        self.table = QtWidgets.QTableWidget(self)
        self.table.setRowCount(4)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Macro No.", "Label", "V1", "V2", "V3", "V4", "V5", "Timer (s)"])

        # Set layout
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addWidget(self.table)
        self.setLayout(self.mainLayout)

        # Load data from JSON file if it exists
        self.load_data()

        # Resize columns
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 120)  # Label column
        self.table.setColumnWidth(7, 80)   # Timer column

    def load_data(self):
        json_path = Path("C:/ssbubble/valve_macro_data.json")
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
                    # Valve States
                    for j, state in enumerate(macro["Valves"][:5], start=2):
                        combo = QtWidgets.QComboBox()
                        combo.addItems(["Open", "Closed", "Ignore"])
                        combo.setCurrentText(state)
                        self.table.setCellWidget(i, j, combo)
                    # Timer SpinBox
                    timer_spinbox = QtWidgets.QDoubleSpinBox()
                    timer_spinbox.setRange(0.1, 3600)
                    timer_spinbox.setSingleStep(0.1)
                    timer_val = macro.get("Timer", 1.0)
                    timer_spinbox.setValue(timer_val)
                    self.table.setCellWidget(i, 7, timer_spinbox)
            except Exception:
                self.set_default_values()
        else:
            self.set_default_values()

    def set_default_values(self):
        for i in range(4):
            # Macro No.
            item = QtWidgets.QTableWidgetItem(f"Macro {i+1}")
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, item)
            # Label
            label_item = QtWidgets.QTableWidgetItem(f"Valve Macro {i+1}")
            self.table.setItem(i, 1, label_item)
            # Valve States
            for j in range(2, 7):
                combo = QtWidgets.QComboBox()
                combo.addItems(["Open", "Closed", "Ignore"])
                combo.setCurrentIndex(1)  # Default to "Closed"
                self.table.setCellWidget(i, j, combo)
            # Timer SpinBox
            timer_spinbox = QtWidgets.QDoubleSpinBox()
            timer_spinbox.setRange(0.1, 3600)
            timer_spinbox.setSingleStep(0.1)
            timer_spinbox.setValue(1.0)
            self.table.setCellWidget(i, 7, timer_spinbox)

    def get_macro_data(self):
        data = []
        for row in range(self.table.rowCount()):
            macro_number = self.table.item(row, 0).text()
            label_text = self.table.item(row, 1).text()
            valve_states = [self.table.cellWidget(row, col).currentText()
                            for col in range(2, 7)]
            valve_states.extend(["Closed", "Closed", "Closed"])
            timer_spinbox = self.table.cellWidget(row, 7)
            timer_value = timer_spinbox.value() if timer_spinbox else 1.0
            data.append({
                "Macro No.": macro_number,
                "Label": label_text,
                "Valves": valve_states,
                "Timer": timer_value
            })
        return data

    def closeEvent(self, event):
        # Save data to JSON
        data = self.get_macro_data()
        json_path = Path("C:/ssbubble/valve_macro_data.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Update the main window's buttons with the new labels
        for i in range(4):
            macro_data = data[i]
            button = getattr(self.parent, f'valveMacro{i+1}Button')
            button.setText(macro_data['Label'])

        super().closeEvent(event)
