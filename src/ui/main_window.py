"""
File: main_window.py
Description: Main application window implementation
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QGroupBox, QMenuBar,
    QStatusBar, QMessageBox, QButtonGroup, QRadioButton, QFrame,
    QStackedWidget, QCheckBox, QLineEdit, QDoubleSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize, QRect
from PyQt6.QtGui import QFont
import logging
from typing import List, Optional
from pathlib import Path

from utils.config import Config
from workers.arduino_worker import ArduinoWorker
from workers.motor_worker import MotorWorker
from models.valve_macro import MacroManager
from .widgets.plot_widget import PlotWidget
from .widgets.log_widget import LogWidget
from .dialogs.macro_editor import MacroEditor


class MainWindow(QMainWindow):
    """
    Main application window.

    Attributes:
        arduino_worker: Worker thread for Arduino communication
        motor_worker: Worker thread for motor control
        plot_widget: Widget for real-time plotting
        log_widget: Widget for logging
    """

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Load configuration
        self.config = Config()

        # Initialize macro manager with config path
        macro_path = Path(self.config.macro_file)
        self.macro_manager = MacroManager(macro_path)

        # Initialize workers
        self.arduino_worker = ArduinoWorker(
            port=f"COM{self.config.arduino_port}")
        self.motor_worker = MotorWorker(port=f"COM{self.config.motor_port}")

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Setup UI
        self.setup_ui()
        self.setup_connections()

        self.logger.info("Application started")

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("SSBubble Control")
        self.setFixedSize(1050, 690)

        # Remove group box borders with stylesheet
        self.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 0px;
                padding-top: 0px;
            }
                    QPushButton:disabled {
            background-color: grey;
            color: white;
            }
            QLineEdit:disabled {
                background-color: grey;
                color: black;
            }
            QSpinBox:disabled {
                background-color: grey;
                color: black;
            }
            """)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create containers for top and bottom sections
        top_container = QWidget()
        bottom_container = QWidget()
        top_layout = QGridLayout(top_container)
        bottom_layout = QGridLayout(bottom_container)

        # Create top section (y < 300)
        self.setup_arduino_section(top_layout)
        self.setup_feedback_section(top_layout)
        self.setup_motor_section(top_layout)
        self.setup_motor_position_section(top_layout)
        self.setup_motor_macro_section(top_layout)

        # Create bottom section (y > 300)
        self.divider(bottom_layout)
        self.setup_valve_section(bottom_layout)
        self.setup_graph_section(bottom_layout)
        self.setup_monitor_section(bottom_layout)

        # Add containers to main layout
        main_layout.addWidget(top_container)
        main_layout.addWidget(bottom_container)

        # Create menu and status bars
        self.setup_menu_bar()
        self.setup_status_bar()

    def setup_arduino_section(self, layout):
        """Setup Arduino connection controls."""
        arduino_group = QGroupBox()
        arduino_group.setFixedSize(181, 291)
        arduino_group.move(10, 0)
        arduino_layout = QVBoxLayout(arduino_group)
        arduino_layout.setContentsMargins(0, 0, 10, 0)

        self.arduino_port_label = QLabel("Arduino Port:")
        font = QFont()
        font.setPointSize(15)
        self.arduino_port_label.setFont(font)
        self.arduino_port_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.arduino_port_spin = QSpinBox()
        self.arduino_port_spin.setMinimumSize(QSize(0, 24))
        font = QFont()
        font.setPointSize(11)
        self.arduino_port_spin.setFont(font)
        self.arduino_port_spin.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        self.arduino_port_spin.setRange(1, 255)
        self.arduino_port_spin.setValue(self.config.arduino_port)
        self.arduino_port_spin.valueChanged.connect(self.update_arduino_port)

        self.arduino_warning_label = QLabel("Warning: Arduino not connected")
        self.arduino_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arduino_warning_label.setStyleSheet("color: red;")

        # Create radio buttons for connection type
        self.arduino_auto_connect_radio = QRadioButton("Auto Connect")
        self.arduino_auto_connect_radio.setChecked(True)
        self.arduino_ttl_radio = QRadioButton("TTL")
        self.arduino_ttl_radio.setChecked(False)
        self.arduino_manual_radio = QRadioButton("Manual")
        self.arduino_manual_radio.setChecked(False)

        # Set font size to 14
        font = QFont()
        font.setPointSize(14)
        self.arduino_auto_connect_radio.setFont(font)
        self.arduino_ttl_radio.setFont(font)
        self.arduino_manual_radio.setFont(font)

        # Create button group for radio buttons
        self.arduino_connect_button_group = QButtonGroup(self)
        self.arduino_connect_button_group.addButton(
            self.arduino_auto_connect_radio)
        self.arduino_connect_button_group.addButton(self.arduino_ttl_radio)
        self.arduino_connect_button_group.addButton(self.arduino_manual_radio)

        self.arduino_connect_button = QPushButton("Connect")
        self.arduino_connect_button.setMinimumSize(QSize(0, 70))
        font = QFont()
        font.setPointSize(18)
        self.arduino_connect_button.setFont(font)
        self.arduino_connect_button.setObjectName("ardConnectButton")
        self.arduino_connect_button.clicked.connect(
            self.handle_arduino_connection)

        arduino_layout.addWidget(self.arduino_port_label)
        arduino_layout.addWidget(self.arduino_port_spin)
        arduino_layout.addWidget(self.arduino_warning_label)
        arduino_layout.addWidget(self.arduino_auto_connect_radio)
        arduino_layout.addWidget(self.arduino_ttl_radio)
        arduino_layout.addWidget(self.arduino_manual_radio)
        arduino_layout.addWidget(self.arduino_connect_button)
        layout.addWidget(arduino_group, 0, 0, 2, 1)

    def setup_feedback_section(self, main_layout):
        """Setup feedback section."""
        feedback_container = QWidget()
        feedback_container.setGeometry(QRect(200, 10, 321, 291))
        feedback_container.setFixedSize(321, 291)
        feedback_container.move(200, 10)

        feedback_layout = QVBoxLayout(feedback_container)
        feedback_layout.setContentsMargins(0, 0, 0, 0)

        self.log_widget = LogWidget()
        feedback_layout.addWidget(self.log_widget)

        main_layout.addWidget(feedback_container, 0, 1, 2, 1)

    def divider(self, layout):
        """Setup divider line."""
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(divider, 0, 0, 1, 5)

    def setup_motor_section(self, layout):
        """Setup motor controls."""
        motor_group = QGroupBox()
        motor_group.setFixedSize(201, 291)
        motor_group.move(530, 10)
        motor_layout = QVBoxLayout(motor_group)
        motor_layout.setContentsMargins(0, 0, 0, 0)

        # Create the motor COM port label
        self.motor_com_port_label = QLabel("Motor Port:")
        self.motor_com_port_label.setEnabled(True)
        font = QFont()
        font.setPointSize(15)
        self.motor_com_port_label.setFont(font)
        self.motor_com_port_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motor_layout.addWidget(self.motor_com_port_label)

        # Create the motor COM port spin box
        self.motor_com_port_spin = QSpinBox()
        self.motor_com_port_spin.setMinimumSize(QSize(0, 24))
        font = QFont()
        font.setPointSize(11)
        self.motor_com_port_spin.setFont(font)
        self.motor_com_port_spin.setValue(9)
        self.motor_com_port_spin.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        motor_layout.addWidget(self.motor_com_port_spin)

        # Create the motor warning label
        self.motor_warning_label = QLabel("Warning: Motor not connected")
        font = QFont()
        font.setPointSize(10)
        self.motor_warning_label.setFont(font)
        self.motor_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.motor_warning_label.setStyleSheet("color: red;")
        motor_layout.addWidget(self.motor_warning_label)

        # Create the motor buttons
        self.motor_connect_btn = QPushButton("Connect Motor")
        self.motor_connect_btn.setMinimumSize(QSize(0, 35))
        font = QFont()
        font.setPointSize(12)
        self.motor_connect_btn.setFont(font)
        self.motor_connect_btn.clicked.connect(self.handle_motor_connection)
        motor_layout.addWidget(self.motor_connect_btn)

        self.motor_calibrate_btn = QPushButton("Calibrate")
        self.motor_calibrate_btn.setMinimumSize(QSize(0, 35))
        font = QFont()
        font.setPointSize(12)
        self.motor_calibrate_btn.setFont(font)
        motor_layout.addWidget(self.motor_calibrate_btn)

        self.motor_stop_btn = QPushButton("STOP")
        self.motor_stop_btn.setMinimumSize(QSize(0, 90))
        font = QFont()
        font.setPointSize(20)
        self.motor_stop_btn.setFont(font)
        motor_layout.addWidget(self.motor_stop_btn)

        layout.addWidget(motor_group, 0, 2, 2, 1)

    def setup_valve_section(self, layout):
        """Setup valve controls with switchable views."""
        valve_group = QGroupBox()
        valve_group.setFixedSize(96, 294)
        valve_group.move(10, 320)
        valve_layout = QVBoxLayout(valve_group)
        valve_layout.setContentsMargins(0, 0, 0, 0)

        valve_group.setFixedSize(96, 294)
        valve_group.move(10, 320)

        self.valve_stack = QStackedWidget()

        manual_control = QWidget()
        manual_layout = QGridLayout(manual_control)

        self.dev_checkbox = QCheckBox("Enable\nControls")
        font = QFont()
        font.setPointSize(9)
        self.dev_checkbox.setFont(font)
        self.dev_checkbox.setChecked(False)
        self.dev_checkbox.toggled.connect(self.toggle_valve_controls)
        manual_layout.addWidget(self.dev_checkbox, 0, 0,
                                Qt.AlignmentFlag.AlignHCenter)

        self.valve_buttons = []
        for i in range(5):
            valve_button = QPushButton()
            valve_button.setMinimumSize(QSize(0, 30))
            font = QFont()
            font.setPointSize(10)
            valve_button.setFont(font)
            valve_button.setText(f"Valve {i+1}")
            valve_button.setObjectName(f"Valve{i+1}Button")
            valve_button.setCheckable(True)
            valve_button.setEnabled(False)
            manual_layout.addWidget(valve_button, i + 1, 0, 1, 1)
            setattr(self, f"Valve{i+1}Button", valve_button)
            self.valve_buttons.append(valve_button)

        auto_control = QWidget()
        auto_layout = QGridLayout(auto_control)

        labels_and_edits = [
            ("Current Step Type", "currentStepTypeLabel", "currentStepTypeEdit"),
            ("Current Step Time", "currentStepTimeLabel", "currentStepTimeEdit"),
            ("Steps Remaining", "stepsRemainingLabel", None),
            ("Steps Time Remaining", "stepsTimeRemainingLabel", None)
        ]

        row = 0
        for label_text, label_name, edit_name in labels_and_edits:
            label = QLabel(label_text)
            font = QFont()
            font.setPointSize(10)
            label.setFont(font)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setattr(self, label_name, label)
            auto_layout.addWidget(label, row, 0)

            if edit_name:
                edit = QLineEdit()
                font = QFont()
                font.setPointSize(10)
                edit.setFont(font)
                edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
                edit.setReadOnly(True)
                edit.setMaximumWidth(100)
                setattr(self, edit_name, edit)
                auto_layout.addWidget(edit, row + 1, 0)
                row += 2
            else:
                row += 1

        self.valve_stack.addWidget(manual_control)
        self.valve_stack.addWidget(auto_control)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setMinimumSize(QSize(0, 30))
        self.reset_button.setMaximumSize(QSize(100, 30))
        font = QFont()
        font.setPointSize(10)
        self.reset_button.setFont(font)
        self.reset_button.clicked.connect(self.reset_valves)

        valve_layout.addWidget(self.valve_stack)
        valve_layout.addWidget(self.reset_button)
        layout.addWidget(valve_group, 1, 0)

    def reset_valves(self):
        """Reset all valves to their default state."""
        for button in self.valve_buttons:
            button.setChecked(False)

        self.currentStepTypeEdit.clear()
        self.currentStepTimeEdit.clear()
        self.stepsRemainingLabel.setText("Steps Remaining")
        self.stepsTimeRemainingLabel.setText("Steps Time Remaining")

    def set_valve_mode(self, is_auto: bool):
        """Switch between manual and automated valve control.

        Args:
            is_auto: True for automated mode, False for manual mode
        """
        self.valve_stack.setCurrentIndex(1 if is_auto else 0)

    def setup_graph_section(self, layout):
        """Setup graph display."""
        graph_group = QGroupBox()
        graph_group.setFixedSize(625, 299)
        graph_group.move(119, 323)
        graph_layout = QVBoxLayout(graph_group)
        graph_layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = PlotWidget(
            max_points=self.config.max_data_points,
            update_interval=self.config.update_interval
        )
        graph_layout.addWidget(self.plot_widget)

        layout.addWidget(graph_group, 1, 1)

    def setup_monitor_section(self, layout):
        """Setup monitoring controls."""
        monitor_group = QGroupBox()
        monitor_group.setFixedSize(261, 291)
        monitor_group.move(760, 320)

        monitor_layout = QGridLayout(monitor_group)
        monitor_layout.setContentsMargins(0, 0, 0, 0)

        # Create pressure radio buttons
        for i in range(1, 5):
            radio = QRadioButton(f"Pressure {i}")
            font = QFont()
            font.setPointSize(10)
            radio.setFont(font)
            radio.setAutoExclusive(False)
            radio.setChecked(True)
            setattr(self, f"pressure{i}RadioButton", radio)
            row, col = (i-1) // 2, (i-1) % 2
            monitor_layout.addWidget(
                radio, row, col, 1, 1, Qt.AlignmentFlag.AlignHCenter)

        # Create buttons with consistent font setting
        self.selectSavePathButton = QPushButton("Select Path..")
        self.selectSavePathButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.selectSavePathButton.setFont(font)
        monitor_layout.addWidget(self.selectSavePathButton, 2, 1, 1, 1)

        self.beginSaveButton = QPushButton("Begin Saving")
        self.beginSaveButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.beginSaveButton.setFont(font)
        self.beginSaveButton.setCheckable(True)
        monitor_layout.addWidget(self.beginSaveButton, 2, 0, 1, 1)

        self.savePathEdit = QLineEdit()
        font = QFont()
        font.setPointSize(10)
        self.savePathEdit.setFont(font)
        monitor_layout.addWidget(self.savePathEdit, 3, 0, 1, 2)

        self.bubbleTimeLabel = QLabel("Bubble Time (s)")
        font = QFont()
        font.setPointSize(10)
        self.bubbleTimeLabel.setFont(font)
        self.bubbleTimeLabel.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        monitor_layout.addWidget(self.bubbleTimeLabel, 4, 0, 1, 1)

        self.bubbleTimeDoubleSpinBox = QDoubleSpinBox()
        self.bubbleTimeDoubleSpinBox.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        self.bubbleTimeDoubleSpinBox.setMinimum(0.0)
        self.bubbleTimeDoubleSpinBox.setValue(5.00)
        monitor_layout.addWidget(self.bubbleTimeDoubleSpinBox, 4, 1, 1, 1)

        self.quickBubbleButton = QPushButton("Quick Bubble")
        self.quickBubbleButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.quickBubbleButton.setFont(font)
        self.quickBubbleButton.setCheckable(True)
        monitor_layout.addWidget(self.quickBubbleButton, 5, 0, 1, 2)

        self.switchGasButton = QPushButton("Switch Gas")
        self.switchGasButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.switchGasButton.setFont(font)
        self.switchGasButton.setCheckable(True)
        monitor_layout.addWidget(self.switchGasButton, 6, 0, 1, 1)

        self.buildPressureButton = QPushButton("Build Pressure")
        self.buildPressureButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.buildPressureButton.setFont(font)
        self.buildPressureButton.setCheckable(True)
        monitor_layout.addWidget(self.buildPressureButton, 6, 1, 1, 1)

        for i in range(1, 5):
            btn = QPushButton(f"Valve Macro {i}")
            btn.setMinimumSize(QSize(0, 25))
            btn.setMaximumWidth(125)
            font = QFont()
            font.setPointSize(10)
            btn.setFont(font)
            setattr(self, f"valveMacro{i}Button", btn)
            row = 7 if i <= 2 else 8
            col = (i-1) % 2
            monitor_layout.addWidget(btn, row, col, 1, 1)

        self.quickVentButton = QPushButton("Quick Vent")
        self.quickVentButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.quickVentButton.setFont(font)
        self.quickVentButton.setCheckable(True)
        monitor_layout.addWidget(self.quickVentButton, 9, 0, 1, 1)

        self.slowVentButton = QPushButton("Slow Vent")
        self.slowVentButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.slowVentButton.setFont(font)
        self.slowVentButton.setCheckable(True)
        monitor_layout.addWidget(self.slowVentButton, 9, 1, 1, 1)

        layout.addWidget(monitor_group, 1, 3)

    def setup_motor_position_section(self, layout):
        """Setup motor position controls."""
        position_group = QGroupBox()
        position_group.setFixedSize(281, 121)
        position_group.move(740, 10)
        motor_pos_layout = QGridLayout(position_group)
        motor_pos_layout.setContentsMargins(0, 0, 0, 0)

        # Current Motor Position
        self.cur_motor_pos_label = QLabel("Current Position:")
        font = QFont()
        font.setPointSize(10)
        self.cur_motor_pos_label.setFont(font)
        self.cur_motor_pos_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        motor_pos_layout.addWidget(self.cur_motor_pos_label, 0, 0, 1, 1)

        self.cur_motor_pos_edit = QLineEdit()
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        self.cur_motor_pos_edit.setSizePolicy(size_policy)
        font = QFont()
        font.setPointSize(10)
        self.cur_motor_pos_edit.setFont(font)
        self.cur_motor_pos_edit.setReadOnly(True)
        motor_pos_layout.addWidget(self.cur_motor_pos_edit, 0, 1, 1, 1)

        # Target Motor Position
        self.target_motor_pos_label = QLabel("Target Position:")
        font = QFont()
        font.setPointSize(10)
        self.target_motor_pos_label.setFont(font)
        self.target_motor_pos_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        motor_pos_layout.addWidget(self.target_motor_pos_label, 1, 0, 1, 1)

        self.target_motor_pos_edit = QLineEdit()
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        self.target_motor_pos_edit.setSizePolicy(size_policy)
        font = QFont()
        font.setPointSize(10)
        self.target_motor_pos_edit.setFont(font)
        motor_pos_layout.addWidget(self.target_motor_pos_edit, 1, 1, 1, 1)

        # Move to Target Button
        self.motor_move_to_target_button = QPushButton("Move to Target")
        self.motor_move_to_target_button.setMinimumSize(QSize(0, 40))
        font = QFont()
        font.setPointSize(11)
        self.motor_move_to_target_button.setFont(font)
        motor_pos_layout.addWidget(
            self.motor_move_to_target_button, 2, 0, 1, 2)

        layout.addWidget(position_group, 0, 3)

    def setup_motor_macro_section(self, layout):
        """Setup motor macro controls."""
        macro_group = QGroupBox()
        macro_group.setFixedSize(281, 171)
        macro_group.move(740, 130)
        motor_macro_layout = QGridLayout(macro_group)
        motor_macro_layout.setContentsMargins(0, 0, 0, 0)

        # Create the motor macro buttons
        self.motor_to_top_button = QPushButton("To Top")
        self.motor_to_top_button.setMinimumSize(QSize(0, 35))
        font = QFont()
        font.setPointSize(10)
        self.motor_to_top_button.setFont(font)
        motor_macro_layout.addWidget(self.motor_to_top_button, 0, 0, 1, 1)

        self.motor_ascent_button = QPushButton("Ascent")
        self.motor_ascent_button.setMinimumSize(QSize(0, 35))
        font = QFont()
        font.setPointSize(10)
        self.motor_ascent_button.setFont(font)
        motor_macro_layout.addWidget(self.motor_ascent_button, 0, 1, 1, 1)

        # Create macro buttons 1-6
        for i in range(1, 7):
            btn = QPushButton(f"Macro {i}")
            btn.setMinimumSize(QSize(0, 35))
            btn.setMaximumWidth(135)
            font = QFont()
            font.setPointSize(10)
            btn.setFont(font)
            setattr(self, f"motor_macro{i}_button", btn)
            row = (i + 1) // 2
            col = (i - 1) % 2
            motor_macro_layout.addWidget(btn, row, col, 1, 1)

        layout.addWidget(macro_group, 1, 3)

    def setup_menu_bar(self):
        """Setup application menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        tools_menu = menubar.addMenu("Tools")
        macro_action = tools_menu.addAction("Macro Editor")
        macro_action.triggered.connect(self.edit_macros)

    def setup_status_bar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")

    def setup_connections(self):
        """Setup signal connections."""
        self.arduino_worker.readings_updated.connect(
            self.handle_pressure_readings)
        self.arduino_worker.error_occurred.connect(self.handle_error)
        self.arduino_worker.status_changed.connect(self.handle_status_message)

        self.motor_worker.position_updated.connect(self.handle_position_update)
        self.motor_worker.error_occurred.connect(self.handle_error)
        self.motor_worker.status_changed.connect(self.handle_status_message)

    @pyqtSlot()
    def handle_arduino_connection(self):
        """Handle Arduino connection/disconnection."""
        if not self.arduino_worker.running:
            if self.arduino_worker.start():
                self.arduino_connect_button.setText("Disconnect")
                self.logger.info("Connected to Arduino")
            else:
                self.handle_error("Failed to connect to Arduino")
        else:
            self.arduino_worker.stop()
            self.arduino_connect_button.setText("Connect")
            self.logger.info("Disconnected from Arduino")

    @pyqtSlot()
    def handle_motor_connection(self):
        """Handle motor connection/disconnection."""
        if not self.motor_worker.running:
            if self.motor_worker.start():
                self.motor_connect_btn.setText("Disconnect")
                self.logger.info("Connected to motor")
            else:
                self.handle_error("Failed to connect to motor")
        else:
            self.motor_worker.stop()
            self.motor_connect_btn.setText("Connect")
            self.logger.info("Disconnected from motor")

    @pyqtSlot(list)
    def handle_pressure_readings(self, readings: List[float]):
        """Handle pressure reading updates."""
        self.plot_widget.update_plot(readings)

    @pyqtSlot(int)
    def handle_position_update(self, position: int):
        """Handle motor position updates."""
        self.position_spin.setValue(position)

    @pyqtSlot(str)
    def handle_status_message(self, message: str):
        """Handle status message updates."""
        self.statusBar().showMessage(message)
        self.log_widget.add_message(message)

    @pyqtSlot(str)
    def handle_error(self, message: str):
        """Handle error messages."""
        self.logger.error(message)
        QMessageBox.critical(self, "Error", message)

    def move_motor(self):
        """Move motor to specified position."""
        position = self.position_spin.value()
        self.motor_worker.move_to(position)

    def edit_macros(self):
        """Open macro editor dialog."""
        editor = MacroEditor(self.macro_manager, self)
        editor.exec()

    def emergency_stop(self):
        """Handle emergency stop."""
        self.motor_worker.stop()
        self.arduino_worker.depressurize()
        QMessageBox.warning(self, "Emergency Stop",
                            "Emergency stop activated!")
        self.logger.warning("Emergency stop activated")

    def closeEvent(self, event):
        """Handle application shutdown."""
        try:
            self.arduino_worker.stop()
            self.motor_worker.stop()

            self.config.save()

            self.logger.info("Shutdown complete")
            event.accept()

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            event.accept()

    def update_arduino_port(self, port: int):
        """
        Update Arduino port configuration.

        Args:
            port: New port number
        """
        self.config.arduino_port = port
        self.config.save()

        if self.arduino_worker.running:
            self.arduino_worker.stop()
            self.arduino_connect_button.setText("Connect")
            self.logger.info("Disconnected from Arduino due to port change")

        self.arduino_worker = ArduinoWorker(port=f"COM{port}")
        self.setup_connections()
        self.logger.info(f"Arduino port updated to COM{port}")

    def toggle_valve_controls(self, enabled: bool):
        """Enable or disable valve control buttons based on checkbox state.

        Args:
            enabled (bool): True to enable buttons, False to disable
        """
        for i in range(1, 6):
            valve_button = getattr(self, f"Valve{i}Button")
            if valve_button:
                valve_button.setEnabled(enabled)
                if not enabled:
                    valve_button.setChecked(False)
