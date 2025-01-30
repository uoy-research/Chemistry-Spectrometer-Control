"""
File: main_window.py
Description: Main application window implementation
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QGroupBox, QMenuBar,
    QStatusBar, QMessageBox, QButtonGroup, QRadioButton, QFrame,
    QStackedWidget, QCheckBox, QLineEdit, QDoubleSpinBox, QSizePolicy,
    QFileDialog, QFormLayout, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize, QRect, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QAction  # Moved QAction to QtGui import
import logging
from typing import List, Optional, Union
from pathlib import Path
import time
import json
import os
import csv

from utils.config import Config
from workers.arduino_worker import ArduinoWorker
from workers.motor_worker import MotorWorker
from .widgets.plot_widget import PlotWidget
from .widgets.log_widget import LogWidget
from .dialogs.valve_macro_editor import ValveMacroEditor
from .dialogs.motor_macro_editor import MotorMacroEditor


class Step:
    """Class representing a sequence step."""

    def __init__(self, step_type: str, time_length: int, motor_position: int = 0):
        self.step_type = step_type
        self.time_length = time_length
        self.motor_position = motor_position


class MainWindow(QMainWindow):
    """
    Main application window.

    Attributes:
        arduino_worker: Worker thread for Arduino communication
        motor_worker: Worker thread for motor control
        plot_widget: Widget for real-time plotting
        log_widget: Widget for logging
    """

    step_types = {
        'd': 'Delay',
        'p': 'Pressurize',
        'v': 'Vent',
        'b': 'Bubble',
        'f': 'Flow',
        'e': 'Evacuate'
    }

    def __init__(self, test_mode: bool = False):
        """Initialize main window.

        Args:
            test_mode: Use mock controllers for testing
        """
        super().__init__()

        # Load configuration
        self.config = Config()
        self.test_mode = test_mode

        # Initialize workers with mock controllers in test mode
        self.arduino_worker = ArduinoWorker(
            port=self.config.arduino_port,
            mock=test_mode
        )
        self.motor_worker = MotorWorker(
            port=self.config.motor_port,
            mock=test_mode
        )

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Initialize state variables
        self.position_check_timer = None  # Track the position check timer
        self.motor_calibrated = False  # Track motor calibration state

        # Add connection tracking flag
        self._connections_initialized = False

        # Setup UI
        self.setup_ui()

        # Setup connections
        if not self._connections_initialized:
            self.setup_connections()
            self._connections_initialized = True

        # Initialize control states
        self.initialize_control_states()

        # Initially disable valve controls
        # Also disable the checkbox initially
        self.disable_valve_controls(True)

        self.logger.info("Application started")

        # Add these instance variables after other initializations
        self.steps = []
        self.motor_flag = False
        self.saving = False
        self.default_save_path = r"C:\ssbubble\data"

        # Add this new instance variable to track active macro
        self.active_valve_macro = None
        self.active_macro_timer = None  # Track the active macro timer

    def initialize_control_states(self):
        """Initialize the enabled/disabled states of all controls."""
        # Motor controls
        if hasattr(self, 'motor_calibrate_btn'):
            self.motor_calibrate_btn.setEnabled(False)
        if hasattr(self, 'motor_stop_btn'):
            # Always enabled for emergency
            self.motor_stop_btn.setEnabled(True)
        self.disable_motor_controls(True)  # Disable all other motor controls

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
            QMenuBar {
                margin: 0;
                padding: 0;
            }
            QMainWindow::separator {
                height: 0px;
                margin: 0px;
                padding: 0px;
            }
            """)

        # Create menu and status bars first
        self.setup_menu_bar()
        self.setup_status_bar()

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 0, 10, 10)  # Adjust top margin to 0
        main_layout.setSpacing(0)

        # Create containers for top and bottom sections
        top_container = QWidget()
        bottom_container = QWidget()
        top_layout = QGridLayout(top_container)
        bottom_layout = QGridLayout(bottom_container)
        
        # Set container layout margins
        top_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

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

        # Load macro labels
        self.load_macro_labels()

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

        self.arduino_warning_label = QLabel("")
        self.arduino_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arduino_warning_label.setStyleSheet("color: red;")
        if not self.test_mode:
            self.arduino_warning_label.setText(
                "Warning: Arduino not connected")

        # Create radio buttons for connection type
        self.arduino_auto_connect_radio = QRadioButton("Automatic")
        self.arduino_auto_connect_radio.setChecked(False)
        self.arduino_ttl_radio = QRadioButton("TTL")
        self.arduino_ttl_radio.setChecked(False)
        self.arduino_manual_radio = QRadioButton("Manual")
        self.arduino_manual_radio.setChecked(True)

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

        self.arduino_connect_btn = QPushButton("Connect")
        self.arduino_connect_btn.setMinimumSize(QSize(0, 70))
        font = QFont()
        font.setPointSize(18)
        self.arduino_connect_btn.setFont(font)
        self.arduino_connect_btn.setObjectName("ardConnectButton")

        arduino_layout.addWidget(self.arduino_port_label)
        arduino_layout.addWidget(self.arduino_port_spin)
        arduino_layout.addWidget(self.arduino_warning_label)
        arduino_layout.addWidget(self.arduino_auto_connect_radio)
        arduino_layout.addWidget(self.arduino_ttl_radio)
        arduino_layout.addWidget(self.arduino_manual_radio)
        arduino_layout.addWidget(self.arduino_connect_btn)
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
        self.motor_warning_label = QLabel("")
        font = QFont()
        font.setPointSize(10)
        self.motor_warning_label.setFont(font)
        self.motor_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.motor_warning_label.setStyleSheet("color: red;")
        if not self.test_mode:
            self.motor_warning_label.setText("Warning: Motor not connected")
        motor_layout.addWidget(self.motor_warning_label)

        # Create the motor buttons
        self.motor_connect_btn = QPushButton("Connect Motor")
        self.motor_connect_btn.setMinimumSize(QSize(0, 35))
        font = QFont()
        font.setPointSize(12)
        self.motor_connect_btn.setFont(font)
        motor_layout.addWidget(self.motor_connect_btn)

        self.motor_calibrate_btn = QPushButton("Calibrate")
        self.motor_calibrate_btn.setMinimumSize(QSize(0, 35))
        font = QFont()
        font.setPointSize(12)
        self.motor_calibrate_btn.setFont(font)
        motor_layout.addWidget(self.motor_calibrate_btn)

        # Create prominent STOP button
        self.motor_stop_btn = QPushButton("STOP")
        self.motor_stop_btn.setMinimumSize(QSize(0, 90))  # Make button taller
        font = QFont()
        font.setPointSize(20)  # Larger font
        font.setBold(True)     # Bold text
        self.motor_stop_btn.setFont(font)
        self.motor_stop_btn.setStyleSheet(
            "background-color: red; color: white;")  # Red background
        motor_layout.addWidget(self.motor_stop_btn)

        # Don't set initial states here - they'll be set in initialize_control_states()
        layout.addWidget(motor_group, 0, 2, 2, 1)

    def disable_motor_controls(self, disabled: bool):
        """Enable/disable motor controls based on connection and calibration state."""
        # Motor position controls
        if hasattr(self, 'target_motor_pos_edit'):
            self.target_motor_pos_edit.setEnabled(
                not disabled and self.motor_calibrated)
            self.motor_move_to_target_button.setEnabled(
                not disabled and self.motor_calibrated)

        # Motor macro buttons
        if hasattr(self, 'motor_to_top_button'):
            self.motor_to_top_button.setEnabled(
                not disabled and self.motor_calibrated)
            self.motor_ascent_button.setEnabled(
                not disabled and self.motor_calibrated)

            # Macro buttons 1-6
            for i in range(1, 7):
                btn = getattr(self, f"motor_macro{i}_button", None)
                if btn:
                    btn.setEnabled(not disabled and self.motor_calibrated)

    def setup_valve_section(self, layout):
        """Setup valve controls with switchable views."""
        valve_group = QGroupBox()
        valve_group.setFixedSize(96, 294)  # May need to adjust height to fit extra button
        valve_group.move(10, 320)
        valve_layout = QVBoxLayout(valve_group)
        valve_layout.setContentsMargins(0, 0, 0, 0)

        # Create the valve stack widget
        self.valve_stack = QStackedWidget()

        # Manual control view
        manual_control = QWidget()
        manual_layout = QVBoxLayout(manual_control)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(2)

        # Add enable checkbox to manual view
        self.dev_checkbox = QCheckBox("Enable\nControls")
        font = QFont()
        font.setPointSize(9)
        self.dev_checkbox.setFont(font)
        self.dev_checkbox.setChecked(False)
        self.dev_checkbox.toggled.connect(self.toggle_valve_controls)
        manual_layout.addWidget(
            self.dev_checkbox, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Create valve control buttons
        self.valve_buttons = []
        for i in range(6):  # Changed from 5 to 6
            valve_button = QPushButton(f"Valve {i+1}")
            valve_button.setMinimumSize(QSize(0, 30))
            valve_button.setCheckable(True)
            valve_button.setEnabled(False)
            setattr(self, f"Valve{i+1}Button", valve_button)
            self.valve_buttons.append(valve_button)
            manual_layout.addWidget(valve_button)

        manual_layout.addStretch()  # Add stretch to push buttons to top

        # Auto control view
        auto_control = QWidget()
        auto_layout = QVBoxLayout(auto_control)
        auto_layout.setContentsMargins(5, 5, 5, 5)
        auto_layout.setSpacing(2)

        # Add sequence status label with word wrap
        self.sequence_status_label = QLabel("Status: Waiting for file")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.sequence_status_label.setFont(font)
        self.sequence_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sequence_status_label.setWordWrap(True)  # Enable word wrap
        self.sequence_status_label.setMinimumHeight(
            40)  # Give space for wrapped text
        auto_layout.addWidget(self.sequence_status_label)

        # Create a form layout for sequence info
        form_layout = QFormLayout()
        form_layout.setSpacing(4)

        # Add sequence info controls with descriptions
        labels_and_edits = [
            ("Current Step Type", "currentStepTypeLabel", "currentStepTypeEdit"),
            ("Step Time Left", "currentStepTimeLabel", "currentStepTimeEdit"),
            ("Steps Remaining", "stepsRemainingLabel", "stepsRemainingEdit"),
            ("Total Time Left", "totalTimeLabel", "totalTimeEdit")
        ]

        for label_text, label_name, edit_name in labels_and_edits:
            # Create container for each stat
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(1)

            # Add description label first
            desc_label = QLabel(label_text)
            desc_label.setWordWrap(True)
            font = QFont()
            font.setPointSize(8)
            font.setItalic(True)
            desc_label.setFont(font)
            desc_label.setStyleSheet("color: gray;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(desc_label)

            # Add value display
            value_widget = QWidget()
            value_layout = QHBoxLayout(value_widget)
            value_layout.setContentsMargins(0, 0, 0, 0)

            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setFixedWidth(80)
            edit.setText("--")
            setattr(self, edit_name, edit)

            value_layout.addWidget(edit)
            container_layout.addWidget(value_widget)

            form_layout.addRow(container)

        # Add form layout to auto layout
        auto_layout.addLayout(form_layout)
        auto_layout.addStretch()

        # Add views to stack
        self.valve_stack.addWidget(manual_control)
        self.valve_stack.addWidget(auto_control)

        # Create reset button
        self.reset_button = QPushButton("Reset")
        self.reset_button.setMinimumSize(QSize(0, 30))
        self.reset_button.setMaximumSize(QSize(100, 30))
        font = QFont()
        font.setPointSize(10)
        self.reset_button.setFont(font)
        self.reset_button.clicked.connect(self.reset_valves)

        # Add everything to main layout
        # Give stack widget stretch
        valve_layout.addWidget(self.valve_stack, 1)
        valve_layout.addWidget(self.reset_button)

        layout.addWidget(valve_group, 1, 0)

        # Set initial stack view to manual mode
        self.valve_stack.setCurrentIndex(0)

    def reset_valves(self):
        """Reset all valves to their default state."""
        # Cancel any active timer
        if self.active_macro_timer is not None:
            self.active_macro_timer.stop()
            self.active_macro_timer = None

        # Reset valve buttons
        for button in self.valve_buttons:
            button.setChecked(False)

        # Reset sequence info displays
        self.currentStepTypeEdit.clear()
        self.currentStepTimeEdit.clear()
        self.stepsRemainingEdit.clear()
        self.totalTimeEdit.clear()

        # Reset valve states
        if self.arduino_worker.running:
            self.arduino_worker.set_valves([0] * 8)  # Close all valves

        # Clear active macro state and re-enable controls
        self.active_valve_macro = None
        self.enable_all_valve_controls()

        # Uncheck all macro buttons
        for i in range(1, 5):
            macro_button = getattr(self, f"valveMacro{i}Button")
            macro_button.setChecked(False)

        self.logger.info("Valves reset to default state")

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
            btn.setCheckable(True)  # Make button checkable
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

        # Connect the select save path button
        self.selectSavePathButton.clicked.connect(
            self.on_selectSavePathButton_clicked)

        # Add this connection
        self.beginSaveButton.clicked.connect(self.on_beginSaveButton_clicked)

    def setup_motor_position_section(self, layout):
        """Setup motor position controls."""
        motor_pos_group = QGroupBox()
        motor_pos_group.setFixedSize(281, 121)
        motor_pos_group.move(740, 10)
        motor_pos_layout = QGridLayout(motor_pos_group)
        motor_pos_layout.setContentsMargins(0, 0, 0, 0)

        # Current Motor Position
        self.cur_motor_pos_label = QLabel("Current Position:")
        font = QFont()
        font.setPointSize(10)
        self.cur_motor_pos_label.setFont(font)
        self.cur_motor_pos_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        motor_pos_layout.addWidget(self.cur_motor_pos_label, 0, 0, 1, 1)

        # Current position as read-only text box
        self.position_spin = QLineEdit()
        self.position_spin.setReadOnly(True)
        self.position_spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        font = QFont()
        font.setPointSize(12)
        self.position_spin.setFont(font)
        motor_pos_layout.addWidget(self.position_spin, 0, 1, 1, 1)

        # Target Motor Position
        self.target_motor_pos_label = QLabel("Target Position:")
        font = QFont()
        font.setPointSize(10)
        self.target_motor_pos_label.setFont(font)
        self.target_motor_pos_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        motor_pos_layout.addWidget(self.target_motor_pos_label, 1, 0, 1, 1)

        # Target position as spin box
        self.target_motor_pos_edit = QDoubleSpinBox()
        self.target_motor_pos_edit.setDecimals(2)
        self.target_motor_pos_edit.setRange(0, 10000)
        self.target_motor_pos_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        font = QFont()
        font.setPointSize(12)
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

        layout.addWidget(motor_pos_group, 0, 3)

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
            btn.setCheckable(True)  # Make button checkable
            font = QFont()
            font.setPointSize(10)
            btn.setFont(font)
            setattr(self, f"motor_macro{i}_button", btn)
            row = (i + 1) // 2
            col = (i - 1) % 2
            motor_macro_layout.addWidget(btn, row, col, 1, 1)

        layout.addWidget(macro_group, 1, 3)

    def setup_menu_bar(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Action menu
        action_menu = menubar.addMenu('Action')
        
        # Add motor sequence action
        motor_sequence_action = QAction('Start Motor Sequence', self)
        motor_sequence_action.triggered.connect(self.start_motor_sequence)
        action_menu.addAction(motor_sequence_action)

        tools_menu = menubar.addMenu("Tools")
        valve_macro_action = tools_menu.addAction("Valve Macros")
        valve_macro_action.triggered.connect(self.edit_macros)
        motor_macro_action = tools_menu.addAction("Motor Macros")
        motor_macro_action.triggered.connect(self.edit_macros)

    def setup_status_bar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")

    def setup_connections(self):
        """Setup signal connections."""
        if self._connections_initialized:
            return
        
        # First disconnect any existing connections to prevent duplicates
        try:
            # Worker signal connections
            self.arduino_worker.readings_updated.disconnect()
            self.arduino_worker.error_occurred.disconnect()
            self.arduino_worker.status_changed.disconnect()

            self.motor_worker.position_updated.disconnect()
            self.motor_worker.error_occurred.disconnect()
            self.motor_worker.status_changed.disconnect()

            # Arduino and valve connections
            self.arduino_connect_btn.clicked.disconnect()
            
            # Valve buttons - Add explicit disconnections
            for i in range(1, 6):
                valve_button = getattr(self, f"Valve{i}Button")
                try:
                    valve_button.clicked.disconnect()
                except TypeError:
                    pass  # Ignore if not connected

            # Quick action buttons
            self.quickVentButton.clicked.disconnect()
            self.slowVentButton.clicked.disconnect()
            self.buildPressureButton.clicked.disconnect()
            self.switchGasButton.clicked.disconnect()
            self.quickBubbleButton.clicked.disconnect()

            # Motor control buttons
            self.motor_connect_btn.clicked.disconnect()
            self.motor_calibrate_btn.clicked.disconnect()
            self.motor_stop_btn.clicked.disconnect()
            self.motor_move_to_target_button.clicked.disconnect()
            self.motor_ascent_button.clicked.disconnect()
            self.motor_to_top_button.clicked.disconnect()

            # Motor macro buttons
            for i in range(1, 7):
                btn = getattr(self, f"motor_macro{i}_button")
                btn.clicked.disconnect()

            # Valve macro buttons
            for i in range(1, 5):
                btn = getattr(self, f"valveMacro{i}Button")
                btn.clicked.disconnect()

            # Pressure radio buttons
            for i in range(1, 5):
                radio = getattr(self, f"pressure{i}RadioButton")
                radio.clicked.disconnect()

        except Exception:
            # Ignore disconnection errors for signals that weren't connected
            pass

        # Now set up new connections
        # Worker signal connections
        self.arduino_worker.readings_updated.connect(self.handle_pressure_readings)
        self.arduino_worker.error_occurred.connect(self.handle_error)
        self.arduino_worker.status_changed.connect(self.handle_status_message)

        self.motor_worker.position_updated.connect(self.handle_position_update)
        self.motor_worker.error_occurred.connect(self.handle_error)
        self.motor_worker.status_changed.connect(self.handle_status_message)
        self.motor_worker.calibration_state_changed.connect(self.handle_calibration_state)

        # Arduino and valve connections
        self.arduino_connect_btn.clicked.connect(self.on_ardConnectButton_clicked)

        # Valve buttons - Use a method instead of lambda
        self.connect_valve_buttons()

        # Quick action buttons
        self.quickVentButton.clicked.connect(self.on_quickVentButton_clicked)
        self.slowVentButton.clicked.connect(self.on_slowVentButton_clicked)
        self.buildPressureButton.clicked.connect(self.on_buildPressureButton_clicked)
        self.switchGasButton.clicked.connect(self.on_switchGasButton_clicked)
        self.quickBubbleButton.clicked.connect(self.on_quickBubbleButton_clicked)

        # Motor control buttons
        self.motor_connect_btn.clicked.connect(self.handle_motor_connection)
        self.motor_calibrate_btn.clicked.connect(self.on_motorCalibrateButton_clicked)
        self.motor_stop_btn.clicked.connect(self.on_motorStopButton_clicked)
        self.motor_move_to_target_button.clicked.connect(self.on_motorMoveToTargetButton_clicked)
        self.motor_ascent_button.clicked.connect(self.on_motorAscentButton_clicked)
        self.motor_to_top_button.clicked.connect(self.on_motorToTopButton_clicked)

        # Motor macro buttons
        for i in range(1, 7):
            btn = getattr(self, f"motor_macro{i}_button")
            btn.clicked.connect(lambda checked, x=i: self.on_motorMacroButton_clicked(x))

        # Valve macro buttons
        for i in range(1, 5):
            btn = getattr(self, f"valveMacro{i}Button")
            btn.clicked.connect(lambda checked, x=i: self.on_valveMacroButton_clicked(x))

        # Pressure radio buttons
        for i in range(1, 5):
            radio = getattr(self, f"pressure{i}RadioButton")
            radio.clicked.connect(lambda checked, x=i: self.on_pressureRadioButton_clicked(x))

        # Connect mode change signals
        self.arduino_connect_button_group.buttonClicked.connect(self.on_arduino_mode_changed)

    def connect_valve_buttons(self):
        """Connect valve button signals using a dedicated method."""
        self.Valve1Button.clicked.connect(self.on_Valve1Button_clicked)
        self.Valve2Button.clicked.connect(self.on_Valve2Button_clicked)
        self.Valve3Button.clicked.connect(self.on_Valve3Button_clicked)
        self.Valve4Button.clicked.connect(self.on_Valve4Button_clicked)
        self.Valve5Button.clicked.connect(self.on_Valve5Button_clicked)
        self.Valve6Button.clicked.connect(self.on_Valve6Button_clicked)  # Add connection for 6th valve

    @pyqtSlot()
    def handle_motor_connection(self):
        """Handle motor connection/disconnection."""
        try:
            if not self.motor_worker.running:
                # Get the port value from the spin box
                port = self.motor_com_port_spin.value()
                
                # Create new worker with current port value
                self.motor_worker = MotorWorker(
                    port=port,
                    mock=self.test_mode
                )
                
                # Reconnect signals for new worker instance
                self.motor_worker.position_updated.connect(self.handle_position_update)
                self.motor_worker.error_occurred.connect(self.handle_error)
                self.motor_worker.status_changed.connect(self.handle_status_message)
                self.motor_worker.calibration_state_changed.connect(self.handle_calibration_state)
                
                # Start the worker - in test mode we don't need actual connection
                if self.test_mode or self.motor_worker.start():
                    self.motor_connect_btn.setText("Disconnect")
                    self.motor_warning_label.setText("")
                    self.motor_warning_label.setVisible(False)
                    self.motor_calibrate_btn.setEnabled(True)
                    self.disable_motor_controls(True)
                    self.logger.info(f"Connected to motor on COM{port}")
                else:
                    self.handle_error("Failed to connect to motor")
                    self.motor_warning_label.setText("Warning: Motor not connected")
                    self.motor_calibrate_btn.setEnabled(False)
                    self.disable_motor_controls(True)
            else:
                # Disconnect the motor
                self.motor_worker.stop()  # This stops the worker thread and closes the connection
                self.motor_connect_btn.setText("Connect")
                self.motor_calibrated = False
                self.motor_warning_label.setText("Warning: Motor not connected")
                self.motor_warning_label.setVisible(True)
                self.motor_calibrate_btn.setEnabled(False)
                self.disable_motor_controls(True)
                self.logger.info("Disconnected from motor")

        except Exception as e:
            self.logger.error(f"Error in motor connection handler: {e}")
            self.handle_error(f"Motor connection error: {str(e)}")

    @pyqtSlot(bool)
    def handle_calibration_state(self, is_calibrated: bool):
        """Handle changes in motor calibration state."""
        self.motor_calibrated = is_calibrated
        self.disable_motor_controls(not is_calibrated)
        if is_calibrated:
            self.motor_calibrate_btn.setEnabled(True)
            self.logger.info("Motor calibration state: Calibrated")
        else:
            self.logger.info("Motor calibration state: Not calibrated")

    def find_sequence_file(self):
        """Look for sequence file in the specified location."""
        try:
            self.file_timer = QTimer()
            self.file_timer.timeout.connect(self.check_sequence_file)
            self.file_timer.start(500)  # Check every 500ms
        except Exception as e:
            self.logger.error(f"Error setting up sequence file timer: {e}")
            self.handle_error("Failed to start sequence file monitoring")

    def check_sequence_file(self):
        """Check for and process sequence file."""
        try:
            if not self.arduino_worker.running:
                self.logger.error("Arduino worker not running")
                self.file_timer.stop()
                return

            sequence_path = Path(r"C:\ssbubble\sequence.txt")
            if not sequence_path.exists():
                return

            # Process in chunks to avoid blocking
            def process_sequence():
                try:
                    success = self.load_sequence()
                    if success:
                        self.handle_sequence_file(True)
                        self.calculate_sequence_time()
                        
                        # Update UI with first step using invokeMethod
                        if self.steps:
                            QMetaObject.invokeMethod(self, "update_sequence_info",
                                Qt.ConnectionType.QueuedConnection,
                                Q_ARG(str, self.step_types[self.steps[0].step_type]),
                                Q_ARG(float, self.steps[0].time_length),
                                Q_ARG(int, len(self.steps)),
                                Q_ARG(float, self.total_sequence_time))
                            
                            QMetaObject.invokeMethod(self, "start_sequence",
                                Qt.ConnectionType.QueuedConnection)
                        
                        self.file_timer.stop()
                    else:
                        self.handle_sequence_file(False)
                except Exception as e:
                    self.logger.error(f"Error processing sequence: {e}")
                    
            # Process sequence in a separate thread to avoid blocking
            QTimer.singleShot(0, process_sequence)

        except Exception as e:
            self.logger.error(f"Error in sequence file check: {e}")
            self.handle_error(f"Sequence file check failed: {str(e)}")

    @pyqtSlot()
    def _update_arduino_disconnect_state(self):
        """Update UI elements when Arduino disconnects. This method runs in the main thread."""
        self.arduino_connect_btn.setText("Connect")
        if not self.test_mode:
            self.arduino_warning_label.setText("Warning: Arduino not connected")
            self.arduino_warning_label.setVisible(True)

    def calculate_sequence_time(self):
        """Calculate total sequence time."""
        self.sequence_running_time = 0
        self.step_running_time = 0
        self.total_sequence_time = sum(step.time_length for step in self.steps)
        self.current_step_time = self.steps[0].time_length if self.steps else 0
        self.logger.info(f"Sequence length is {self.total_sequence_time} ms")

    def write_to_prospa(self, success: bool):
        """Write status back to Prospa."""
        try:
            with open(r"C:\ssbubble\prospa.txt", "w") as f:
                f.write("1" if success else "0")
        except Exception as e:
            self.logger.error(f"Failed to write to Prospa: {e}")

    def delete_sequence_file(self):
        """Delete the sequence file."""
        try:
            Path(r"C:\ssbubble\sequence.txt").unlink(missing_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to delete sequence file: {e}")

    @pyqtSlot(bool)
    def on_Valve1Button_clicked(self, checked: bool):
        """Handle Valve 1 (Switch valve) button click."""
        if self.arduino_worker.running:
            # Create valve states list with all valves off except the target valve
            valve_states = [0] * 8  # 8 valve states
            valve_states[0] = 1 if checked else 0  # Valve 1 is index 0
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(f"Valve 1 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve2Button_clicked(self, checked: bool):
        """Handle Valve 2 (Inlet valve) button click."""
        if self.arduino_worker.running:
            valve_states = [0] * 8
            valve_states[1] = 1 if checked else 0  # Valve 2 is index 1
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(f"Valve 2 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve3Button_clicked(self, checked: bool):
        """Handle Valve 3 (Outlet valve) button click."""
        if self.arduino_worker.running:
            valve_states = [0] * 8
            valve_states[2] = 1 if checked else 0  # Valve 3 is index 2
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(f"Valve 3 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve4Button_clicked(self, checked: bool):
        """Handle Valve 4 (Vent valve) button click."""
        if self.arduino_worker.running:
            valve_states = [0] * 8
            valve_states[3] = 1 if checked else 0  # Valve 4 is index 3
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(f"Valve 4 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve5Button_clicked(self, checked: bool):
        """Handle Valve 5 (Short valve) button click."""
        if self.arduino_worker.running:
            valve_states = [0] * 8
            valve_states[4] = 1 if checked else 0  # Valve 5 is index 4
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(f"Valve 5 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve6Button_clicked(self, checked: bool):
        """Handle Valve 6 button click."""
        if self.arduino_worker.running:
            # Create valve states list with all valves off except the target valve
            valve_states = [0] * 8  # 8 valve states
            valve_states[5] = 1 if checked else 0  # Valve 6 is index 5
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(f"Valve 6 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_quickVentButton_clicked(self, checked: bool):
        """Handle quick vent button click."""
        if not self.arduino_worker.running:
            return

        if checked:
            # Configure valves for quick venting
            valve_states = [0] * 8  # Initialize all valves closed
            valve_states[1] = 0     # Close inlet (Valve 2)
            valve_states[3] = 1     # Open vent (Valve 4)
            valve_states[4] = 1     # Open short (Valve 5)
            self.arduino_worker.set_valves(valve_states)

            # Update valve button states
            self.Valve2Button.setChecked(False)  # Inlet
            self.Valve4Button.setChecked(True)   # Vent
            self.Valve5Button.setChecked(True)   # Short

            self.logger.info("Quick vent started")
        else:
            # Close all valves
            self.arduino_worker.set_valves([0] * 8)

            # Update valve button states
            self.Valve4Button.setChecked(False)  # Vent
            self.Valve5Button.setChecked(False)  # Short

            self.logger.info("Quick vent stopped")

    @pyqtSlot(bool)
    def on_slowVentButton_clicked(self, checked: bool):
        """Handle slow vent button click."""
        if not self.arduino_worker.running:
            return

        if checked:
            # Configure valves for slow venting
            valve_states = [0] * 8  # Initialize all valves closed
            valve_states[1] = 0     # Close inlet (Valve 2)
            valve_states[3] = 1     # Open vent (Valve 4)
            self.arduino_worker.set_valves(valve_states)

            # Update valve button states
            self.Valve2Button.setChecked(False)  # Inlet
            self.Valve4Button.setChecked(True)   # Vent

            self.logger.info("Slow vent started")
        else:
            # Close all valves
            self.arduino_worker.set_valves([0] * 8)

            # Update valve button states
            self.Valve4Button.setChecked(False)  # Vent

            self.logger.info("Slow vent stopped")

    @pyqtSlot(bool)
    def on_buildPressureButton_clicked(self, checked: bool):
        """Handle build pressure button click."""
        if self.arduino_worker.running:
            valve_states = [0] * 8
            valve_states[1] = 1 if checked else 0  # Valve 2 (inlet)
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(f"Pressure build {'started' if checked else 'stopped'}")

    @pyqtSlot(bool)
    def on_switchGasButton_clicked(self, checked: bool):
        """Handle switch gas button click."""
        if self.arduino_worker.running:
            valve_states = [0] * 8
            valve_states[0] = 1 if checked else 0  # Valve 1 (switch)
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(
                f"Gas switch {'started' if checked else 'stopped'}")

    @pyqtSlot(bool)
    def on_quickBubbleButton_clicked(self, checked: bool):
        """Handle quick bubble button click."""
        if not self.arduino_worker.running:
            return

        if checked:
            duration = self.bubbleTimeDoubleSpinBox.value()
            # Open inlet and outlet valves
            valve_states = [0] * 8
            valve_states[1] = 1  # Valve 2 (inlet)
            valve_states[2] = 1  # Valve 3 (outlet)
            self.arduino_worker.set_valves(valve_states)

            # Start timer to close valves after duration
            QTimer.singleShot(int(duration * 1000), self.stop_bubble)
            self.logger.info(f"Quick bubble started for {duration}s")
        else:
            self.stop_bubble()

    def stop_bubble(self):
        """Stop bubbling sequence."""
        if self.arduino_worker.running:
            # Close all valves
            self.arduino_worker.set_valves([0] * 8)
            self.quickBubbleButton.setChecked(False)
            self.logger.info("Quick bubble complete")

    def disable_valve_controls(self, disabled: bool):
        """Enable/disable valve controls."""
        # Only enable if in manual mode and Arduino is connected
        enabled = (not disabled and 
                  self.arduino_worker.running and 
                  self.arduino_manual_radio.isChecked())

        # Disable individual valve buttons
        for i in range(1, 7):  # Changed from 6 to 7 to include Valve6
            valve_button = getattr(self, f"Valve{i}Button")
            valve_button.setEnabled(enabled)

        # Quick action buttons
        self.quickBubbleButton.setEnabled(enabled)
        self.switchGasButton.setEnabled(enabled)
        self.buildPressureButton.setEnabled(enabled)
        self.quickVentButton.setEnabled(enabled)
        self.slowVentButton.setEnabled(enabled)

        # Valve macro buttons
        for i in range(1, 5):
            if hasattr(self, f'valveMacro{i}Button'):
                getattr(self, f'valveMacro{i}Button').setEnabled(enabled)

    def disable_quick_controls(self, disabled: bool):
        """Enable/disable quick action and macro controls."""
        # Disable quick action buttons
        quick_action_buttons = [
            self.quickVentButton,
            self.slowVentButton,
            self.buildPressureButton,
            self.switchGasButton,
            self.quickBubbleButton
        ]

        for button in quick_action_buttons:
            button.setEnabled(not disabled)
            if disabled:
                button.setChecked(False)

        # Disable valve macro buttons
        for i in range(1, 5):
            macro_button = getattr(self, f"valveMacro{i}Button")
            if macro_button:
                macro_button.setEnabled(not disabled)
                if disabled:
                    macro_button.setChecked(False)

    def toggle_valve_controls(self, enabled: bool):
        """Enable or disable valve control buttons based on checkbox state.

        Args:
            enabled (bool): True to enable buttons, False to disable
        """
        if self.arduino_worker.running:
            # Only enable valve buttons if Arduino is connected and in manual mode
            if self.arduino_worker.controller.mode == 0:  # Manual mode
                # Only toggle the individual valve buttons 1-5
                for i in range(1, 6):
                    if hasattr(self, f'Valve{i}Button'):
                        getattr(self, f'Valve{i}Button').setEnabled(enabled)
            else:
                # Force disable if not in manual mode
                for i in range(1, 6):
                    if hasattr(self, f'Valve{i}Button'):
                        getattr(self, f'Valve{i}Button').setEnabled(False)
                self.dev_checkbox.setChecked(False)
        else:
            # Force disable if Arduino not connected
            for i in range(1, 6):
                if hasattr(self, f'Valve{i}Button'):
                    getattr(self, f'Valve{i}Button').setEnabled(False)
            self.dev_checkbox.setChecked(False)

    @pyqtSlot()
    def on_ardConnectButton_clicked(self):
        """Handle Arduino connect button click."""
        try:
            if not self.arduino_worker.running:
                # Determine connection mode
                if self.arduino_auto_connect_radio.isChecked():
                    mode = 1  # Auto mode
                elif self.arduino_ttl_radio.isChecked():
                    mode = 2  # TTL mode
                else:
                    mode = 0  # Manual mode

                try:
                    # Set mode before starting the worker
                    self.arduino_worker.controller.mode = mode
                    success = self.arduino_worker.start()
                    if success or self.test_mode:
                        self.arduino_connect_btn.setText("Disconnect")
                        self.arduino_warning_label.setText("")
                        self.arduino_warning_label.setVisible(False)

                        # Enable/disable controls based on mode
                        if mode == 0:  # Manual mode
                            # Enable checkbox for valve buttons
                            self.dev_checkbox.setEnabled(True)
                            self.disable_quick_controls(False)  # Enable other controls
                        else:
                            self.dev_checkbox.setEnabled(False)
                            self.disable_valve_controls(True)
                            self.disable_quick_controls(True)

                        # Set valve mode
                        self.set_valve_mode(mode == 1)

                        # If in automatic mode, start looking for sequence file after a delay
                        if mode == 1:
                            # Set motor to sequence mode if connected
                            if self.motor_worker.running:
                                self.motor_worker.set_sequence_mode(True)
                                self.logger.info("Motor set to sequence mode")
                            # Wait 2 seconds before starting sequence file monitoring
                            QTimer.singleShot(2000, self.find_sequence_file)
                            self.logger.info("Will start sequence file monitoring in 2 seconds")

                        self.logger.info(f"Connected to Arduino in mode {mode}")
                    else:
                        self.handle_error("Failed to connect to Arduino")
                        if not self.test_mode:
                            self.arduino_warning_label.setText(
                                "Warning: Arduino not connected")
                            self.arduino_warning_label.setVisible(True)
                except Exception as e:
                    self.handle_error(f"Failed to connect to Arduino: {str(e)}")
                    self.arduino_connect_btn.setText("Connect")
                    if not self.test_mode:
                        self.arduino_warning_label.setText(
                            "Warning: Arduino not connected")
                        self.arduino_warning_label.setVisible(True)
            else:
                try:
                    self.arduino_worker.stop()
                    self.arduino_connect_btn.setText("Connect")
                    if not self.test_mode:
                        self.arduino_warning_label.setText(
                            "Warning: Arduino not connected")
                        self.arduino_warning_label.setVisible(True)

                    # Disable all valve controls on disconnect
                    self.dev_checkbox.setEnabled(False)
                    self.dev_checkbox.setChecked(False)
                    self.disable_valve_controls(True)

                    # Reset to manual mode when disconnecting
                    self.set_valve_mode(False)
                    self.logger.info("Disconnected from Arduino")
                except Exception as e:
                    self.handle_error(f"Error disconnecting Arduino: {str(e)}")

        except Exception as e:
            self.logger.error(f"Uncaught exception in Arduino connection: {str(e)}")
            self.handle_error("An unexpected error occurred while connecting to Arduino")
            self.arduino_connect_btn.setText("Connect")
            if not self.test_mode:
                self.arduino_warning_label.setText(
                    "Warning: Arduino not connected")
                self.arduino_warning_label.setVisible(True)

    @pyqtSlot()
    def on_motorCalibrateButton_clicked(self):
        """Handle motor calibration button click."""
        if self.motor_worker.running:
            try:
                # Disable controls during calibration
                self.disable_motor_controls(True)
                self.motor_calibrate_btn.setEnabled(False)
                
                if self.motor_worker.calibrate():
                    self.logger.info("Motor calibration started")
                else:
                    self.handle_error("Failed to start motor calibration")
            except Exception as e:
                self.handle_error(f"Calibration error: {e}")
            self.motor_calibrate_btn.setEnabled(True)

    @pyqtSlot(bool)
    def handle_calibration_complete(self, success: bool):
        """Handle completion of motor calibration."""
        if success:
            self.motor_calibrated = True
            self.disable_motor_controls(False)
        else:
            self.motor_calibrated = False
            self.handle_error("Motor calibration failed")
        self.motor_calibrate_btn.setEnabled(True)

    @pyqtSlot()
    def on_motorStopButton_clicked(self):
        """Handle motor emergency stop button click."""
        if self.motor_worker.running:
            self.motor_worker.emergency_stop()
            self.motor_calibrated = False  # Reset calibration state after emergency stop
            # Disable controls after emergency stop
            self.disable_motor_controls(True)
            self.motor_calibrate_btn.setEnabled(True)  # Allow recalibration
            self.logger.warning("Motor emergency stop activated")

    @pyqtSlot()
    def on_motorMoveToTargetButton_clicked(self):
        """Handle move to target button click."""
        if self.motor_worker.running:
            try:
                target = self.target_motor_pos_edit.value()
                
                # Special case: if target is 0, use to_top command instead
                if target == 0:
                    if self.motor_worker.to_top():
                        self.logger.info("Moving motor to top position (0.00)")
                        return
                    else:
                        self.handle_error("Failed to move motor to top")
                        return
                
                if target < 0:
                    QMessageBox.warning(self, "Invalid Position", 
                        "Invalid target position. Position must be non-negative (0 is home position at top).")
                    return
                if target > self.motor_worker.controller.POSITION_MAX:
                    response = QMessageBox.question(self, "Position Limit Exceeded",
                        f"Target position {target}mm exceeds maximum allowed position of {self.motor_worker.controller.POSITION_MAX}mm.\n\n"
                        f"Would you like to move to the maximum position of {self.motor_worker.controller.POSITION_MAX}mm?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
                    
                    if response == QMessageBox.StandardButton.Cancel:
                        return
                    target = self.motor_worker.controller.POSITION_MAX
            
                self.motor_worker.move_to(target)
                self.logger.info(f"Moving motor to position {target}mm")
            except ValueError:
                self.handle_error("Invalid target position")

    @pyqtSlot()
    def on_motorAscentButton_clicked(self):
        """Handle motor ascent button click."""
        if self.motor_worker.running:
            if self.motor_worker.ascent():
                self.logger.info("Starting motor ascent")
            else:
                self.handle_error("Failed to start motor ascent")

    @pyqtSlot()
    def on_motorToTopButton_clicked(self):
        """Handle motor to top button click."""
        if self.motor_worker.running:
            if self.motor_worker.to_top():
                self.logger.info("Moving motor to top position")
            else:
                self.handle_error("Failed to move motor to top")

    @pyqtSlot(int)
    def on_motorMacroButton_clicked(self, macro_num: int):
        """Handle motor macro button click.

        Args:
            macro_num: Macro number (1-6)
        """
        if self.motor_worker.running:
            try:
                # Get the macro button that was clicked
                macro_button = getattr(self, f"motor_macro{macro_num}_button")

                # Uncheck all other macro buttons
                for i in range(1, 7):
                    if i != macro_num:
                        other_button = getattr(self, f"motor_macro{i}_button")
                        other_button.setChecked(False)

                macro = self.load_motor_macro(macro_num)
                if macro:
                    position = macro["Position"]
                    # Add position validation
                    if position < 0:
                        self.handle_error(
                            "Invalid macro position. Motor positions must be non-negative (0 is home position at top).")
                        return

                    # Check the macro button
                    macro_button.setChecked(True)

                    # Start the movement
                    success = self.motor_worker.move_to(position)
                    if success:
                        self.logger.info(f"Executing motor macro {macro_num}: {macro['Label']}")

                        # Create a timer to check position periodically
                        self.position_check_timer = QTimer(self)
                        self.position_check_timer.setInterval(
                            100)  # Check every 100ms

                        def check_position():
                            current_pos = self.motor_worker.get_current_position()
                            if current_pos == position:
                                macro_button.setChecked(False)
                                self.position_check_timer.stop()
                                self.position_check_timer = None

                        self.position_check_timer.timeout.connect(
                            check_position)
                        self.position_check_timer.start()
                    else:
                        macro_button.setChecked(False)
                else:
                    self.handle_error(f"Motor macro {macro_num} not found")
                    macro_button.setChecked(False)
            except Exception as e:
                self.handle_error(
                    f"Failed to execute motor macro {macro_num}: {e}")
                # Ensure macro button is unchecked on error
                macro_button = getattr(self, f"motor_macro{macro_num}_button")
                macro_button.setChecked(False)
                # Clean up timer on error
                if self.position_check_timer is not None:
                    self.position_check_timer.stop()
                    self.position_check_timer = None

    @pyqtSlot(bool)
    def on_beginSaveButton_clicked(self, checked=None):
        """Handle begin save button click."""
        # If called programmatically, use button's checked state
        if checked is None:
            checked = self.beginSaveButton.isChecked()

        if checked:
            try:
                # Create data directory if it doesn't exist
                data_dir = Path("C:/ssbubble/data")
                data_dir.mkdir(parents=True, exist_ok=True)

                # Get or generate save path
                save_path = self.savePathEdit.text()
                if not save_path:
                    # Generate default save path with timestamp
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    save_path = str(
                        data_dir / f"pressure_data_{timestamp}.csv")

                # Update the text field with the generated path
                self.savePathEdit.setText(save_path)

                # Ensure directory exists
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)

                # Start recording
                if self.plot_widget.start_recording(save_path):
                    self.beginSaveButton.setText("Stop Saving")
                    self.saving = True
                    self.logger.info(f"Started recording data to {save_path}")
                else:
                    self.handle_error("Failed to start recording")
                    self.beginSaveButton.setChecked(False)
                    self.saving = False
                    self.beginSaveButton.setText("Begin Saving")
            except Exception as e:
                self.handle_error(f"Failed to start recording: {str(e)}")
                self.beginSaveButton.setChecked(False)
                self.saving = False
                self.beginSaveButton.setText("Begin Saving")
        else:
            self.plot_widget.stop_recording()
            self.beginSaveButton.setText("Begin Saving")
            self.beginSaveButton.setChecked(
                False)  # Ensure button is unchecked
            self.saving = False
            self.logger.info("Stopped recording data")

    @pyqtSlot()
    def on_selectSavePathButton_clicked(self):
        """Handle select save path button click."""
        try:
            # Get initial directory - use current path if exists, otherwise default
            initial_dir = str(Path(self.savePathEdit.text(
            )).parent) if self.savePathEdit.text() else self.default_save_path

            # Create default filename with timestamp
            default_filename = f"pressure_data_{
                time.strftime('%m%d-%H%M')}.csv"

            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Select Save Location",
                os.path.join(initial_dir, default_filename),
                "CSV Files (*.csv);;All Files (*.*)"
            )

            if file_path:
                # If user didn't add .csv extension, add it
                if not file_path.lower().endswith('.csv'):
                    file_path += '.csv'

                # Update the save path text field
                self.savePathEdit.setText(file_path)
                self.logger.info(f"Save path set to: {file_path}")

        except Exception as e:
            self.logger.error(f"Error setting save path: {e}")
            self.handle_error("Failed to set save path")

    @pyqtSlot(int)
    def on_pressureRadioButton_clicked(self, sensor_num: int):
        """Handle pressure sensor radio button click.

        Args:
            sensor_num: Pressure sensor number (1-4)
        """
        radio = getattr(self, f"pressure{sensor_num}RadioButton")
        # Adjust index since plot widget uses 0-based indexing
        if sensor_num <= 3:  # Only first 3 sensors are plotted
            self.plot_widget.sensor_toggles[sensor_num -
                                            1].setChecked(radio.isChecked())
        self.logger.info(
            f"Pressure sensor {sensor_num} display {'enabled' if radio.isChecked() else 'disabled'}")

    @pyqtSlot(int)
    def on_valveMacroButton_clicked(self, macro_num: int):
        """Handle valve macro button click.

        Args:
            macro_num: Macro number (1-4)
        """
        if self.arduino_worker.running:
            try:
                # Get the macro button that was clicked
                macro_button = getattr(self, f"valveMacro{macro_num}Button")

                # If this macro is already active, treat as cancel
                if self.active_valve_macro == macro_num:
                    # Cancel any pending timer
                    if self.active_macro_timer is not None:
                        self.active_macro_timer.stop()
                        self.active_macro_timer = None
                    self.reset_valves()
                    self.active_valve_macro = None
                    return

                macro = self.load_valve_macro(macro_num)
                if macro:
                    # Cancel any existing timer from previous macro
                    if self.active_macro_timer is not None:
                        self.active_macro_timer.stop()
                        self.active_macro_timer = None

                    # Disable other valve controls before executing macro
                    self.active_valve_macro = macro_num
                    self.disable_other_valve_controls(macro_num)

                    # Convert valve states to binary (0/1)
                    valve_states = []
                    for state in macro["Valves"]:
                        if state == "Open":
                            valve_states.append(1)
                        else:  # "Closed" or "Ignore"
                            valve_states.append(0)

                    # Ensure we have 8 valve states (pad with zeros if needed)
                    while len(valve_states) < 8:
                        valve_states.append(0)

                    # Send valve states to Arduino
                    self.arduino_worker.set_valves(valve_states)
                    self.logger.info(f"Sent valve states for macro {macro_num}: {valve_states}")

                    # Update valve button states
                    # Only first 5 valves have buttons
                    for i, state in enumerate(valve_states[:5]):
                        valve_button = getattr(self, f"Valve{i+1}Button")
                        valve_button.setChecked(bool(state))

                    # Check the macro button
                    macro_button.setChecked(True)

                    # If macro has a timer, schedule valve reset
                    timer = macro.get("Timer", 0)
                    if timer > 0:
                        def reset_valves():
                            # Reset all valves to closed
                            self.arduino_worker.set_valves([0] * 8)
                            self.logger.info("Reset valves after macro timer")
                            
                            # Reset button states
                            for i in range(1, 6):
                                valve_button = getattr(self, f"Valve{i}Button")
                                valve_button.setChecked(False)
                            
                            # Reset macro state
                            self.active_valve_macro = None
                            self.active_macro_timer = None
                            macro_button.setChecked(False)
                            
                            # Re-enable controls
                            self.enable_all_valve_controls()

                        # Create and store the timer
                        self.active_macro_timer = QTimer()
                        self.active_macro_timer.setSingleShot(True)
                        self.active_macro_timer.timeout.connect(reset_valves)
                        self.active_macro_timer.start(int(timer * 1000))

                    self.logger.info(f"Executed valve macro {macro_num}: {macro['Label']}")
                else:
                    self.handle_error(f"Valve macro {macro_num} not found")
                    macro_button.setChecked(False)
            except Exception as e:
                self.handle_error(f"Failed to execute valve macro {macro_num}: {e}")
                # Ensure macro button is unchecked on error
                macro_button = getattr(self, f"valveMacro{macro_num}Button")
                macro_button.setChecked(False)
                # Clean up timer and state on error
                if self.active_macro_timer is not None:
                    self.active_macro_timer.stop()
                    self.active_macro_timer = None
                self.active_valve_macro = None
                self.enable_all_valve_controls()

    @pyqtSlot()
    def on_loadSequence_clicked(self):
        """Handle load sequence button click."""
        sequence = self.sequence_combo.currentText()
        self.logger.info(f"Loading sequence: {sequence}")
        # Add sequence loading logic here

    @pyqtSlot()
    def on_startSequence_clicked(self):
        """Handle start sequence button click."""
        self.logger.info("Starting sequence")
        # Add sequence start logic here

    @pyqtSlot()
    def on_pauseSequence_clicked(self):
        """Handle pause sequence button click."""
        self.logger.info("Pausing sequence")
        # Add sequence pause logic here

    @pyqtSlot()
    def on_stopSequence_clicked(self):
        """Handle stop sequence button click."""
        self.logger.info("Stopping sequence")
        # Add sequence stop logic here

    @pyqtSlot(str, float, int, float)
    def update_sequence_info(self, step_type: str, step_time: float, steps_left: int, total_time: float):
        """Update sequence information displays."""
        try:
            self.currentStepTypeEdit.setText(str(step_type))
            self.currentStepTimeEdit.setText(f"{step_time:.1f}s")
            self.stepsRemainingEdit.setText(str(steps_left))
            self.totalTimeEdit.setText(f"{total_time:.1f}s")
        except Exception as e:
            self.logger.error(f"Error updating sequence info: {e}")

    @pyqtSlot(str)
    def update_sequence_status(self, status: str):
        """Update sequence status display.

        Args:
            status: Status message to display
        """
        self.sequence_status_label.setText(f"Status: {status}")

    @pyqtSlot()
    def start_sequence(self):
        """Start executing the loaded sequence."""
        try:
            if not self.steps:
                self.logger.error("No sequence loaded")
                return

            # Enable sequence mode for motor if motor movements are part of sequence
            if self.motor_flag and self.motor_worker.running:
                # Check calibration once at sequence start
                if not self.motor_worker.controller.check_calibrated():
                    self.logger.error("Motor not calibrated - cannot start sequence")
                    self.handle_error("Motor must be calibrated before starting sequence")
                    return
                    
                # Explicitly set sequence mode
                self.motor_worker.set_sequence_mode(True)
                self.logger.info("Motor set to sequence mode for sequence execution")

            # Execute first step
            self.execute_step(self.steps[0])

            # Start step timer
            self.step_start_time = time.time()
            self.step_timer = QTimer()
            self.step_timer.timeout.connect(self.update_step_time)
            self.step_timer.start(100)  # Update every 100ms

            # Schedule next step
            if len(self.steps) > 1:
                QTimer.singleShot(self.steps[0].time_length, self.next_step)

            self.logger.info("Sequence execution started")

        except Exception as e:
            self.logger.error(f"Error starting sequence: {e}")
            self.handle_error("Failed to start sequence")
            # Disable sequence mode on error
            if self.motor_flag and self.motor_worker.running:
                self.motor_worker.set_sequence_mode(False)

    def next_step(self):
        """Execute the next step in the sequence."""
        try:
            # Remove completed step
            self.steps.pop(0)

            if self.steps:
                # Execute next step
                self.execute_step(self.steps[0])
                # Reset step timer and schedule next step
                self.step_start_time = time.time()
                QTimer.singleShot(self.steps[0].time_length, self.next_step)
            else:
                # Sequence complete
                self.step_timer.stop()
                # Disable sequence mode when complete
                if self.motor_flag and self.motor_worker.running:
                    self.motor_worker.set_sequence_mode(False)
                
                # Update UI and handle completion
                self.update_sequence_info("Complete", 0, 0, 0)
                self.update_sequence_status("Complete")
                
                # Stop data recording if active
                if self.saving:
                    self.plot_widget.stop_recording()
                    self.beginSaveButton.setText("Begin Saving")
                    self.beginSaveButton.setChecked(False)
                    self.saving = False
                    self.logger.info("Data recording stopped with sequence completion")

                self.logger.info("Sequence execution completed")

        except Exception as e:
            self.logger.error(f"Error in sequence execution: {e}")
            self.handle_error("Failed to execute sequence")
            # Disable sequence mode on error
            if self.motor_flag and self.motor_worker.running:
                self.motor_worker.set_sequence_mode(False)

    def execute_step(self, step):
        """Execute a single sequence step."""
        try:
            # Set valve states based on step type
            valve_states = [0] * 8  # Initialize all valves closed

            if step.step_type == 'p':  # Pressurize
                valve_states[1] = 1  # Open inlet valve
            elif step.step_type == 'v':  # Vent
                valve_states[3] = 1  # Open vent valve
            elif step.step_type == 'b':  # Bubble
                valve_states[1] = 1  # Open inlet valve
                valve_states[2] = 1  # Open outlet valve
            elif step.step_type == 'f':  # Flow
                valve_states[2] = 1  # Open outlet valve
            elif step.step_type == 'e':  # Evacuate
                valve_states[3] = 1  # Open vent valve
                valve_states[4] = 1  # Open short valve

            # Set valve states
            self.arduino_worker.set_valves(valve_states)

            # Move motor if required
            if self.motor_flag and step.motor_position is not None:
                self.motor_worker.move_to(step.motor_position)

            self.logger.info(f"Executing step: {self.step_types[step.step_type]}")

        except Exception as e:
            self.logger.error(f"Error executing step: {e}")
            self.handle_error("Failed to execute sequence step")

    def disable_other_valve_controls(self, active_macro_num: int):
        """Disable all valve controls except the active macro button.
        
        Args:
            active_macro_num: Number of the active macro button (1-4)
        """
        # Disable individual valve buttons
        for i in range(1, 6):
            valve_button = getattr(self, f"Valve{i}Button")
            valve_button.setEnabled(False)

        # Disable other macro buttons
        for i in range(1, 5):
            if i != active_macro_num:
                macro_button = getattr(self, f"valveMacro{i}Button")
                macro_button.setEnabled(False)

        # Disable quick action buttons
        self.quickBubbleButton.setEnabled(False)
        self.switchGasButton.setEnabled(False)
        self.buildPressureButton.setEnabled(False)
        self.quickVentButton.setEnabled(False)
        self.slowVentButton.setEnabled(False)

    def enable_all_valve_controls(self):
        """Re-enable all valve controls."""
        # Only enable if in manual mode and Arduino is connected
        if self.arduino_worker.running and self.arduino_manual_radio.isChecked():
            # Enable individual valve buttons
            for i in range(1, 6):
                valve_button = getattr(self, f"Valve{i}Button")
                valve_button.setEnabled(True)

            # Enable macro buttons
            for i in range(1, 5):
                macro_button = getattr(self, f"valveMacro{i}Button")
                macro_button.setEnabled(True)

            # Enable quick action buttons
            self.quickBubbleButton.setEnabled(True)
            self.switchGasButton.setEnabled(True)
            self.buildPressureButton.setEnabled(True)
            self.quickVentButton.setEnabled(True)
            self.slowVentButton.setEnabled(True)

    def load_valve_macro(self, macro_num: int) -> dict:
        """Load valve macro data from JSON file.

        Args:
            macro_num: Macro number (1-4)

        Returns:
            dict: Macro data or None if not found
        """
        try:
            json_path = Path("C:/ssbubble/valve_macro_data.json")
            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    for macro in data:
                        if macro["Macro No."] == f"Macro {macro_num}":
                            return macro
        except Exception as e:
            self.logger.error(f"Error loading valve macro {macro_num}: {e}")
        return None

    def load_motor_macro(self, macro_num: int) -> dict:
        """Load motor macro data from JSON file.

        Args:
            macro_num: Macro number (1-6)

        Returns:
            dict: Macro data or None if not found
        """
        try:
            json_path = Path("C:/ssbubble/motor_macro_data.json")
            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    for macro in data:
                        if macro["Macro No."] == f"Macro {macro_num}":
                            return macro
        except Exception as e:
            self.logger.error(f"Error loading motor macro {macro_num}: {e}")
        return None

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
            self.arduino_connect_btn.setText("Connect")
            self.logger.info("Disconnected from Arduino due to port change")

        self.arduino_worker = ArduinoWorker(
            port=port,
            mock=self.test_mode
        )
        self.setup_connections()
        #self.logger.debug(f"Arduino port updated to COM{port}")

    @pyqtSlot(list)
    def handle_pressure_readings(self, readings: List[float]):
        """Handle pressure reading updates."""
        self.plot_widget.update_plot(readings)

    @pyqtSlot(float)  # Update slot to accept float
    def handle_position_update(self, position: float):
        """Handle motor position update.

        Args:
            position: Current motor position (float)
        """
        try:
            # Format position to 2 decimal places and update display
            self.position_spin.setText(f"{position:.2f}")
        except Exception as e:
            self.logger.error(f"Error updating position display: {e}")

    @pyqtSlot(str)
    def handle_status_message(self, message: str):
        """Handle status message updates."""
        # Check for motor disconnection message
        if message == "Motor disconnected":
            # Reset UI elements
            self.motor_connect_btn.setText("Connect")
            self.motor_calibrated = False
            self.motor_warning_label.setText("Warning: Motor not connected")
            self.motor_warning_label.setVisible(True)
            self.motor_calibrate_btn.setEnabled(False)
            self.disable_motor_controls(True)
            
        self.statusBar().showMessage(message)
        self.log_widget.add_message(message)

    @pyqtSlot(str)
    def handle_error(self, message: str):
        """Handle error messages."""
        # Only show message box for critical errors, not connection issues
        if not any(err in message.lower() for err in ["position", "failed to get", "connection"]):
            QMessageBox.critical(self, "Error", message)
        # Log all errors
        self.logger.error(message)

    def edit_macros(self):
        """Open macro editor dialog."""
        # Get the sender (which menu item triggered this)
        sender = self.sender()
        if sender.text() == "Valve Macros":
            editor = ValveMacroEditor(self)
        else:  # Motor Macros
            editor = MotorMacroEditor(self)
        editor.exec()

    def move_motor(self):
        """Move motor to specified position."""
        position = self.position_spin.value()
        self.motor_worker.move_to(position)

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

    def load_sequence(self):
        """Load a sequence from a file."""
        try:
            negative_positions_found = False  # Track if any negative positions are found
            self.steps = []  # initialise steps
            with open(r"C:\ssbubble\sequence.txt", "r") as f:
                raw_sequence = f.readlines()

                # Check if the sequence file is empty
                if not raw_sequence:
                    self.logger.error("Sequence file is empty")
                    return False

                # Get the save path from the second line of the sequence file
                seq_save_path = raw_sequence[1].strip()
                sequence_string = raw_sequence[0].strip()
                i = 0

                # Check for capital 'M' in the sequence string
                self.motor_flag = False
                if 'M' in sequence_string:
                    self.motor_flag = True
                    sequence_string = sequence_string.replace(
                        'M', '')  # Remove 'M' from the sequence string

                if self.motor_flag:
                    try:
                        if not self.motor_worker.running or not self.motor_calibrated:
                            self.logger.error(
                                "Sequence requires motor, but motor is not ready")
                            return False
                    except Exception as e:
                        self.logger.error(
                            "Sequence requires motor, but motor is not ready")
                        return False

                # Parse the sequence string
                while i < len(sequence_string):
                    # Check for valid step types
                    if sequence_string[i] in self.step_types.keys():
                        step_type = sequence_string[i]
                    else:
                        self.logger.error("Invalid step type in sequence file")
                        return False

                    # Get the time length of the step
                    i += 1
                    time_length = ""
                    while i < len(sequence_string) and sequence_string[i].isdigit():
                        time_length += sequence_string[i]
                        i += 1
                    try:
                        time_length = int(time_length)
                    except ValueError:
                        self.logger.error(
                            "Invalid time length in sequence file")
                        return False
                    if time_length <= 0:
                        self.logger.error(
                            "Invalid time length in sequence file")
                        return False

                    # Get motor position if motor_flag is True
                    motor_position = 0
                    if self.motor_flag and i < len(sequence_string) and sequence_string[i] == 'm':
                        i += 1
                        motor_position_str = ""
                        # Check for negative sign
                        is_negative = False
                        if i < len(sequence_string) and sequence_string[i] == '-':
                            is_negative = True
                            i += 1

                        # Collect digits and decimal point for float values
                        decimal_found = False
                        while i < len(sequence_string) and (sequence_string[i].isdigit() or 
                              (sequence_string[i] == '.' and not decimal_found)):
                            if sequence_string[i] == '.':
                                decimal_found = True
                            motor_position_str += sequence_string[i]
                            i += 1
                        try:
                            motor_position = float(motor_position_str)
                            if is_negative:
                                motor_position = -motor_position
                                negative_positions_found = True
                                motor_position = 0  # Default to home position
                        except ValueError:
                            self.logger.error(
                                "Invalid motor position in sequence file")
                            return False

                    # Create a step object and add it to the list
                    step = Step(step_type, time_length, motor_position)
                    self.steps.append(step)

                # Log warning if negative positions were found
                if negative_positions_found:
                    self.logger.warning(
                        "Negative motor positions found in sequence. These have been defaulted to 0 (home position)")

                # Automatically start saving at sequence start
                if not self.saving:
                    # Get the save path from the sequence file
                    if len(seq_save_path) > 1:    # Look for save path in second line of sequence file
                        if seq_save_path.endswith('.csv'):
                            self.savePathEdit.setText(seq_save_path)
                        else:   # Add timestamped csv to the file path if no file specified
                            self.savePathEdit.setText(os.path.join(
                                seq_save_path, f"pressure_data_{time.strftime('%m%d-%H%M')}.csv").replace("/", "\\"))
                    else:
                        # If no save path is specified, use the default path
                        self.savePathEdit.setText(
                            os.path.join(self.default_save_path, f"pressure_data_{time.strftime('%m%d-%H%M')}.csv").replace("/", "\\"))

                    # Simulate save button click
                    # This will trigger the slot with the correct checked state
                    # Actually start the recording
                    self.on_beginSaveButton_clicked(True)

            return True

        except FileNotFoundError:
            self.logger.error("Sequence file not found")
            return False
        except IOError as e:
            self.logger.error(f"Error reading sequence file: {e}")
            return False

    def load_macro_labels(self):
        """Load and set macro button labels from JSON files."""
        try:
            # Load valve macro labels
            for i in range(1, 5):
                macro = self.load_valve_macro(i)
                if macro:
                    button = getattr(self, f"valveMacro{i}Button")
                    button.setText(macro.get("Label", f"Macro {i}"))
                    button.setToolTip(macro.get("Description", ""))

            # Load motor macro labels
            for i in range(1, 7):
                macro = self.load_motor_macro(i)
                if macro:
                    button = getattr(self, f"motor_macro{i}_button")
                    button.setText(macro.get("Label", f"Macro {i}"))
                    button.setToolTip(macro.get("Description", ""))

        except Exception as e:
            self.logger.error(f"Error loading macro labels: {e}")

    def on_arduino_connection_changed(self, connected: bool):
        """Handle Arduino connection state changes."""
        if connected:
            self.arduino_connect_btn.setText("Disconnect")
            self.arduino_warning_label.setText("")
            # Only enable controls if in manual mode
            self.disable_valve_controls(
                not self.arduino_manual_radio.isChecked())
        else:
            self.arduino_connect_btn.setText("Connect")
            if not self.test_mode:
                self.arduino_warning_label.setText(
                    "Warning: Arduino not connected")
            # Disable all controls when disconnected
            self.disable_valve_controls(True)

    def on_arduino_mode_changed(self):
        """Handle Arduino mode changes."""
        # Disable controls if not in manual mode
        self.disable_valve_controls(not self.arduino_manual_radio.isChecked())

    def handle_sequence_file(self, success: bool):
        """Handle sequence file cleanup after processing.

        Args:
            success: Whether sequence processing was successful
        """
        sequence_path = Path(r"C:\ssbubble\sequence.txt")
        prospa_path = Path(r"C:\ssbubble\prospa.txt")

        try:
            # Write status to Prospa
            with open(prospa_path, 'w') as f:
                f.write('1' if success else '0')

            # Delete sequence file only if not in test mode
            if success and not self.test_mode:
                sequence_path.unlink()
                self.logger.info("Sequence file processed and deleted")
            elif success and self.test_mode:
                self.logger.info(
                    "Test mode: Sequence file processed but preserved")
            else:
                self.logger.error("Failed to process sequence file")

        except Exception as e:
            self.logger.error(f"Error handling sequence file cleanup: {e}")

    def update_step_time(self):
        """Update the time remaining display for current step and total sequence."""
        try:
            if self.steps and len(self.steps) > 0:
                # Calculate current step time remaining
                elapsed = int((time.time() - self.step_start_time)
                              * 1000)  # Convert to ms
                step_remaining = max(0, self.steps[0].time_length - elapsed)

                # Calculate total time remaining
                total_remaining = step_remaining  # Start with current step remaining
                for step in self.steps[1:]:
                    total_remaining += step.time_length

                # Update UI with remaining times
                self.update_sequence_info(
                    step_type=self.step_types[self.steps[0].step_type],
                    step_time=step_remaining / 1000,  # Convert to seconds for display
                    steps_left=len(self.steps),
                    total_time=total_remaining / 1000  # Convert to seconds
                )
        except Exception as e:
            self.logger.error(f"Error updating step time: {e}")

    def next_step(self):
        """Execute the next step in the sequence."""
        try:
            # Remove completed step
            self.steps.pop(0)

            if self.steps:
                # Execute next step
                self.execute_step(self.steps[0])
                # Reset step timer and schedule next step
                self.step_start_time = time.time()
                QTimer.singleShot(self.steps[0].time_length, self.next_step)
            else:
                # Sequence complete
                self.step_timer.stop()
                # Disable sequence mode when complete
                if self.motor_flag and self.motor_worker.running:
                    self.motor_worker.set_sequence_mode(False)
                
                # Update UI and handle completion
                self.update_sequence_info("Complete", 0, 0, 0)
                self.update_sequence_status("Complete")
                
                # Stop data recording if active
                if self.saving:
                    self.plot_widget.stop_recording()
                    self.beginSaveButton.setText("Begin Saving")
                    self.beginSaveButton.setChecked(False)
                    self.saving = False
                    self.logger.info("Data recording stopped with sequence completion")

                self.logger.info("Sequence execution completed")

        except Exception as e:
            self.logger.error(f"Error in sequence execution: {e}")
            self.handle_error("Failed to execute sequence")
            # Disable sequence mode on error
            if self.motor_flag and self.motor_worker.running:
                self.motor_worker.set_sequence_mode(False)

    def execute_step(self, step):
        """Execute a single sequence step."""
        try:
            # Set valve states based on step type
            valve_states = [0] * 8  # Initialize all valves closed

            if step.step_type == 'p':  # Pressurize
                valve_states[1] = 1  # Open inlet valve
            elif step.step_type == 'v':  # Vent
                valve_states[3] = 1  # Open vent valve
            elif step.step_type == 'b':  # Bubble
                valve_states[1] = 1  # Open inlet valve
                valve_states[2] = 1  # Open outlet valve
            elif step.step_type == 'f':  # Flow
                valve_states[2] = 1  # Open outlet valve
            elif step.step_type == 'e':  # Evacuate
                valve_states[3] = 1  # Open vent valve
                valve_states[4] = 1  # Open short valve

            # Set valve states
            self.arduino_worker.set_valves(valve_states)

            # Move motor if required
            if self.motor_flag and step.motor_position is not None:
                self.motor_worker.move_to(step.motor_position)

            self.logger.info(f"Executing step: {self.step_types[step.step_type]}")

        except Exception as e:
            self.logger.error(f"Error executing step: {e}")
            self.handle_error("Failed to execute sequence step")

    def disable_other_valve_controls(self, active_macro_num: int):
        """Disable all valve controls except the active macro button.
        
        Args:
            active_macro_num: Number of the active macro button (1-4)
        """
        # Disable individual valve buttons
        for i in range(1, 6):
            valve_button = getattr(self, f"Valve{i}Button")
            valve_button.setEnabled(False)

        # Disable other macro buttons
        for i in range(1, 5):
            if i != active_macro_num:
                macro_button = getattr(self, f"valveMacro{i}Button")
                macro_button.setEnabled(False)

        # Disable quick action buttons
        self.quickBubbleButton.setEnabled(False)
        self.switchGasButton.setEnabled(False)
        self.buildPressureButton.setEnabled(False)
        self.quickVentButton.setEnabled(False)
        self.slowVentButton.setEnabled(False)

    def enable_all_valve_controls(self):
        """Re-enable all valve controls."""
        # Only enable if in manual mode and Arduino is connected
        if self.arduino_worker.running and self.arduino_manual_radio.isChecked():
            # Enable individual valve buttons
            for i in range(1, 6):
                valve_button = getattr(self, f"Valve{i}Button")
                valve_button.setEnabled(True)

            # Enable macro buttons
            for i in range(1, 5):
                macro_button = getattr(self, f"valveMacro{i}Button")
                macro_button.setEnabled(True)

            # Enable quick action buttons
            self.quickBubbleButton.setEnabled(True)
            self.switchGasButton.setEnabled(True)
            self.buildPressureButton.setEnabled(True)
            self.quickVentButton.setEnabled(True)
            self.slowVentButton.setEnabled(True)

    def start_motor_sequence(self):
        """Load and start a motor-only sequence from CSV."""
        try:
            # Check if motor is connected and calibrated
            if not self.motor_worker.running:
                self.handle_error("Motor not connected")
                return
                
            if not self.motor_worker.controller.check_calibrated():
                self.handle_error("Motor must be calibrated before starting sequence")
                return

            # Load sequence from CSV - updated path
            sequence_path = Path(r"C:\ssbubble\motor_sequence.csv")
            if not sequence_path.exists():
                self.handle_error("Motor sequence file not found")
                return

            # Read CSV file
            motor_steps = []
            with open(sequence_path, 'r') as f:
                csv_reader = csv.reader(f)
                for row in csv_reader:
                    try:
                        position = float(row[0])
                        time_ms = int(float(row[1]) * 1000)  # Convert to milliseconds
                        motor_steps.append((position, time_ms))
                    except (ValueError, IndexError) as e:
                        self.logger.error(f"Invalid row in sequence file: {row}")
                        self.handle_error("Invalid motor sequence file format")
                        return

            if not motor_steps:
                self.handle_error("No valid steps found in sequence file")
                return

            # Enable sequence mode
            self.motor_worker.set_sequence_mode(True)
            self.logger.info("Starting motor-only sequence")

            # Execute first step
            self.execute_motor_step(motor_steps[0])
            
            # Schedule subsequent steps
            def schedule_next_step(step_index):
                if step_index < len(motor_steps):
                    QTimer.singleShot(motor_steps[step_index-1][1], 
                                    lambda: self.execute_motor_step(motor_steps[step_index], 
                                    lambda: schedule_next_step(step_index + 1)))

            schedule_next_step(1)

        except Exception as e:
            self.logger.error(f"Error starting motor sequence: {e}")
            self.handle_error(f"Failed to start motor sequence: {str(e)}")
            self.motor_worker.set_sequence_mode(False)

    def execute_motor_step(self, step, callback=None):
        """Execute a single motor sequence step.
        
        Args:
            step: Tuple of (position, time_ms)
            callback: Optional callback function to execute after movement starts
        """
        try:
            position, _ = step
            self.logger.info(f"Moving to position: {position}")
            success = self.motor_worker.move_to(position)
            
            if success and callback:
                callback()
            elif not success:
                self.logger.error("Failed to execute motor movement")
                self.motor_worker.set_sequence_mode(False)
                
        except Exception as e:
            self.logger.error(f"Error executing motor step: {e}")
            self.motor_worker.set_sequence_mode(False)
