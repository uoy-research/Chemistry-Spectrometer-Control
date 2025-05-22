from PyQt6 import QtWidgets, QtCore
from utils.config_manager import ConfigManager


class ValveMacroEditor(QtWidgets.QDialog):
    # Add signal for macro updates
    macro_updated = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = ConfigManager()

        self.setWindowTitle("Valve Macro Editor")
        self.setGeometry(100, 100, 700, 190)
        self.setFixedSize(673, 170)

        # Create a table widget
        self.table = QtWidgets.QTableWidget(self)
        self.table.setRowCount(4)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["Macro No.", "Label", "V1", "V2", "V3", "V4", "V5", "V6", "Timer (s)"])

        # Set layout
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addWidget(self.table)
        self.setLayout(self.mainLayout)

        # Load data from config
        self.load_data()

        # Resize columns
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 120)  # Label column
        self.table.setColumnWidth(8, 80)   # Timer column

    def load_data(self):
        try:
            valve_macros = self.config_manager.valve_macros
            for i in range(4):
                macro_num = str(i + 1)
                macro_data = valve_macros.get(macro_num, {
                    "Label": f"Valve Macro {i+1}",
                    "Valves": [0] * 8,
                    "Timer": 1.0
                })
                
                # Macro No.
                item = QtWidgets.QTableWidgetItem(f"Macro {i+1}")
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, 0, item)
                
                # Label
                label_text = macro_data.get("Label", f"Valve Macro {i+1}")
                label_item = QtWidgets.QTableWidgetItem(label_text)
                self.table.setItem(i, 1, label_item)
                
                # Valve States
                for j, state in enumerate(macro_data["Valves"][:6], start=2):
                    combo = QtWidgets.QComboBox()
                    combo.addItems(["Open", "Closed", "Ignore"])
                    if state == 1:
                        combo.setCurrentText("Open")
                    elif state == 0:
                        combo.setCurrentText("Closed")
                    else:
                        combo.setCurrentText("Ignore")
                    self.table.setCellWidget(i, j, combo)
                
                # Timer SpinBox
                timer_spinbox = QtWidgets.QDoubleSpinBox()
                timer_spinbox.setRange(0.1, 3600)
                timer_spinbox.setSingleStep(0.1)
                timer_val = macro_data.get("Timer", 1.0)
                timer_spinbox.setValue(timer_val)
                self.table.setCellWidget(i, 8, timer_spinbox)
        except Exception:
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
            for j in range(2, 8):
                combo = QtWidgets.QComboBox()
                combo.addItems(["Open", "Closed", "Ignore"])
                combo.setCurrentIndex(1)  # Default to "Closed"
                self.table.setCellWidget(i, j, combo)
            # Timer SpinBox
            timer_spinbox = QtWidgets.QDoubleSpinBox()
            timer_spinbox.setRange(0.1, 3600)
            timer_spinbox.setSingleStep(0.1)
            timer_spinbox.setValue(1.0)
            self.table.setCellWidget(i, 8, timer_spinbox)

    def get_macro_data(self):
        data = []
        for row in range(self.table.rowCount()):
            macro_number = self.table.item(row, 0).text()
            label_text = self.table.item(row, 1).text()
            valve_states = []
            for col in range(2, 8):
                state = self.table.cellWidget(row, col).currentText()
                if state == "Open":
                    valve_states.append(1)
                elif state == "Closed":
                    valve_states.append(0)
                else:  # "Ignore"
                    valve_states.append(2)
            valve_states.extend([0, 0])  # Add states for valves 7-8
            timer_spinbox = self.table.cellWidget(row, 8)
            timer_value = timer_spinbox.value() if timer_spinbox else 1.0
            data.append({
                "Label": label_text,
                "Valves": valve_states,
                "Timer": timer_value
            })
        return data

    def closeEvent(self, event):
        # Update macros in config manager
        for i, macro in enumerate(self.get_macro_data()):
            # Macro numbers are 1-based
            self.config_manager.update_valve_macro(i+1, macro)

        # Emit signal that macros were updated BEFORE closing
        self.macro_updated.emit()

        # Call parent's closeEvent last
        super().closeEvent(event)
