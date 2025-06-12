from PyQt6 import QtWidgets, QtCore
from utils.config_manager import ConfigManager


class MotorMacroEditor(QtWidgets.QDialog):
    # Add signal for macro updates
    macro_updated = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = ConfigManager()

        self.setWindowTitle("Motor Macro Editor")
        self.setGeometry(100, 100, 390, 230)
        self.setFixedSize(390, 230)

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

        # Load data from config
        self.load_data()

        # Resize all columns to fit
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 180)  # Label column
        self.table.setColumnWidth(2, 100)  # Position column

    def load_data(self):
        try:
            motor_macros = self.config_manager.motor_macros
            for i in range(6):
                macro_num = str(i + 1)
                macro_data = motor_macros.get(macro_num, {
                    "Label": f"Motor Macro {i+1}",
                    "Position": 0.0
                })
                
                # Macro No.
                item = QtWidgets.QTableWidgetItem(f"Macro {i+1}")
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, 0, item)
                
                # Label
                label_text = macro_data.get("Label", f"Motor Macro {i+1}")
                label_item = QtWidgets.QTableWidgetItem(label_text)
                self.table.setItem(i, 1, label_item)
                
                # Position DoubleSpinBox
                position_spinbox = QtWidgets.QDoubleSpinBox()
                position_spinbox.setRange(0.0, 324.05)
                position_spinbox.setDecimals(2)  # Set to 2 decimal places
                position_spinbox.setSingleStep(0.01)  # Step by 0.01
                position_val = float(macro_data.get("Position", 0.0))
                position_spinbox.setValue(position_val)
                self.table.setCellWidget(i, 2, position_spinbox)
        except Exception as e:
            self.parent.logger.error(f"Error loading motor macros: {e}")
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
            # Position DoubleSpinBox
            position_spinbox = QtWidgets.QDoubleSpinBox()
            position_spinbox.setRange(0.0, 324.05)
            position_spinbox.setDecimals(2)  # Set to 2 decimal places
            position_spinbox.setSingleStep(0.01)  # Step by 0.01
            position_spinbox.setValue(0.0)
            self.table.setCellWidget(i, 2, position_spinbox)

    def get_macro_data(self):
        data = []
        for row in range(self.table.rowCount()):
            label_text = self.table.item(row, 1).text()
            position_spinbox = self.table.cellWidget(row, 2)
            position_value = float(position_spinbox.value()) if position_spinbox else 0.0
            data.append({
                "Label": label_text,
                "Position": position_value
            })
        return data

    def closeEvent(self, event):
        try:
            # Update macros in config manager
            for i, macro in enumerate(self.get_macro_data()):
                # Macro numbers are 1-based
                self.config_manager.update_motor_macro(i+1, macro)

            # Reload the config to ensure changes are reflected
            self.config_manager.reload_config()

            # Emit signal that macros were updated BEFORE closing
            self.macro_updated.emit()
        except Exception as e:
            self.parent.logger.error(f"Error saving motor macros: {e}")

        # Call parent's closeEvent last
        super().closeEvent(event)
