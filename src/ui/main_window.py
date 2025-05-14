"""
File: main_window.py
Description: Main application window implementation
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QGroupBox, QMenuBar,
    QStatusBar, QMessageBox, QButtonGroup, QRadioButton, QFrame,
    QStackedWidget, QCheckBox, QLineEdit, QDoubleSpinBox, QSizePolicy,
    QFileDialog, QFormLayout, QComboBox, QDialog, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize, QRect, QMetaObject, Q_ARG, QCoreApplication
from PyQt6.QtGui import QFont
from datetime import datetime
import logging
from typing import List, Optional, Union
from pathlib import Path
import time
import json
import os

from utils.config import Config
from utils.timing_logger import setup_timing_logger, get_timing_logger  # Add import
from utils.logger import shutdown_logging
from workers.arduino_worker import ArduinoWorker
from workers.motor_worker import MotorWorker
from .widgets.plot_widget import PlotWidget
from .widgets.log_widget import LogWidget
from .dialogs.valve_macro_editor import ValveMacroEditor
from .dialogs.motor_macro_editor import MotorMacroEditor
from .dialogs.dev_panel import DevPanel
from utils.config_manager import ConfigManager


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
        'w': 'Wait',
        'f': 'Default',
        'v': 'Slow Vent',
        'b': 'Bubble',
        'd': 'Close All',
        'p': 'Pressurise',
        'c': 'Cleanup',
        'q': 'Quick Vent',
        'g': 'Set Gas pH2',
        'h': 'Set Gas H2',
        'n': 'Set Gas N2',
    }

    def __init__(self, test_mode=False, keep_sequence=False, timing_mode=False, args=None):
        """Initialize the main window."""
        super().__init__()

        # Store command line args
        self.args = args

        # Reset motor worker instance count at startup
        MotorWorker.reset_instance_count()

        # Load configuration
        self.config = Config()
        self.test_mode = test_mode
        self.keep_sequence = keep_sequence
        self.timing_mode = timing_mode  # Store timing mode flag

        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing MainWindow with test_mode={test_mode}")

        # Clean up old files
        try:
            ssbubble_path = Path("C:/ssbubble")
            files_to_delete = [
                "sequence.txt",
                "prospa.txt",
                "device_status.txt",
                "sequence_finish_time.txt"
            ]
            for filename in files_to_delete:
                file_path = ssbubble_path / filename
                if file_path.exists():
                    file_path.unlink()
                    self.logger.info(f"Deleted {filename}")
        except Exception as e:
            self.logger.error(f"Error cleaning up files: {e}")

        # Initialize workers as None
        self.motor_worker = None
        self.arduino_worker = None
        self.logger.info("Workers initialized as None")

        # Initialize device status file
        try:
            status_path = Path("C:/ssbubble/device_status.txt")
            status_path.parent.mkdir(parents=True, exist_ok=True)
            with open(status_path, 'w') as f:
                f.write("00")  # Both devices initially disconnected
        except Exception as e:
            self.logger.error(f"Failed to initialize device status file: {e}")

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

        # Add previous save path tracking
        self.prev_save_path = None

        # Setup timing logger
        self.timing_logger = setup_timing_logger(timing_mode)

        self.config_manager = ConfigManager()

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
        self.motor_com_port_spin.setRange(1, 255)
        self.motor_com_port_spin.setValue(
            self.config.motor_port)  # Use config value
        self.motor_com_port_spin.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        self.motor_com_port_spin.valueChanged.connect(
            self.update_motor_port)  # Add connection
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

        # Modify STOP button height
        self.motor_stop_btn = QPushButton("STOP")
        self.motor_stop_btn.setMinimumSize(
            QSize(0, 50))  # Reduced from 90 to 50
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.motor_stop_btn.setFont(font)
        self.motor_stop_btn.setStyleSheet(
            "background-color: red; color: white;")
        motor_layout.addWidget(self.motor_stop_btn)

        # Add speed control combo box
        self.motor_speed_combo = QComboBox()
        self.motor_speed_combo.addItems(['Fast', 'Medium', 'Slow'])
        self.motor_speed_combo.setCurrentText(
            'Medium')  # Default to medium speed
        font = QFont()
        font.setPointSize(11)
        self.motor_speed_combo.setFont(font)
        self.motor_speed_combo.currentTextChanged.connect(
            self.on_motor_speed_changed)
        self.motor_speed_combo.setEnabled(False)  # Initially disabled
        motor_layout.addWidget(self.motor_speed_combo)

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

        # Add speed combo box control
        if hasattr(self, 'motor_speed_combo'):
            self.motor_speed_combo.setEnabled(
                not disabled and self.motor_calibrated)

        # Motor macro buttons
        if hasattr(self, 'motor_to_top_button'):
            self.motor_to_top_button.setEnabled(
                not disabled and self.motor_calibrated)
            self.motor_to_bottom_button.setEnabled(
                not disabled and self.motor_calibrated)

            # Macro buttons 1-6
            for i in range(1, 7):
                btn = getattr(self, f"motor_macro{i}_button", None)
                if btn:
                    btn.setEnabled(not disabled and self.motor_calibrated)

    def setup_valve_section(self, layout):
        """Setup valve controls with switchable views."""
        valve_group = QGroupBox()
        # May need to adjust height to fit extra button
        valve_group.setFixedSize(96, 294)
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
        """Reset valves to default state, preserving inlet/outlet valves."""
        try:
            if self.arduino_worker and self.arduino_worker.running:
                # Get current valve states
                current_valve_states = [0] * 8
                try:
                    if hasattr(self.arduino_worker, 'get_valve_states'):
                        current_valve_states = self.arduino_worker.get_valve_states()
                except Exception as e:
                    self.logger.warning(
                        f"Could not get current valve states: {e}")

                # Create new valve states, preserving first two valves
                valve_states = current_valve_states.copy()
                # Reset valves 3-8 to closed
                for i in range(2, 8):
                    valve_states[i] = 0

                # Send valve states to Arduino
                self.arduino_worker.set_valves(valve_states)
                self.logger.info(f"Reset valves: {valve_states}")

                # Update valve button states
                for i in range(2, 6):  # Only update buttons for valves 3-6
                    valve_button = getattr(self, f"Valve{i+1}Button")
                    valve_button.setChecked(False)

                # Reset macro buttons
                for i in range(1, 5):
                    macro_button = getattr(self, f"valveMacro{i}Button")
                    macro_button.setChecked(False)

                self.active_valve_macro = None

        except Exception as e:
            self.logger.error(f"Error resetting valves: {e}")

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

        enum_pressure_sensors = ["Rig", "Inlet", "Tube", "Outlet"]
        # Create pressure radio buttons
        for i in range(1, 5):
            radio = QRadioButton(enum_pressure_sensors[i-1])
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

        self.bubbleTimeDoubleSpinBox = QDoubleSpinBox()
        self.bubbleTimeDoubleSpinBox.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        self.bubbleTimeDoubleSpinBox.setMinimum(0.0)
        self.bubbleTimeDoubleSpinBox.setValue(5.00)
        self.bubbleTimeDoubleSpinBox.setSuffix(" s")  # Add suffix for seconds
        monitor_layout.addWidget(self.bubbleTimeDoubleSpinBox, 4, 1, 1, 1)

        self.quickBubbleButton = QPushButton("Quick Bubble")
        self.quickBubbleButton.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.quickBubbleButton.setFont(font)
        self.quickBubbleButton.setCheckable(True)
        monitor_layout.addWidget(self.quickBubbleButton, 4, 0, 1, 1)

        self.switchGas1Button = QPushButton("Switch pH2")
        self.switchGas1Button.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.switchGas1Button.setFont(font)
        self.switchGas1Button.setCheckable(True)
        monitor_layout.addWidget(self.switchGas1Button, 5, 0, 1, 1)

        self.switchGas2Button = QPushButton("Switch H2")
        self.switchGas2Button.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.switchGas2Button.setFont(font)
        self.switchGas2Button.setCheckable(True)
        monitor_layout.addWidget(self.switchGas2Button, 5, 1, 1, 1)

        self.switchGas3Button = QPushButton("Switch N2")
        self.switchGas3Button.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setPointSize(10)
        self.switchGas3Button.setFont(font)
        self.switchGas3Button.setCheckable(True)
        monitor_layout.addWidget(self.switchGas3Button, 6, 0, 1, 1)

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

        # Replace ascent button with to bottom button
        self.motor_to_bottom_button = QPushButton("To Bottom")
        self.motor_to_bottom_button.setMinimumSize(QSize(0, 35))
        font = QFont()
        font.setPointSize(10)
        self.motor_to_bottom_button.setFont(font)
        motor_macro_layout.addWidget(self.motor_to_bottom_button, 0, 1, 1, 1)

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
        """Setup application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        valve_macro_action = tools_menu.addAction("Valve Macros")
        valve_macro_action.triggered.connect(self.edit_macros)
        motor_macro_action = tools_menu.addAction("Motor Macros")
        motor_macro_action.triggered.connect(self.edit_macros)

        # Dev menu
        dev_menu = menubar.addMenu("Dev")
        open_dev_panel_action = dev_menu.addAction("Open Dev Panel")
        open_dev_panel_action.triggered.connect(self.show_dev_panel)

    def show_dev_panel(self):
        """Show the developer panel if password is correct."""
        password, ok = QInputDialog.getText(
            self,
            "Developer Access",
            "Enter developer password:",
            QLineEdit.EchoMode.Password
        )

        if ok and password == self.config.dev_password:
            dev_panel = DevPanel(self)
            dev_panel.setWindowModality(
                Qt.WindowModality.NonModal)  # Make non-modal
            dev_panel.show()  # Use show() instead of exec()
        elif ok:  # Wrong password
            QMessageBox.warning(self, "Access Denied",
                                "Invalid developer password")

    def setup_status_bar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")

    def setup_connections(self):
        """Set up signal-slot connections."""
        if self._connections_initialized:
            return

        try:
            # First disconnect any existing connections to prevent duplicates
            try:
                # Only try to disconnect motor worker signals if it exists
                if self.motor_worker:
                    self.motor_worker.position_updated.disconnect()
                    self.motor_worker.error_occurred.disconnect()
                    self.motor_worker.status_changed.disconnect()
                    self.motor_worker.calibration_state_changed.disconnect()

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
                self.quickBubbleButton.clicked.disconnect()
                self.switchGas1Button.clicked.disconnect()
                self.switchGas2Button.clicked.disconnect()
                self.switchGas3Button.clicked.disconnect()
                self.buildPressureButton.clicked.disconnect()
                self.quickVentButton.clicked.disconnect()
                self.slowVentButton.clicked.disconnect()

                # Motor control buttons
                self.motor_connect_btn.clicked.disconnect()
                self.motor_calibrate_btn.clicked.disconnect()
                self.motor_stop_btn.clicked.disconnect()
                self.motor_move_to_target_button.clicked.disconnect()
                self.motor_to_bottom_button.clicked.disconnect()
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
            # Worker signal connections for Arduino are now handled in ArduinoWorker.__init__

            # Motor worker connections are set up when the worker is created

            # Arduino and valve connections
            self.arduino_connect_btn.clicked.connect(
                self.on_ardConnectButton_clicked)

            # Valve buttons
            self.connect_valve_buttons()

            # Quick action buttons
            self.quickBubbleButton.clicked.connect(
                self.on_quickBubbleButton_clicked)
            self.slowVentButton.clicked.connect(self.on_slowVentButton_clicked)
            self.quickVentButton.clicked.connect(
                self.on_quickVentButton_clicked)
            self.buildPressureButton.clicked.connect(
                self.on_buildPressureButton_clicked)
            self.switchGas1Button.clicked.connect(
                self.on_switchGas1Button_clicked)
            self.switchGas2Button.clicked.connect(
                self.on_switchGas2Button_clicked)
            self.switchGas3Button.clicked.connect(
                self.on_switchGas3Button_clicked)

            # Motor control buttons
            self.motor_connect_btn.clicked.connect(
                self.handle_motor_connection)
            self.motor_calibrate_btn.clicked.connect(
                self.on_motorCalibrateButton_clicked)
            self.motor_stop_btn.clicked.connect(
                self.on_motorStopButton_clicked)
            self.motor_move_to_target_button.clicked.connect(
                self.on_motorMoveToTargetButton_clicked)
            self.motor_to_bottom_button.clicked.connect(
                self.on_motorToBottomButton_clicked)
            self.motor_to_top_button.clicked.connect(
                self.on_motorToTopButton_clicked)

            # Motor macro buttons
            for i in range(1, 7):
                btn = getattr(self, f"motor_macro{i}_button")
                btn.clicked.connect(
                    lambda checked, x=i: self.on_motorMacroButton_clicked(x))

            # Valve macro buttons
            for i in range(1, 5):
                btn = getattr(self, f"valveMacro{i}Button")
                btn.clicked.connect(
                    lambda checked, x=i: self.on_valveMacroButton_clicked(x))

            # Pressure radio buttons
            for i in range(1, 5):
                radio = getattr(self, f"pressure{i}RadioButton")
                radio.clicked.connect(
                    lambda checked, x=i: self.on_pressureRadioButton_clicked(x))

            # Connect mode change signals
            self.arduino_connect_button_group.buttonClicked.connect(
                self.on_arduino_mode_changed)

            # Connect motor worker signals
            if self.motor_worker:
                self.motor_worker.position_updated.connect(
                    self._update_motor_position)
                self.motor_worker.error_occurred.connect(
                    self._handle_motor_error)
                self.motor_worker.status_changed.connect(
                    self._update_motor_status)
                self.motor_worker.calibration_state_changed.connect(
                    self._update_calibration_state)
                self.motor_worker.critical_error_occurred.connect(
                    self.handle_critical_motor_error)

                # Make sure position_reached signal is connected
                if hasattr(self.motor_worker, 'position_reached'):
                    self.motor_worker.position_reached.connect(
                        self._handle_position_reached)

            self._connections_initialized = True

        except Exception as e:
            self.logger.error(f"Error setting up connections: {e}")
            raise

    def connect_valve_buttons(self):
        """Connect valve button signals using a dedicated method."""
        self.Valve1Button.clicked.connect(self.on_Valve1Button_clicked)
        self.Valve2Button.clicked.connect(self.on_Valve2Button_clicked)
        self.Valve3Button.clicked.connect(self.on_Valve3Button_clicked)
        self.Valve4Button.clicked.connect(self.on_Valve4Button_clicked)
        self.Valve5Button.clicked.connect(self.on_Valve5Button_clicked)
        self.Valve6Button.clicked.connect(
            self.on_Valve6Button_clicked)  # Add connection for 6th valve

    @pyqtSlot()
    def handle_motor_connection(self):
        """Handle motor connection/disconnection."""
        try:
            if not self.motor_worker or not self.motor_worker.running:
                # Create new worker when connecting
                port = self.motor_com_port_spin.value()
                self.motor_worker = MotorWorker(
                    port=port,
                    update_interval=self.config.motor_update_interval,
                    mock=self.test_mode,
                    timing_mode=self.timing_mode  # Pass timing mode to worker
                )

                # Setup connections for new worker
                self.motor_worker.position_updated.connect(
                    self.handle_position_update)
                self.motor_worker.error_occurred.connect(self.handle_error)
                self.motor_worker.status_changed.connect(
                    self.handle_status_message)
                self.motor_worker.calibration_state_changed.connect(
                    self.handle_calibration_state_changed)

                # Start the worker
                if self.motor_worker.start():
                    self.motor_connect_btn.setText("Disconnect")
                    self.motor_warning_label.setText("")
                    self.motor_warning_label.setVisible(False)
                    self.motor_calibrate_btn.setEnabled(True)
                    self.disable_motor_controls(True)
                    self.logger.info(f"Connected to motor on COM{port}")
                    self.update_device_status()
                else:
                    self.cleanup_motor_worker()
                    self.handle_error("Failed to connect to motor")
                    self.motor_warning_label.setText(
                        "Warning: Motor not connected")
                    self.motor_calibrate_btn.setEnabled(False)
                    self.disable_motor_controls(True)
            else:
                # Disconnect and cleanup worker
                self.cleanup_motor_timers()  # Add this line to clean up timers
                self.cleanup_motor_worker()
                self.motor_connect_btn.setText("Connect")
                self.motor_calibrated = False
                self.motor_warning_label.setText(
                    "Warning: Motor not connected")
                self.motor_warning_label.setVisible(True)
                self.motor_calibrate_btn.setEnabled(False)
                self.disable_motor_controls(True)
                self.logger.info("Disconnected from motor")
                self.update_device_status()

        except Exception as e:
            self.logger.error(f"Error in motor connection handler: {e}")
            self.handle_error(f"Motor connection error: {str(e)}")
            self.cleanup_motor_worker()

    def cleanup_motor_worker(self):
        """Clean up motor worker resources."""
        try:
            if self.motor_worker:
                # First, stop any active timers in the worker
                if hasattr(self.motor_worker, '_calibration_check_timer') and self.motor_worker._calibration_check_timer:
                    self.motor_worker._calibration_check_timer.stop()

                # Disconnect all signals from the worker - use try/except for each
                try:
                    if hasattr(self.motor_worker, 'position_updated'):
                        try:
                            self.motor_worker.position_updated.disconnect()
                        except TypeError:
                            pass  # Signal wasn't connected
                except Exception as e:
                    self.logger.warning(
                        f"Error disconnecting position_updated signal: {e}")

                try:
                    if hasattr(self.motor_worker, 'error_occurred'):
                        try:
                            self.motor_worker.error_occurred.disconnect()
                        except TypeError:
                            pass
                except Exception as e:
                    self.logger.warning(
                        f"Error disconnecting error_occurred signal: {e}")

                try:
                    if hasattr(self.motor_worker, 'status_changed'):
                        try:
                            self.motor_worker.status_changed.disconnect()
                        except TypeError:
                            pass
                except Exception as e:
                    self.logger.warning(
                        f"Error disconnecting status_changed signal: {e}")

                try:
                    if hasattr(self.motor_worker, 'calibration_state_changed'):
                        try:
                            self.motor_worker.calibration_state_changed.disconnect()
                        except TypeError:
                            pass
                except Exception as e:
                    self.logger.warning(
                        f"Error disconnecting calibration_state_changed signal: {e}")

                try:
                    if hasattr(self.motor_worker, 'position_reached'):
                        try:
                            self.motor_worker.position_reached.disconnect()
                        except TypeError:
                            pass
                except Exception as e:
                    self.logger.warning(
                        f"Error disconnecting position_reached signal: {e}")

                try:
                    if hasattr(self.motor_worker, 'movement_completed'):
                        try:
                            self.motor_worker.movement_completed.disconnect()
                        except TypeError:
                            pass
                except Exception as e:
                    self.logger.warning(
                        f"Error disconnecting movement_completed signal: {e}")

                # Properly stop the worker thread
                self.motor_worker.cleanup()

                # Wait for thread to finish (with timeout)
                if not self.motor_worker.wait(1000):  # 1 second timeout
                    self.logger.warning(
                        "Motor worker thread did not terminate gracefully, forcing termination")
                    self.motor_worker.terminate()

                self.motor_worker = None
        except Exception as e:
            self.logger.error(f"Error cleaning up motor worker: {e}")

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
            if not hasattr(self, 'attempt'):
                self.attempt = 0
            if not hasattr(self, 'sequence_start_time'):
                self.sequence_start_time = 0
            self.file_timer = QTimer()
            self.file_timer.timeout.connect(self.check_sequence_file)
            self.file_timer.start(100)  # Check every 100ms
        except Exception as e:
            self.logger.error(f"Error setting up sequence file timer: {e}")
            self.handle_error("Failed to start sequence file monitoring")

    def check_sequence_file(self):
        """Check for and process sequence file."""
        try:
            sequence_path = Path(r"C:\ssbubble\sequence.txt")
            if sequence_path.exists():
                # Process in chunks to avoid blocking
                def process_sequence():
                    try:
                        success = self.load_sequence()
                        if success:
                            # Check if devices are connected
                            if not self.arduino_worker:
                                self.logger.error(
                                    "Arduino not connected, sequence cancelled")
                                return
                            if (not self.motor_worker and self.motor_flag):
                                self.logger.error(
                                    "Motor not connected, sequence cancelled")
                                return

                            # Set sequence start time
                            self.sequence_start_time = time.time()

                            # Call start_sequence directly
                            self.start_sequence()

                            # Stop sequence file timer
                            self.file_timer.stop()

                            # Delete sequence file after processing
                            self.handle_sequence_file(True)

                            # Calculate sequence time
                            self.calculate_sequence_time()

                            # Update UI with first step
                            if self.steps:
                                QMetaObject.invokeMethod(self, "update_sequence_info",
                                                         Qt.ConnectionType.QueuedConnection,
                                                         Q_ARG(
                                                             str, self.step_types[self.steps[0].step_type]),
                                                         Q_ARG(
                                                             float, self.steps[0].time_length),
                                                         Q_ARG(
                                                             int, len(self.steps)),
                                                         Q_ARG(float, self.total_sequence_time))

                            if not self.write_sequence_finish_time(
                                    self.total_sequence_time):
                                self.logger.error(
                                    "Failed to write sequence finish time")

                        else:
                            self.handle_sequence_file(False)
                            self.logger.error(
                                "Sequence file could not be loaded")
                    except Exception as e:
                        self.logger.error(f"Error processing sequence: {e}")

                # Process sequence in a separate thread to avoid blocking
                QTimer.singleShot(0, process_sequence)

            else:
                if self.attempt % 10 == 0:
                    self.attempt = 0
                    self.logger.info("Sequence file not found")
                self.attempt += 1

        except Exception as e:
            self.logger.error(f"Error in sequence file check: {e}")
            self.handle_error(f"Sequence file check failed: {str(e)}")

    def write_sequence_finish_time(self, sequence_time: float):
        """Write sequence finish time to file.

        Args:
            sequence_time: Total sequence time in milliseconds
        """
        try:
            # Get start time - use delayed start time if exists, otherwise use current time
            if hasattr(self, 'sequence_start_delay') and self.sequence_start_delay != None:
                start_time = self.sequence_start_delay.timestamp()
            else:
                start_time = time.time()

            # Calculate end time by adding sequence duration
            end_datetime = datetime.fromtimestamp(
                start_time + (sequence_time / 1000))

            # Format end time as required
            end_time = f"[{end_datetime.year}, {end_datetime.month:02d}, {end_datetime.day:02d}, {end_datetime.hour:02d}, {end_datetime.minute:02d}, {end_datetime.second:02d}, {int(end_datetime.microsecond)}]"

            # Write to file
            with open(r"C:\ssbubble\sequence_finish_time.txt", "w") as f:
                f.write(f"{end_time}")

            self.logger.info(f"Sequence finish time: {end_time}")
            return True

        except Exception as e:
            self.logger.error(f"Error writing sequence finish time: {e}")
            return False

    @pyqtSlot()
    def _update_arduino_disconnect_state(self):
        """Update UI elements when Arduino disconnects. This method runs in the main thread."""
        self.arduino_connect_btn.setText("Connect")
        if not self.test_mode:
            self.arduino_warning_label.setText(
                "Warning: Arduino not connected")
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
        """
        try:
            Path(r"C:\ssbubble\sequence.txt").unlink(missing_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to delete sequence file: {e}")
        """
        pass

    @pyqtSlot(bool)
    def on_Valve1Button_clicked(self, checked: bool):
        """Handle Valve 1 (Switch valve) button click."""
        if self.arduino_worker and self.arduino_worker.running:
            try:
                # Get current valve states
                current_states = [2] * 8
                if hasattr(self.arduino_worker, 'get_valve_states'):
                    current_states = self.arduino_worker.get_valve_states()

                # Only update the state of valve 1
                current_states[0] = 1 if checked else 0

                # Send updated states to Arduino
                self.arduino_worker.set_valves(current_states)
                self.logger.info(
                    f"Valve 1 {'opened' if checked else 'closed'}")
            except Exception as e:
                self.logger.error(f"Error controlling Valve 1: {e}")

    @pyqtSlot(bool)
    def on_Valve2Button_clicked(self, checked: bool):
        """Handle Valve 2 (Inlet valve) button click."""
        if self.arduino_worker and self.arduino_worker.running:
            try:
                # Get current valve states
                current_states = [2] * 8
                if hasattr(self.arduino_worker, 'get_valve_states'):
                    current_states = self.arduino_worker.get_valve_states()

                # Only update the state of valve 2
                current_states[1] = 1 if checked else 0

                # Send updated states to Arduino
                self.arduino_worker.set_valves(current_states)
                self.logger.info(
                    f"Valve 2 {'opened' if checked else 'closed'}")
            except Exception as e:
                self.logger.error(f"Error controlling Valve 2: {e}")

    @pyqtSlot(bool)
    def on_Valve3Button_clicked(self, checked: bool):
        """Handle Valve 3 (Outlet valve) button click."""
        if self.arduino_worker and self.arduino_worker.running:
            try:
                # Get current valve states
                current_states = [2] * 8
                if hasattr(self.arduino_worker, 'get_valve_states'):
                    current_states = self.arduino_worker.get_valve_states()

                # Only update the state of valve 3
                current_states[2] = 1 if checked else 0

                # Send updated states to Arduino
                self.arduino_worker.set_valves(current_states)
                self.logger.info(
                    f"Valve 3 {'opened' if checked else 'closed'}")
            except Exception as e:
                self.logger.error(f"Error controlling Valve 3: {e}")

    @pyqtSlot(bool)
    def on_Valve4Button_clicked(self, checked: bool):
        """Handle Valve 4 (Vent valve) button click."""
        if self.arduino_worker and self.arduino_worker.running:
            try:
                # Get current valve states
                current_states = [2] * 8
                if hasattr(self.arduino_worker, 'get_valve_states'):
                    current_states = self.arduino_worker.get_valve_states()

                # Only update the state of valve 4
                current_states[3] = 1 if checked else 0

                # Send updated states to Arduino
                self.arduino_worker.set_valves(current_states)
                self.logger.info(
                    f"Valve 4 {'opened' if checked else 'closed'}")
            except Exception as e:
                self.logger.error(f"Error controlling Valve 4: {e}")

    @pyqtSlot(bool)
    def on_Valve5Button_clicked(self, checked: bool):
        """Handle Valve 5 (Short valve) button click."""
        if self.arduino_worker and self.arduino_worker.running:
            try:
                # Get current valve states
                current_states = [2] * 8
                if hasattr(self.arduino_worker, 'get_valve_states'):
                    current_states = self.arduino_worker.get_valve_states()

                # Only update the state of valve 5
                current_states[4] = 1 if checked else 0

                # Send updated states to Arduino
                self.arduino_worker.set_valves(current_states)
                self.logger.info(
                    f"Valve 5 {'opened' if checked else 'closed'}")
            except Exception as e:
                self.logger.error(f"Error controlling Valve 5: {e}")

    @pyqtSlot(bool)
    def on_Valve6Button_clicked(self, checked: bool):
        """Handle Valve 6 (Long valve) button click."""
        if self.arduino_worker and self.arduino_worker.running:
            try:
                # Get current valve states
                current_states = [0] * 8
                if hasattr(self.arduino_worker, 'get_valve_states'):
                    current_states = self.arduino_worker.get_valve_states()
                logging.info(f"Current states: {current_states}")

                # Only update the state of valve 6
                current_states[5] = 1 if checked else 0

                # Send updated states to Arduino
                self.arduino_worker.set_valves(current_states)
                self.logger.info(
                    f"Valve 6 {'opened' if checked else 'closed'}")
            except Exception as e:
                self.logger.error(f"Error controlling Valve 6: {e}")

    @pyqtSlot(bool)
    def on_quickVentButton_clicked(self, checked: bool):
        """Handle quick vent button click."""
        if not self.arduino_worker.running:
            return

        if checked:
            # Configure valves for quick venting
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[2] = 0     # Close inlet (Valve 3)
            valve_states[3] = 1     # Open outlet (Valve 4)
            valve_states[4] = 0     # Close vent (Valve 5)
            valve_states[5] = 1     # Open short (Valve 6)
            self.arduino_worker.set_valves(valve_states)

            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

            self.logger.info("Quick vent started")
        else:
            # Close valves 3-6
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[2] = 0
            valve_states[3] = 0
            valve_states[4] = 0
            valve_states[5] = 0
            self.arduino_worker.set_valves(valve_states)

            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

            self.logger.info("Quick vent stopped")

    @pyqtSlot(bool)
    def on_slowVentButton_clicked(self, checked: bool):
        """Handle slow vent button click."""
        if not self.arduino_worker.running:
            return

        if checked:
            # Configure valves for slow venting
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[2] = 0     # Close inlet (Valve 3)
            valve_states[3] = 1     # Open outlet (Valve 4)
            valve_states[4] = 1     # Open vent (Valve 5)
            valve_states[5] = 0     # Close short (Valve 6)
            self.arduino_worker.set_valves(valve_states)

            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

            self.logger.info("Slow vent started")
        else:
            # Close valves 3-6
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[2] = 0
            valve_states[3] = 0
            valve_states[4] = 0
            valve_states[5] = 0
            self.arduino_worker.set_valves(valve_states)

            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

            self.logger.info("Slow vent stopped")

    @pyqtSlot(bool)
    def on_buildPressureButton_clicked(self, checked: bool):
        """Handle build pressure button click."""
        if self.arduino_worker.running:
            valve_states = self.arduino_worker.get_valve_states()

            valve_states[2] = 1 if checked else 0  # Valve 3 (inlet)
            valve_states[3] = 0 if checked else 0  # Valve 4 (outlet)
            valve_states[4] = 0 if checked else 0  # Valve 5 (vent)
            valve_states[5] = 0 if checked else 0  # Valve 6 (short)
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(
                f"Pressure build {'started' if checked else 'stopped'}")
            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

    @pyqtSlot(bool)
    def on_switchGas1Button_clicked(self, checked: bool):
        """Handle switch gas button click."""
        if self.arduino_worker.running:
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[0] = 0
            valve_states[1] = 0
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(
                f"Gas switch {'started' if checked else 'stopped'}")
            self.switchGas1Button.setChecked(True)
            self.switchGas2Button.setChecked(False)
            self.switchGas3Button.setChecked(False)
            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

    @pyqtSlot(bool)
    def on_switchGas2Button_clicked(self, checked: bool):
        """Handle switch gas button click."""
        if self.arduino_worker.running:
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[0] = 0
            valve_states[1] = 1
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(
                f"Gas switch {'started' if checked else 'stopped'}")
            self.switchGas1Button.setChecked(False)
            self.switchGas2Button.setChecked(True)
            self.switchGas3Button.setChecked(False)
            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

    @pyqtSlot(bool)
    def on_switchGas3Button_clicked(self, checked: bool):
        """Handle switch gas button click."""
        if self.arduino_worker.running:
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[0] = 1
            valve_states[1] = 1
            self.arduino_worker.set_valves(valve_states)
            self.logger.info(
                f"Gas switch {'started' if checked else 'stopped'}")
            self.switchGas1Button.setChecked(False)
            self.switchGas2Button.setChecked(False)
            self.switchGas3Button.setChecked(True)
            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))

    def on_quickBubbleButton_clicked(self, checked: bool):
        """Handle quick bubble button click."""
        if not self.arduino_worker.running:
            return

        if checked:
            duration = self.bubbleTimeDoubleSpinBox.value()
            # Open inlet and outlet valves
            valve_states = self.arduino_worker.get_valve_states()
            valve_states[2] = 1  # Valve 2 (inlet)
            valve_states[3] = 1  # Valve 3 (outlet)
            valve_states[4] = 1  # Valve 4 (vent)
            valve_states[5] = 0  # Valve 5 (short)
            self.arduino_worker.set_valves(valve_states)

            # Start timer to close valves after duration
            QTimer.singleShot(int(duration * 1000), self.stop_bubble)
            self.logger.info(f"Quick bubble started for {duration}s")
            # Update valve button states to reflect macro settings
            for i in range(6):
                valve_button = getattr(self, f"Valve{i+1}Button")
                valve_button.setChecked(bool(valve_states[i]))
        else:
            self.stop_bubble()

    def stop_bubble(self):
        """Stop bubbling sequence."""
        if self.arduino_worker and self.arduino_worker.running:
            # Use the reset_valves method to preserve inlet/outlet valves
            self.reset_valves()
            self.quickBubbleButton.setChecked(False)
            self.logger.info("Quick bubble complete")

    def disable_valve_controls(self, disabled: bool = True):
        """Enable/disable valve controls.

        Args:
            disabled (bool): True to disable controls, False to enable
        """
        # Only enable if in manual mode and Arduino is connected
        enabled = (not disabled and
                   self.arduino_worker and  # Check if worker exists
                   self.arduino_worker.running and
                   self.arduino_manual_radio.isChecked())

        # Set enabled state for all valve buttons
        for i in range(1, 6):
            valve_button = getattr(self, f"Valve{i}Button")
            valve_button.setEnabled(enabled)

        # Set enabled state for macro buttons
        for i in range(1, 5):
            macro_button = getattr(self, f"valveMacro{i}Button")
            macro_button.setEnabled(enabled)

        # Set enabled state for quick action buttons
        self.quickBubbleButton.setEnabled(enabled)
        self.switchGas1Button.setEnabled(enabled)
        self.switchGas2Button.setEnabled(enabled)
        self.switchGas3Button.setEnabled(enabled)
        self.buildPressureButton.setEnabled(enabled)
        self.quickVentButton.setEnabled(enabled)
        self.slowVentButton.setEnabled(enabled)

    def disable_quick_controls(self, disabled: bool):
        """Enable/disable quick action and macro controls."""
        # Disable quick action buttons
        quick_action_buttons = [
            self.quickVentButton,
            self.slowVentButton,
            self.buildPressureButton,
            self.switchGas1Button,
            self.switchGas2Button,
            self.switchGas3Button,
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
        if self.arduino_worker and self.arduino_worker.running:  # Check if worker exists
            # Only enable valve buttons if Arduino is connected and in manual mode
            if self.arduino_worker.controller.mode == 0:  # Manual mode
                # Toggle all individual valve buttons 1-6
                for i in range(1, 7):  # Changed from 6 to 7 to include valve 6
                    if hasattr(self, f'Valve{i}Button'):
                        getattr(self, f'Valve{i}Button').setEnabled(enabled)
            else:
                # Force disable if not in manual mode
                for i in range(1, 7):  # Changed from 6 to 7 to include valve 6
                    if hasattr(self, f'Valve{i}Button'):
                        getattr(self, f'Valve{i}Button').setEnabled(False)
                self.dev_checkbox.setChecked(False)
        else:
            # Force disable if Arduino not connected
            for i in range(1, 7):  # Changed from 6 to 7 to include valve 6
                if hasattr(self, f'Valve{i}Button'):
                    getattr(self, f'Valve{i}Button').setEnabled(False)
            self.dev_checkbox.setChecked(False)

    @pyqtSlot()
    def on_ardConnectButton_clicked(self):
        """Handle Arduino connect button click."""
        try:
            # Check if we're disconnecting
            if self.arduino_worker and self.arduino_worker.running:
                try:
                    # Stop all timers first
                    self.cleanup_file_timer()
                    if hasattr(self, 'connection_check_timer'):
                        self.connection_check_timer.stop()
                        self.connection_check_timer.deleteLater()
                        delattr(self, 'connection_check_timer')

                    # Stop recording if it's active before disconnecting
                    if self.saving:
                        self.logger.info(
                            "Stopping data recording due to Arduino disconnection")
                        self.plot_widget.stop_recording()
                        self.beginSaveButton.setText("Begin Saving")
                        self.beginSaveButton.setChecked(False)
                        self.saving = False

                    # Uncheck all valve controls before disconnecting
                    self.uncheck_all_valve_controls()

                    self.arduino_worker.stop()
                    self.arduino_worker = None  # Clear the worker
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
                    self.update_device_status()  # Update after disconnect
                    return
                except Exception as e:
                    self.logger.error(f"Error disconnecting Arduino: {str(e)}")
                    return

            # Create new Arduino worker when connecting
            try:
                # Determine connection mode
                if self.arduino_auto_connect_radio.isChecked():
                    mode = 1  # Auto mode
                elif self.arduino_ttl_radio.isChecked():
                    mode = 2  # TTL mode
                else:
                    mode = 0  # Manual mode

                # Create new worker instance
                self.arduino_worker = ArduinoWorker(
                    port=self.arduino_port_spin.value(),
                    mock=self.test_mode,
                    mode=mode
                )

                # Connect the readings signal to plot widget
                self.arduino_worker.readings_updated.connect(
                    self.plot_widget.update_plot)

                # Set mode and start worker
                if self.arduino_worker.controller:
                    success = self.arduino_worker.start()

                    # Modified success check to handle test mode
                    if success or self.test_mode:
                        self.arduino_connect_btn.setText("Disconnect")
                        self.arduino_warning_label.setText("")
                        self.arduino_warning_label.setVisible(False)

                        # Enable/disable controls based on mode
                        if mode == 0:  # Manual mode
                            self.dev_checkbox.setEnabled(True)
                            self.disable_quick_controls(False)
                        else:
                            self.dev_checkbox.setEnabled(False)
                            self.disable_valve_controls(True)
                            self.disable_quick_controls(True)

                        # Set valve mode
                        self.set_valve_mode(mode)

                        self.logger.info(
                            f"Connected to Arduino in mode {mode}")

                        # Create a timer to check connection status and update device status
                        self.connection_check_timer = QTimer()
                        self.connection_check_timer.setSingleShot(True)
                        self.connection_check_timer.timeout.connect(
                            self._check_connection_and_update)
                        self.connection_check_timer.start(
                            1000)  # Check every second

                    else:
                        self.arduino_worker = None  # Clear failed worker
                        self.handle_error("Failed to connect to Arduino")
                        if not self.test_mode:
                            self.arduino_warning_label.setText(
                                "Warning: Arduino not connected")
                            self.arduino_warning_label.setVisible(True)
                else:
                    self.handle_error(
                        "Failed to initialize Arduino controller")
                    self.arduino_worker = None

            except Exception as e:
                self.arduino_worker = None  # Clear failed worker
                self.handle_error(f"Failed to connect to Arduino: {str(e)}")
                self.arduino_connect_btn.setText("Connect")
                if not self.test_mode:
                    self.arduino_warning_label.setText(
                        "Warning: Arduino not connected")
                    self.arduino_warning_label.setVisible(True)

        except Exception as e:
            self.logger.error(
                f"Uncaught exception in Arduino connection: {str(e)}")
            if self.arduino_worker:
                self.arduino_worker.stop()
                self.arduino_worker = None
            self.handle_error(
                "An unexpected error occurred while connecting to Arduino")
            self.arduino_connect_btn.setText("Connect")
            if not self.test_mode:
                self.arduino_warning_label.setText(
                    "Warning: Arduino not connected")
                self.arduino_warning_label.setVisible(True)

    def _check_connection_and_update(self):
        """Check if Arduino is connected and update device status if it is."""
        if self.arduino_worker and self.arduino_worker.running:
            self.update_device_status()
            # If in automatic mode and connection is confirmed, start sequence monitoring
            if self.arduino_auto_connect_radio.isChecked():
                if self.motor_worker and self.motor_worker.running:
                    self.motor_worker.set_sequence_mode(True)
                    self.logger.info("Motor set to sequence mode")
                self.start_sequence_monitoring()
            if hasattr(self, 'connection_check_timer'):
                self.connection_check_timer.stop()
                self.connection_check_timer.deleteLater()
                delattr(self, 'connection_check_timer')
        else:
            # If not connected yet, check again in a second
            if hasattr(self, 'connection_check_timer'):
                self.connection_check_timer.start(1000)

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
        """Handle motor stop button click."""
        try:
            if self.motor_worker and self.motor_worker.running:
                self.motor_worker.emergency_stop()
                self.logger.info("Motor stopped by user")
        except Exception as e:
            self.logger.error(f"Error stopping motor: {e}")
            self.handle_error("Failed to stop motor")
        self.update_device_status()  # Update device status after emergency stop

    @pyqtSlot()
    def on_motorMoveToTargetButton_clicked(self):
        """Handle move to target button click."""
        try:
            target = float(self.target_motor_pos_edit.text())
            if self.motor_worker.running:
                if target < 0:
                    QMessageBox.warning(self, "Invalid Position",
                                        "Invalid target position. Position must be non-negative.")
                    return
                elif target > self.motor_worker.controller.POSITION_MAX:
                    response = QMessageBox.question(self, "Position Limit Exceeded",
                                                    f"Target position {target}mm exceeds maximum allowed position of {
                                                        self.motor_worker.controller.POSITION_MAX}mm.\n\n"
                                                    f"Would you like to move to the maximum position of {
                                                        self.motor_worker.controller.POSITION_MAX}mm?",
                                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)

                    if response != QMessageBox.StandardButton.Yes:
                        return
                    else:
                        target = self.motor_worker.controller.POSITION_MAX
                        self.motor_worker.move_to(target)
                        # self.logger.info(f"Moving motor to position {target}mm")
                        if self.timing_mode:
                            self.timing_logger.info(
                                f"MOTOR_COMMAND_SENT - Target Position: {target}mm")
                else:
                    self.motor_worker.move_to(target)
                    # self.logger.info(f"Moving motor to position {target}mm")
                    if self.timing_mode:
                        self.timing_logger.info(
                            f"MOTOR_COMMAND_SENT - Target Position: {target}mm")
        except ValueError:
            self.handle_error("Invalid target position")

    @pyqtSlot()
    def on_motorToBottomButton_clicked(self):
        """Handle motor to bottom button click."""
        if self.motor_worker.running:
            if self.motor_worker.to_bottom():
                pass
                # self.logger.info("Moving motor to bottom position")
            else:
                self.handle_error("Failed to move motor to bottom")

    @pyqtSlot()
    def on_motorToTopButton_clicked(self):
        """Handle motor to top button click."""
        if self.motor_worker.running:
            if self.motor_worker.to_top():
                pass
                # self.logger.info("Moving motor to top position")
            else:
                self.handle_error("Failed to move motor to top")

    @pyqtSlot(int)
    def on_motorMacroButton_clicked(self, macro_num: int):
        """Handle motor macro button click.

        Args:
            macro_num: Macro number (1-6)
        """
        if self.motor_worker and self.motor_worker.running:
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
                        self.logger.info(f"Executing motor macro {
                                         macro_num}: {macro['Label']}")

                        # Stop any existing timer
                        if hasattr(self, 'position_check_timer') and self.position_check_timer is not None:
                            self.position_check_timer.stop()
                            self.position_check_timer = None

                        # Create a timer to check position periodically
                        self.position_check_timer = QTimer(self)
                        self.position_check_timer.setInterval(
                            100)  # Check every 100ms

                        def check_position():
                            if not self.motor_worker:  # Check if motor worker exists
                                if self.position_check_timer:
                                    self.position_check_timer.stop()
                                    self.position_check_timer = None
                                macro_button.setChecked(False)
                                return

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
                self.logger.error(f"Error executing motor macro: {e}")
                if hasattr(self, 'position_check_timer') and self.position_check_timer is not None:
                    self.position_check_timer.stop()
                    self.position_check_timer = None

    @pyqtSlot(bool)
    def on_beginSaveButton_clicked(self, checked=None):
        """Handle begin save button click."""
        # Add debug logging for initial state
        self.logger.debug(
            f"Begin save clicked - Initial state: checked={checked}, saving={self.saving}")

        # If called programmatically, use button's checked state
        if checked is None:
            checked = self.beginSaveButton.isChecked()

        self.logger.debug(f"Using checked state: {checked}")

        if checked:
            try:
                # Create data directory if it doesn't exist
                data_dir = Path("C:/ssbubble/data")
                data_dir.mkdir(parents=True, exist_ok=True)

                # Get or generate save path
                save_path = self.savePathEdit.text()
                self.logger.debug(f"Save path from edit: {save_path}")

                if not save_path:
                    # Generate default save path with timestamp
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    save_path = str(
                        data_dir / f"pressure_data_{timestamp}.csv")
                    self.logger.debug(f"Generated save path: {save_path}")

                # Update the text field with the generated path
                self.savePathEdit.setText(save_path)

                # Ensure directory exists
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)

                # Start recording
                self.logger.debug("Attempting to start recording...")
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
            self.logger.debug("Stopping recording...")
            self.plot_widget.stop_recording()
            self.beginSaveButton.setText("Begin Saving")
            self.beginSaveButton.setChecked(False)
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
        """Handle pressure sensor radio button clicks."""
        try:
            # Get the radio button that was clicked
            radio = getattr(self, f'pressure{sensor_num}RadioButton')

            # Update plot visibility based on radio button state
            self.plot_widget.set_sensor_visibility(
                sensor_num, radio.isChecked())

            # Log the change
            if radio.isChecked():
                self.logger.info(f"Pressure sensor {
                                 sensor_num} display enabled")
            else:
                self.logger.info(f"Pressure sensor {
                                 sensor_num} display disabled")

        except Exception as e:
            self.logger.error(f"Error handling pressure radio button: {e}")

    @pyqtSlot(int)
    def on_valveMacroButton_clicked(self, macro_num: int):
        """Handle valve macro button click."""
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

                    # Record current valve states before applying macro
                    self.pre_macro_states = [0] * 8
                    if hasattr(self.arduino_worker, 'get_valve_states'):
                        self.pre_macro_states = self.arduino_worker.get_valve_states()

                    self.logger.info(
                        f"Pre-macro valve states: {self.pre_macro_states}")

                    # Create new valve states based on macro settings
                    valve_states = [0] * 8
                    for i, state in enumerate(macro["Valves"]):
                        if state == "Open":
                            valve_states[i] = 1
                        elif state == "Closed":
                            valve_states[i] = 0
                        elif state == "Ignore":
                            valve_states[i] = self.pre_macro_states[i]

                    # Send valve states to Arduino
                    self.arduino_worker.set_valves(valve_states)
                    self.logger.info(f"Sent valve states for macro {
                                     macro_num}: {valve_states}")

                    # Update valve button states to reflect macro settings
                    for i in range(6):
                        valve_button = getattr(self, f"Valve{i+1}Button")
                        valve_button.setChecked(bool(valve_states[i]))

                    # Check the macro button
                    macro_button.setChecked(True)

                    # If macro has a timer, schedule valve reset
                    timer = macro.get("Timer", 0)
                    if timer > 0:
                        def reset_valves():
                            try:
                                # Create new states: restore valves 1-2, close 3-8
                                final_states = [0] * 8
                                # Restore valve 1
                                final_states[0] = self.pre_macro_states[0]
                                # Restore valve 2
                                final_states[1] = self.pre_macro_states[1]
                                # Valves 3-8 remain 0 (closed)

                                # Send valve states to Arduino
                                self.arduino_worker.set_valves(final_states)

                                # Update valve button states
                                for i in range(6):
                                    valve_button = getattr(
                                        self, f"Valve{i+1}Button")
                                    valve_button.setChecked(
                                        bool(final_states[i]))

                                # Reset macro state
                                self.active_valve_macro = None
                                self.active_macro_timer = None
                                macro_button.setChecked(False)

                                # Re-enable controls
                                self.enable_all_valve_controls()

                                self.logger.info(
                                    f"Reset valves after macro: {final_states}")

                            except Exception as e:
                                self.logger.error(f"Error in macro reset: {e}")

                        # Create and store the timer
                        self.active_macro_timer = QTimer()
                        self.active_macro_timer.setSingleShot(True)
                        self.active_macro_timer.timeout.connect(reset_valves)
                        self.active_macro_timer.start(int(timer * 1000))

                    self.logger.info(f"Executed valve macro {
                                     macro_num}: {macro['Label']}")
                else:
                    self.handle_error(f"Valve macro {macro_num} not found")
                    macro_button.setChecked(False)

            except Exception as e:
                self.handle_error(
                    f"Failed to execute valve macro {macro_num}: {e}")
                # Clean up on error
                if self.active_macro_timer is not None:
                    self.active_macro_timer.stop()
                    self.active_macro_timer = None
                self.active_valve_macro = None
                macro_button.setChecked(False)
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
        """Start sequence execution."""
        try:
            if self.steps:
                # Check if we need to delay the sequence start
                if hasattr(self, 'sequence_start_delay') and self.sequence_start_delay:
                    current_time = datetime.now()
                    if current_time < self.sequence_start_delay:
                        # Calculate delay in milliseconds
                        delay_ms = int(
                            (self.sequence_start_delay - current_time).total_seconds() * 1000)

                        # Update status to show waiting
                        self.update_sequence_status(
                            f"Waiting for start time: {self.sequence_start_delay.strftime('%Y-%m-%d %H:%M:%S.%f')}")

                        # Schedule the actual sequence start
                        QTimer.singleShot(
                            delay_ms, self._start_sequence_execution)
                        self.logger.info(
                            f"Sequence delayed to start at {self.sequence_start_delay}")
                        return

                # No delay needed, start immediately
                self._start_sequence_execution()

        except Exception as e:
            self.logger.error(f"Error starting sequence: {e}")
            self.handle_error("Failed to start sequence")

    def _start_sequence_execution(self):
        """Internal method to execute sequence after any delay."""
        try:
            # Clear plot before starting new sequence
            # self.plot_widget.clear_plot()

            # Only start recording if not already recording
            if self.saving and not self.plot_widget.recording:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filepath = os.path.join(
                    self.default_save_path, f"sequence_{timestamp}.csv")
                if not self.plot_widget.start_recording(filepath):
                    self.handle_error("Failed to start data recording")
                    return

            # Execute first step
            self.execute_step(self.steps[0])

            # Start step timer
            self.step_start_time = time.time()
            self.step_timer = QTimer()
            self.step_timer.timeout.connect(self.update_step_time)
            self.step_timer.start(100)  # Update every 100ms

            # Schedule next step
            QTimer.singleShot(self.steps[0].time_length, self.next_step)

            self.logger.info("Sequence execution started")
            self.update_sequence_status("Running")

        except Exception as e:
            self.logger.error(f"Error executing sequence: {e}")
            self.handle_error("Failed to execute sequence")

    def next_step(self):
        """Execute the next step in the sequence."""
        self.steps.pop(0)  # Remove completed step

        if not self.steps:  # Sequence complete
            self.step_timer.stop()

            # Reset valves while preserving inlet/outlet
            if self.arduino_worker and self.arduino_worker.running:
                self.reset_valves()

            # Disable sequence mode
            if self.motor_flag and self.motor_worker:
                self.motor_worker.set_sequence_mode(False)

            # Update UI and stop recording
            self.update_sequence_info("Complete", 0, 0, 0)
            self.update_sequence_status("Complete")

            # Start a 15-minute timer to stop saving if no new sequence is received
            if self.saving:
                # Cancel any existing save timer first
                if hasattr(self, 'save_stop_timer') and self.save_stop_timer is not None:
                    self.save_stop_timer.stop()

                # Create new timer for 15 minutes (900000 ms)
                self.save_stop_timer = QTimer()
                self.save_stop_timer.setSingleShot(True)
                self.save_stop_timer.timeout.connect(self.stop_saving_timeout)
                self.save_stop_timer.start(900000)  # 15 minutes
                self.logger.info(
                    "Started 15-minute timer to stop saving if no new sequence is received")

            # Restart sequence monitoring
            if self.arduino_worker and self.arduino_worker.running and self.arduino_worker.mode == 1:
                self.logger.info("Restarting sequence monitoring")
                self.start_sequence_monitoring()

        else:
            # Execute next step in current sequence
            self.execute_step(self.steps[0])
            # Reset step timer and schedule next step
            self.step_start_time = time.time()
            QTimer.singleShot(self.steps[0].time_length, self.next_step)

    def execute_step(self, step):
        """Execute a single step in the sequence."""
        if not step:
            return

        if self.arduino_worker and self.arduino_worker.running:
            # init valve states
            valve_states = [0] * 8

            # get current valve states
            valve_states = self.arduino_worker.get_valve_states()

            # Get valve states from configuration
            config_valve_states = self.config_manager.get_step_valve_states(
                step.step_type)

            if config_valve_states is not None:
                # Update valve states based on configuration
                for valve_num, state in config_valve_states.items():
                    if state == 'ignore':
                        continue  # Skip valves that should maintain their current state
                    elif state == 'open':
                        valve_states[valve_num - 1] = 1
                    elif state == 'close':
                        valve_states[valve_num - 1] = 0

                # set valve states
                self.arduino_worker.set_valves(valve_states)
            else:
                # Fallback to default behavior if configuration is not found
                self.log_widget.add_message(
                    f"Warning: No configuration found for step type '{step.step_type}'", logging.WARNING)
                return
        else:
            self.log_widget.add_message(
                f"Warning: Arduino not connected", logging.WARNING)
            return

        # Handle motor position if specified
        if hasattr(step, 'motor_position') and step.motor_position >= 0:
            if self.motor_flag:
                self.motor_worker.move_to(step.motor_position)
            else:
                self.logger.info(
                    "Skipping motor movement - motor not required for this sequence")

    def disable_other_valve_controls(self, active_macro_num: int):
        """Disable all valve controls except the active macro button.

        Args:
            active_macro_num: Number of the active macro button (1-4)
        """
        # Disable individual valve buttons
        for i in range(1, 7):
            valve_button = getattr(self, f"Valve{i}Button")
            valve_button.setEnabled(False)

        # Disable other macro buttons
        for i in range(1, 5):
            if i != active_macro_num:
                macro_button = getattr(self, f"valveMacro{i}Button")
                macro_button.setEnabled(False)

        # Disable quick action buttons
        self.quickBubbleButton.setEnabled(False)
        self.switchGas1Button.setEnabled(False)
        self.switchGas2Button.setEnabled(False)
        self.switchGas3Button.setEnabled(False)
        self.buildPressureButton.setEnabled(False)
        self.quickVentButton.setEnabled(False)
        self.slowVentButton.setEnabled(False)

    def enable_all_valve_controls(self):
        """Re-enable all valve controls."""
        # Only enable if in manual mode and Arduino is connected
        if self.arduino_worker.running and self.arduino_manual_radio.isChecked():
            # Enable individual valve buttons
            for i in range(1, 7):
                valve_button = getattr(self, f"Valve{i}Button")
                valve_button.setEnabled(True)

            # Enable macro buttons
            for i in range(1, 5):
                macro_button = getattr(self, f"valveMacro{i}Button")
                macro_button.setEnabled(True)

            # Enable quick action buttons
            self.quickBubbleButton.setEnabled(True)
            self.switchGas1Button.setEnabled(True)
            self.switchGas2Button.setEnabled(True)
            self.switchGas3Button.setEnabled(True)
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
        """Update Arduino port configuration."""
        self.config.arduino_port = port
        self.config.save()

        # If currently connected, disconnect first
        if self.arduino_worker and self.arduino_worker.running:
            self.cleanup_arduino_worker()
            self.arduino_connect_btn.setText("Connect")
            self.logger.info("Disconnected from Arduino due to port change")

            # Reset UI state
            if not self.test_mode:
                self.arduino_warning_label.setText(
                    "Warning: Arduino not connected")
                self.arduino_warning_label.setVisible(True)

            # Disable controls
            self.dev_checkbox.setEnabled(False)
            self.dev_checkbox.setChecked(False)
            self.disable_valve_controls(True)

        self.logger.info(f"Arduino port updated to COM{port}")

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
        # Existing error handling...

        # Update status file if error affects device connections
        if any(term in message.lower() for term in ["connect", "connection", "disconnected", "calibration"]):
            self.update_device_status()

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

    def closeEvent(self, event):
        """Handle application shutdown."""
        try:
            # Stop saving if it's currently active
            if self.saving:
                self.logger.info(
                    "Stopping data recording during application shutdown")
                self.plot_widget.stop_recording()
                self.saving = False

            # Write disconnected status before cleanup
            try:
                with open(Path("C:/ssbubble/device_status.txt"), 'w') as f:
                    f.write("00")
            except Exception as e:
                self.logger.error(f"Failed to reset device status file: {e}")

            # First stop all timers
            self.cleanup_file_timer()
            self.cleanup_motor_timers()

            # Then clean up workers
            if hasattr(self, 'arduino_worker') and self.arduino_worker:
                self.cleanup_arduino_worker()

            if hasattr(self, 'motor_worker') and self.motor_worker:
                self.cleanup_motor_worker()

            # Finally shutdown logging system
            # Add a small delay to allow final logs to be processed
            QTimer.singleShot(100, shutdown_logging)

            # Accept the event immediately to prevent UI freezing
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            event.accept()

    def load_sequence(self):
        """Load sequence from file.

        Expected format:
        ["step_type1","step_type2",...]  # Valid types: d,p,v,b,f,e,c
        ["time1","time2",...]  # Times in milliseconds
        ["pos1","pos2",...] or ["None",...]  # Positions in mm or "None"
        ["speed"]  # Global motor speed (fast, medium, slow)
        save_path  # Path or "None"
        [year,month,day,hour,minute,second,millisecond] or "None" # Start delay timestamp

        Example:
        ["b","p","d","b","v"]
        ["1000","1000","1000","1000","1000"]    
        ["10","200","0","250","None"]
        ["fast"]
        C:\\ssbubble\\data
        [2025,2,22,18,58,10,861]
        """
        try:
            # Cancel any active save stop timer when a new sequence is loaded
            if hasattr(self, 'save_stop_timer') and self.save_stop_timer is not None:
                self.save_stop_timer.stop()
                self.save_stop_timer = None
                self.logger.info(
                    "Cancelled save stop timer due to new sequence")

            # Init steps
            self.steps = []
            self.motor_flag = False

            # Check if sequence file exists
            with open(Path("C:/ssbubble/sequence.txt"), 'r') as f:
                sequence = f.readlines()

            # Check if sequence file is empty
            if not sequence:
                self.logger.error("Sequence file is empty")
                return False

            # Parse start delay timestamp from fifth line
            start_delay_str = sequence[5].strip() if len(
                sequence) > 5 else "None"
            start_delay = None

            if start_delay_str != "None":
                try:
                    # Parse timestamp list [year,month,day,hour,minute,second,millisecond]
                    timestamp_list = eval(start_delay_str)
                    from datetime import datetime
                    start_delay = datetime(
                        timestamp_list[0],  # year
                        timestamp_list[1],  # month
                        timestamp_list[2],  # day
                        timestamp_list[3],  # hour
                        timestamp_list[4],  # minute
                        timestamp_list[5],  # second
                        timestamp_list[6]   # microsecond
                    )
                except Exception as e:
                    self.logger.error(
                        f"Invalid start delay timestamp format: {e}")
                    return False

            # Store start delay
            self.sequence_start_delay = start_delay

            # Get the save path from the fourth line
            seq_save_path = sequence[4].strip() if len(
                sequence) > 4 else "None"

            # Get the global motor speed from the third line
            global_motor_speed = None
            if len(sequence) > 3:
                try:
                    # Parse motor speed - expecting format like ["fast"]
                    speed_str = sequence[3].strip()
                    # Remove brackets and quotes
                    speed_str = speed_str.strip('[]').replace('"', '').strip()
                    if speed_str:
                        global_motor_speed = speed_str.lower()
                        self.logger.info(
                            f"Global motor speed set to: {global_motor_speed}")
                except Exception as e:
                    self.logger.error(f"Error parsing motor speed: {e}")
                    # Continue with default speed if there's an error

            # Convert lists into steps - handle double quoted format
            step_types = sequence[0].strip().strip(
                '[]').replace('"', '').split(',')

            # IMPORTANT: Swap the order of time_lengths and motor_positions to match the new format
            time_lengths = sequence[1].strip().strip(
                '[]').replace('"', '').split(',')
            motor_positions = sequence[2].strip().strip(
                '[]').replace('"', '').split(',')

            # Clean any whitespace
            step_types = [s.strip() for s in step_types]
            time_lengths = [t.strip() for t in time_lengths]
            motor_positions = [p.strip() for p in motor_positions]

            # Validate step types
            valid_step_types = set(self.step_types.keys())  # d,p,v,b,f,e,c
            if not all(step_type in valid_step_types for step_type in step_types):
                invalid_types = [
                    t for t in step_types if t not in valid_step_types]
                self.logger.error(
                    f"Invalid step types in sequence: {invalid_types}. Valid types are: {list(valid_step_types)}")
                return False

            # Convert time lengths to numbers
            try:
                time_lengths = [int(time) for time in time_lengths]
                if not all(t > 0 for t in time_lengths):
                    self.logger.error("Time lengths must be positive numbers")
                    return False
            except ValueError:
                self.logger.error(
                    f"Invalid time lengths in sequence file - must be integers. Values: {time_lengths}")
                return False

            # Handle motor positions
            try:
                motor_positions = [None if pos == "None" else float(
                    pos) for pos in motor_positions]
                if any(pos is not None and pos < 0 for pos in motor_positions):
                    self.logger.error("Motor positions must be non-negative")
                    return False
                # Check if all non-None positions are equal to 364.40
                if all(pos is None or abs(pos - 364.40) < 0.01 for pos in motor_positions):
                    # If motor is not connected, it's not required
                    if not self.motor_worker or not self.motor_worker.running:
                        self.motor_flag = False
                        self.logger.info(
                            "Motor not required - not connected and all positions are at maximum (364.40)")
                    else:
                        # Check current position
                        current_pos = self.motor_worker.get_current_position()
                        if abs(current_pos - 364.40) < 0.01:
                            self.motor_flag = False
                            self.logger.info(
                                "Motor not required - already at maximum position (364.40)")
                        else:
                            self.motor_flag = True
                            self.logger.info(
                                "Motor required - needs to move to maximum position (364.40)")
                elif any(pos is not None for pos in motor_positions):
                    self.motor_flag = True
            except ValueError:
                self.logger.error(
                    f"Invalid motor positions in sequence file - must be numbers or 'None'. Values: {motor_positions}")
                return False

            # Validate sequence lengths match
            if not (len(step_types) == len(motor_positions) == len(time_lengths)):
                self.logger.error(
                    f"Sequence lists have different lengths: steps={len(step_types)}, times={len(time_lengths)}, positions={len(motor_positions)}")
                return False

            # Parse steps
            for i in range(len(step_types)):
                step_type = step_types[i]
                motor_position = motor_positions[i]
                if motor_position is not None and self.motor_worker:
                    motor_position = min(
                        motor_position, self.motor_worker.max_position)
                time_length = time_lengths[i]

                # Create step object
                step = Step(step_type, time_length, motor_position)
                self.steps.append(step)

            # Apply global motor speed if specified and motor is connected
            if global_motor_speed and self.motor_worker and self.motor_worker.running:
                # Set the motor speed combo box
                if global_motor_speed in ['fast', 'medium', 'slow']:
                    # Convert to title case for the combo box
                    speed_text = global_motor_speed.title()
                    self.motor_speed_combo.setCurrentText(speed_text)
                    # This will trigger the on_motor_speed_changed slot
                else:
                    self.logger.warning(
                        f"Invalid motor speed: {global_motor_speed}. Using current speed.")

            # Check if saving already
            if not self.saving:
                # Get the save path from the sequence file
                if len(seq_save_path) > 1:
                    if seq_save_path.endswith('.csv'):
                        self.savePathEdit.setText(seq_save_path)
                        self.prev_save_path = seq_save_path
                        # Don't set saving=True until after start_recording succeeds
                        if self.on_beginSaveButton_clicked(True):
                            self.saving = True
                    else:
                        new_path = os.path.join(
                            seq_save_path, f"pressure_data_{time.strftime('%m%d-%H%M')}.csv").replace("/", "\\")
                        self.savePathEdit.setText(new_path)
                        self.prev_save_path = new_path
                        if self.on_beginSaveButton_clicked(True):
                            self.saving = True
                elif seq_save_path == "None":   # No save path means stop saving
                    self.savePathEdit.setText("")
                    self.prev_save_path = None
                    self.on_beginSaveButton_clicked(False)
                    self.saving = False
            else:
                if seq_save_path != self.prev_save_path and seq_save_path != "None":
                    # New save path given, stop saving and restart with new path
                    self.on_beginSaveButton_clicked(
                        False)  # Stop current recording
                    self.savePathEdit.setText(seq_save_path)
                    self.prev_save_path = seq_save_path
                    # Start new recording
                    if self.on_beginSaveButton_clicked(True):
                        self.saving = True
                elif seq_save_path == "None":
                    self.on_beginSaveButton_clicked(False)
                    self.savePathEdit.setText("")
                    self.prev_save_path = None
                    self.saving = False

            return True
        except FileNotFoundError:
            self.logger.error("Sequence file not found")
            return False
        except IOError as e:
            self.logger.error(f"Error reading sequence file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading sequence: {e}")
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
            if success and not self.keep_sequence:
                sequence_path.unlink()
                self.logger.info("Sequence file processed and deleted")
            elif success and self.keep_sequence:
                self.logger.info(
                    "Sequence file processed but preserved")
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

    def cleanup_file_timer(self):
        """Clean up file monitoring timer."""
        if hasattr(self, 'file_check_timer') and self.file_check_timer:
            self.file_check_timer.stop()
            self.file_check_timer.deleteLater()
            self.file_check_timer = None

        # When the 15-minute timer elapses, stop recording
        if self.plot_widget and self.plot_widget.recording:
            self.plot_widget.stop_recording()
            self.log_widget.log_info(
                "Recording stopped: 15-minute sequence timer elapsed")

    def cleanup_arduino_worker(self):
        """Clean up Arduino worker resources."""
        try:
            if self.arduino_worker:
                # Stop file check timer if it exists
                self.cleanup_file_timer()

                self.arduino_worker.stop()
                self.arduino_worker = None
                self.logger.info("Arduino worker cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up Arduino worker: {e}")

    @pyqtSlot(bool)
    def handle_calibration_state_changed(self, is_calibrated: bool):
        """Handle motor calibration state changes."""
        self.motor_calibrated = is_calibrated
        if is_calibrated:
            self.motor_warning_label.setText("")
            self.motor_warning_label.setVisible(False)
            self.disable_motor_controls(False)  # Enable controls
            self.logger.info("Motor calibrated successfully")
            self.update_device_status()  # Update after successful calibration
        else:
            self.motor_warning_label.setText("Motor needs calibration")
            self.motor_warning_label.setVisible(True)
            self.disable_motor_controls(True)  # Disable controls
            self.logger.info("Motor needs calibration")
            self.update_device_status()  # Update after failed calibration

    @pyqtSlot(str)
    def on_motor_speed_changed(self, speed_text: str):
        """Handle motor speed changes.

        Args:
            speed_text: Selected speed text (Fast/Medium/Slow)
        """
        try:
            # Map text to speed values
            speed_map = {
                'Fast': 6500,    # Maximum speed
                'Medium': 4000,   # 60% speed
                'Slow': 2000      # 30% speed
            }

            speed = speed_map.get(speed_text)
            if speed is not None and self.motor_worker.running:
                success = self.motor_worker.set_speed(speed)
                if success:
                    self.logger.info(f"Motor speed set to {speed_text}")
                else:
                    self.logger.error(
                        f"Failed to set motor speed to {speed_text}")

        except Exception as e:
            self.logger.error(f"Error setting motor speed: {e}")

    def update_motor_port(self, port: int):
        """Update motor port configuration."""
        self.config.motor_port = port
        self.config.save()

        # If currently connected, disconnect and cleanup
        if self.motor_worker and self.motor_worker.running:
            self.cleanup_motor_worker()
            self.motor_connect_btn.setText("Connect")
            self.logger.info("Disconnected from motor due to port change")

            # Reset motor state
            self.motor_calibrated = False
            self.motor_warning_label.setText("Warning: Motor not connected")
            self.motor_warning_label.setVisible(True)
            self.motor_calibrate_btn.setEnabled(False)
            self.disable_motor_controls(True)

        # Create new worker with updated port
        self.motor_worker = MotorWorker(
            port=port,
            update_interval=self.config.motor_update_interval,
            mock=self.test_mode,
            timing_mode=self.timing_mode  # Pass timing mode to worker
        )
        self.setup_connections()
        #self.logger.info(f"Motor port updated to COM{port}")

    def start_sequence_monitoring(self):
        """Start sequence file monitoring after delay."""
        try:
            # Create and store the delay timer
            self.delay_timer = QTimer()
            self.delay_timer.setSingleShot(True)
            self.delay_timer.timeout.connect(self.find_sequence_file)
            self.delay_timer.start()  # Can put a delay here if needed
            self.logger.info(
                "Starting sequence file monitoring")
        except Exception as e:
            self.logger.error(f"Error setting up sequence monitoring: {e}")

    def cleanup_file_timer(self):
        """Clean up file monitoring timer."""
        if hasattr(self, 'file_check_timer') and self.file_check_timer:
            self.file_check_timer.stop()
            self.file_check_timer.deleteLater()
            self.file_check_timer = None

        # When the 15-minute timer elapses, stop recording
        if self.plot_widget and self.plot_widget.recording:
            self.plot_widget.stop_recording()
            self.log_widget.log_info(
                "Recording stopped: 15-minute sequence timer elapsed")

    def uncheck_all_valve_controls(self):
        """Uncheck all valve buttons and macros."""
        try:
            # Uncheck all valve buttons
            for i in range(1, 7):  # For all 6 valve buttons
                valve_button = getattr(self, f"Valve{i}Button")
                valve_button.setChecked(False)

            # Uncheck all valve macro buttons
            for i in range(1, 5):  # For all 4 macro buttons
                macro_button = getattr(self, f"valveMacro{i}Button")
                macro_button.setChecked(False)

            # Uncheck quick action buttons
            self.quickBubbleButton.setChecked(False)
            self.switchGas1Button.setChecked(False)
            self.switchGas2Button.setChecked(False)
            self.switchGas3Button.setChecked(False)
            self.buildPressureButton.setChecked(False)
            self.quickVentButton.setChecked(False)
            self.slowVentButton.setChecked(False)

            self.logger.info("All valve controls unchecked")
        except Exception as e:
            self.logger.error(f"Error unchecking valve controls: {e}")

    def update_device_status(self):
        """Update device status file with current connection states.

        Format: XY where:
        X: Arduino status (0=disconnected, 1=connected in auto mode)
        Y: Motor status (0=disconnected/uncalibrated, 1=connected and calibrated)
        """
        try:
            self.logger.info("Updating device status file...")  # Add debug log

            # Get Arduino status (1 if connected and in auto mode)
            if self.test_mode:
                # In test mode, check both worker and controller mode
                arduino_status = '1' if (self.arduino_worker and
                                         self.arduino_worker.running and
                                         (self.arduino_worker.mode == 1 or
                                          self.arduino_worker.controller.mode == 1)) else '0'
                self.logger.debug(f"Test mode - Arduino worker mode: {self.arduino_worker.mode if self.arduino_worker else 'None'}, "
                                  f"Controller mode: {self.arduino_worker.controller.mode if self.arduino_worker and self.arduino_worker.controller else 'None'}")
            else:
                # Normal mode - check worker mode
                arduino_status = '1' if (self.arduino_worker and
                                         self.arduino_worker.running and
                                         self.arduino_worker.mode == 1) else '0'

            # Get Motor status (1 if connected and calibrated)
            motor_status = '1' if (self.motor_worker and
                                   self.motor_worker.running and
                                   self.motor_calibrated) else '0'

            # Write status to file
            status_path = Path("C:/ssbubble/device_status.txt")
            status_path.parent.mkdir(parents=True, exist_ok=True)

            with open(status_path, 'w') as f:
                f.write(f"{arduino_status}{motor_status}")

            self.logger.debug(
                f"Device status updated: Arduino={arduino_status}, Motor={motor_status}")

        except Exception as e:
            self.logger.error(f"Failed to update device status file: {e}")

    def _setup_motor_worker(self):
        """Set up the motor worker thread."""
        try:
            # Create motor worker
            self.motor_worker = MotorWorker(
                port=int(self.config.get('motor', 'port')),
                update_interval=0.1,
                mock=(self.config.get('motor', 'mode') == '2'),
                timing_mode=self.timing_mode,
            )

            # Connect signals
            self.motor_worker.position_updated.connect(
                self._update_motor_position)
            self.motor_worker.error_occurred.connect(self._handle_motor_error)
            self.motor_worker.status_changed.connect(self._update_motor_status)
            self.motor_worker.calibration_state_changed.connect(
                self._update_calibration_state)

            # Start the worker
            self.motor_worker.start()

        except Exception as e:
            self.logger.error(f"Error setting up motor worker: {e}")

    @pyqtSlot(float)
    def _handle_position_reached(self, position):
        """Handle motor position reached signal."""
        self.logger.info(f"Motor reached position: {position}mm")
        # Any additional handling when position is reached

    def cleanup_motor_timers(self):
        """Clean up all motor-related timers."""
        # Clean up file timer if it's running
        self.cleanup_file_timer()

        # Clean up save stop timer if it exists
        if hasattr(self, 'save_stop_timer') and self.save_stop_timer is not None:
            self.save_stop_timer.stop()
            self.save_stop_timer = None
            self.logger.info("Save stop timer cleaned up")

        # Cancel any pending single-shot timers related to motor operations
        # Use QCoreApplication instead of QApplication for better compatibility
        from PyQt6.QtCore import QCoreApplication
        for timer in QCoreApplication.instance().findChildren(QTimer):
            if timer.isSingleShot() and timer.isActive():
                timer.stop()

    def stop_saving_timeout(self):
        """Stop saving after the timeout period if saving is still active."""
        if self.saving:
            self.logger.info(
                "15-minute timeout reached - stopping data recording")
            self.on_beginSaveButton_clicked(False)
            self.saving = False

    def handle_critical_motor_error(self, message: str):
        """Handle critical motor errors by stopping the sequence, cleaning up, and alerting the user."""
        self.logger.critical(f"Critical motor error: {message}")
        # Stop any running sequence
        try:
            if hasattr(self, 'step_timer') and self.step_timer:
                self.step_timer.stop()
        except Exception:
            pass
        # Clean up motor worker
        try:
            self.cleanup_motor_worker()
        except Exception:
            pass
        # Show critical error dialog
        QMessageBox.critical(self, "Critical Motor Error",
                             f"A critical error occurred with the motor and the sequence has been stopped.\n\nError: {message}")
        # Optionally, update UI to reflect stopped state
        self.update_device_status()
