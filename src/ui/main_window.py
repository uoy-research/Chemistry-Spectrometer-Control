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

    def __init__(self, test_mode: bool = False):
        """Initialize main window.
        
        Args:
            test_mode: Use mock controllers for testing
        """
        super().__init__()

        # Load configuration
        self.config = Config()
        self.test_mode = test_mode

        # Initialize macro manager with config path
        macro_path = Path(self.config.macro_file)
        self.macro_manager = MacroManager(macro_path)

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

        self.arduino_warning_label = QLabel("")
        self.arduino_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arduino_warning_label.setStyleSheet("color: red;")
        if not self.test_mode:
            self.arduino_warning_label.setText("Warning: Arduino not connected")

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

        self.arduino_connect_button = QPushButton("Connect")
        self.arduino_connect_button.setMinimumSize(QSize(0, 70))
        font = QFont()
        font.setPointSize(18)
        self.arduino_connect_button.setFont(font)
        self.arduino_connect_button.setObjectName("ardConnectButton")

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
        self.motor_stop_btn.setStyleSheet("background-color: red; color: white;")  # Red background
        motor_layout.addWidget(self.motor_stop_btn)

        layout.addWidget(motor_group, 0, 2, 2, 1)

    def setup_valve_section(self, layout):
        """Setup valve controls with switchable views."""
        valve_group = QGroupBox()
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
        manual_layout.addWidget(self.dev_checkbox, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Create valve control buttons
        self.valve_buttons = []
        for i in range(5):
            valve_button = QPushButton(f"Valve {i+1}")
            valve_button.setMinimumSize(QSize(0, 30))
            font = QFont()
            font.setPointSize(10)
            valve_button.setFont(font)
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
        self.sequence_status_label.setMinimumHeight(40)  # Give space for wrapped text
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
        valve_layout.addWidget(self.valve_stack, 1)  # Give stack widget stretch
        valve_layout.addWidget(self.reset_button)

        layout.addWidget(valve_group, 1, 0)

        # Set initial stack view to manual mode
        self.valve_stack.setCurrentIndex(0)

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
        # Worker signal connections
        self.arduino_worker.readings_updated.connect(
            self.handle_pressure_readings)
        self.arduino_worker.error_occurred.connect(self.handle_error)
        self.arduino_worker.status_changed.connect(self.handle_status_message)

        self.motor_worker.position_updated.connect(self.handle_position_update)
        self.motor_worker.error_occurred.connect(self.handle_error)
        self.motor_worker.status_changed.connect(self.handle_status_message)

        # Arduino and valve connections
        self.arduino_connect_button.clicked.connect(self.on_ardConnectButton_clicked)
        
        # Valve buttons
        self.Valve1Button.clicked.connect(self.on_Valve1Button_clicked)
        self.Valve2Button.clicked.connect(self.on_Valve2Button_clicked)
        self.Valve3Button.clicked.connect(self.on_Valve3Button_clicked)
        self.Valve4Button.clicked.connect(self.on_Valve4Button_clicked)
        self.Valve5Button.clicked.connect(self.on_Valve5Button_clicked)

        # Quick action buttons
        self.quickVentButton.clicked.connect(self.on_quickVentButton_clicked)
        self.slowVentButton.clicked.connect(self.on_slowVentButton_clicked)
        self.buildPressureButton.clicked.connect(self.on_buildPressureButton_clicked)
        self.switchGasButton.clicked.connect(self.on_switchGasButton_clicked)
        self.quickBubbleButton.clicked.connect(self.on_quickBubbleButton_clicked)

        # Motor control buttons
        self.motor_connect_btn.clicked.connect(self.on_motorConnectButton_clicked)
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
        #self.logger.error(message)
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
                        self.arduino_connect_button.setText("Disconnect")
                        self.arduino_warning_label.setText("")
                        self.arduino_warning_label.setVisible(False)
                        self.set_valve_mode(mode == 1)  # Auto mode if mode == 1
                        
                        # If in automatic mode, start looking for sequence file
                        if mode == 1:
                            self.find_sequence_file()
                            
                        self.logger.info(f"Connected to Arduino in mode {mode}")
                    else:
                        self.handle_error("Failed to connect to Arduino")
                        if not self.test_mode:
                            self.arduino_warning_label.setText("Warning: Arduino not connected")
                            self.arduino_warning_label.setVisible(True)
                except Exception as e:
                    self.handle_error(f"Failed to connect to Arduino: {str(e)}")
                    self.arduino_connect_button.setText("Connect")
                    if not self.test_mode:
                        self.arduino_warning_label.setText("Warning: Arduino not connected")
                        self.arduino_warning_label.setVisible(True)
            else:
                try:
                    self.arduino_worker.stop()
                    self.arduino_connect_button.setText("Connect")
                    if not self.test_mode:
                        self.arduino_warning_label.setText("Warning: Arduino not connected")
                        self.arduino_warning_label.setVisible(True)
                    # Reset to manual mode when disconnecting
                    self.set_valve_mode(False)
                    self.logger.info("Disconnected from Arduino")
                except Exception as e:
                    self.handle_error(f"Error disconnecting Arduino: {str(e)}")
        except Exception as e:
            self.logger.error(f"Uncaught exception in Arduino connection: {str(e)}")
            self.handle_error("An unexpected error occurred while connecting to Arduino")
            self.arduino_connect_button.setText("Connect")
            if not self.test_mode:
                self.arduino_warning_label.setText("Warning: Arduino not connected")
                self.arduino_warning_label.setVisible(True)

    def find_sequence_file(self):
        """Look for sequence file in the specified location."""
        self.file_timer = QTimer()
        self.file_timer.timeout.connect(self.check_sequence_file)
        self.file_timer.start(500)  # Check every 500ms

    def check_sequence_file(self):
        """Check if sequence file exists and load it if found."""
        if Path(r"C:\ssbubble\sequence.txt").exists():
            self.update_sequence_status("Loading sequence")
            self.logger.info("Sequence file found")
            if self.load_sequence():
                self.logger.info("Sequence loaded successfully")
                self.logger.info("Starting sequence")
                
                # Calculate sequence timing
                self.calculate_sequence_time()
                
                # Update UI with first step
                if self.steps:
                    step_type = self.step_types[self.steps[0].step_type]
                    self.update_sequence_info(
                        step_type=step_type,
                        step_time=self.steps[0].time_length,
                        steps_left=len(self.steps),
                        total_time=self.total_sequence_time
                    )
                    self.update_sequence_status("Running")
                
                # Signal success to Prospa
                self.write_to_prospa(True)
                self.delete_sequence_file()
                
                # Start sequence execution
                self.start_sequence()
            else:
                self.update_sequence_status("Error loading sequence")
                self.write_to_prospa(False)
                self.delete_sequence_file()
                self.handle_error("Failed to load sequence")
                
            self.file_timer.stop()
        else:
            if self.arduino_worker.running:
                self.update_sequence_status("Waiting for file")
                self.logger.debug("Sequence file not found, checking again...")

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
            self.arduino_worker.set_valve(1, checked)
            self.logger.info(f"Valve 1 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve2Button_clicked(self, checked: bool):
        """Handle Valve 2 (Inlet valve) button click."""
        if self.arduino_worker.running:
            self.arduino_worker.set_valve(2, checked)
            self.logger.info(f"Valve 2 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve3Button_clicked(self, checked: bool):
        """Handle Valve 3 (Outlet valve) button click."""
        if self.arduino_worker.running:
            self.arduino_worker.set_valve(3, checked)
            self.logger.info(f"Valve 3 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve4Button_clicked(self, checked: bool):
        """Handle Valve 4 (Vent valve) button click."""
        if self.arduino_worker.running:
            self.arduino_worker.set_valve(4, checked)
            self.logger.info(f"Valve 4 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_Valve5Button_clicked(self, checked: bool):
        """Handle Valve 5 (Short valve) button click."""
        if self.arduino_worker.running:
            self.arduino_worker.set_valve(5, checked)
            self.logger.info(f"Valve 5 {'opened' if checked else 'closed'}")

    @pyqtSlot(bool)
    def on_quickVentButton_clicked(self, checked: bool):
        """Handle quick vent button click."""
        if not self.arduino_worker.running:
            return
        
        if checked:
            # Open vent and short valves, close inlet
            self.arduino_worker.set_valve(2, False)  # Close inlet
            self.arduino_worker.set_valve(4, True)   # Open vent
            self.arduino_worker.set_valve(5, True)   # Open short
            self.disable_valve_controls(True)
            self.logger.info("Quick vent started")
        else:
            # Close all valves
            for valve in range(1, 6):
                self.arduino_worker.set_valve(valve, False)
            self.disable_valve_controls(False)
            self.logger.info("Quick vent stopped")

    @pyqtSlot(bool)
    def on_slowVentButton_clicked(self, checked: bool):
        """Handle slow vent button click."""
        if not self.arduino_worker.running:
            return
        
        if checked:
            # Configure valves for slow venting
            self.arduino_worker.set_valve(2, False)  # Close inlet
            self.arduino_worker.set_valve(4, True)   # Open vent
            self.disable_valve_controls(True)
            self.logger.info("Slow vent started")
        else:
            # Close all valves
            for valve in range(1, 6):
                self.arduino_worker.set_valve(valve, False)
            self.disable_valve_controls(False)
            self.logger.info("Slow vent stopped")

    @pyqtSlot(bool)
    def on_buildPressureButton_clicked(self, checked: bool):
        """Handle build pressure button click."""
        if self.arduino_worker.running:
            self.arduino_worker.set_valve(2, checked)  # Toggle inlet valve
            self.logger.info(f"Pressure build {'started' if checked else 'stopped'}")

    @pyqtSlot(bool)
    def on_switchGasButton_clicked(self, checked: bool):
        """Handle switch gas button click."""
        if self.arduino_worker.running:
            self.arduino_worker.set_valve(1, checked)  # Toggle switch valve
            self.logger.info(f"Gas switch {'started' if checked else 'stopped'}")

    @pyqtSlot(bool)
    def on_quickBubbleButton_clicked(self, checked: bool):
        """Handle quick bubble button click."""
        if not self.arduino_worker.running:
            return
        
        if checked:
            duration = self.bubbleTimeDoubleSpinBox.value()
            # Open inlet and outlet valves
            self.arduino_worker.set_valve(2, True)
            self.arduino_worker.set_valve(3, True)
            self.disable_valve_controls(True)
            
            # Start timer to close valves after duration
            QTimer.singleShot(int(duration * 1000), self.stop_bubble)
            self.logger.info(f"Quick bubble started for {duration}s")
        else:
            self.stop_bubble()

    def stop_bubble(self):
        """Stop bubbling sequence."""
        if self.arduino_worker.running:
            # Close all valves
            for valve in range(1, 6):
                self.arduino_worker.set_valve(valve, False)
            self.disable_valve_controls(False)
            self.quickBubbleButton.setChecked(False)
            self.logger.info("Bubble sequence stopped")

    def disable_valve_controls(self, disabled: bool):
        """Enable/disable valve controls."""
        for button in self.valve_buttons:
            button.setEnabled(not disabled)

    @pyqtSlot()
    def on_motorConnectButton_clicked(self):
        """Handle motor connect button click."""
        try:
            if not self.motor_worker.running:
                port = self.motor_com_port_spin.value()
                try:
                    # Create new worker with updated port
                    self.motor_worker = MotorWorker(port=port, mock=self.test_mode)
                    # Reconnect signals
                    self.motor_worker.position_updated.connect(self.handle_position_update)
                    self.motor_worker.error_occurred.connect(self.handle_error)
                    self.motor_worker.status_changed.connect(self.handle_status_message)
                    
                    success = self.motor_worker.start()  # Start the thread
                    if success or self.test_mode:  # Success or test mode
                        self.motor_connect_btn.setText("Disconnect")
                        self.motor_warning_label.setText("")
                        self.motor_warning_label.setVisible(False)
                        self.logger.info(f"Connected to motor on COM{port}")
                    else:
                        self.handle_error("Failed to connect to motor")
                        if not self.test_mode:
                            self.motor_warning_label.setText("Warning: Motor not connected")
                            self.motor_warning_label.setVisible(True)
                except Exception as e:
                    self.handle_error(f"Failed to connect to motor: {str(e)}")
                    self.motor_connect_btn.setText("Connect")
                    if not self.test_mode:
                        self.motor_warning_label.setText("Warning: Motor not connected")
                        self.motor_warning_label.setVisible(True)
            else:
                try:
                    self.motor_worker.stop()
                    self.motor_connect_btn.setText("Connect")
                    if not self.test_mode:
                        self.motor_warning_label.setText("Warning: Motor not connected")
                        self.motor_warning_label.setVisible(True)
                    self.logger.info("Disconnected from motor")
                except Exception as e:
                    self.handle_error(f"Error disconnecting motor: {str(e)}")
        except Exception as e:
            self.logger.error(f"Uncaught exception in motor connection: {str(e)}")
            self.handle_error("An unexpected error occurred while connecting to motor")
            self.motor_connect_btn.setText("Connect")
            if not self.test_mode:
                self.motor_warning_label.setText("Warning: Motor not connected")
                self.motor_warning_label.setVisible(True)

    @pyqtSlot()
    def on_motorCalibrateButton_clicked(self):
        """Handle motor calibration button click."""
        if self.motor_worker.running:
            # Move to position 0 for calibration
            self.motor_worker.move_to(0)
            self.logger.info("Motor calibration started")

    @pyqtSlot()
    def on_motorStopButton_clicked(self):
        """Handle motor emergency stop button click."""
        if self.motor_worker.running:
            self.motor_worker.emergency_stop()
            self.logger.warning("Motor emergency stop activated")

    @pyqtSlot()
    def on_motorMoveToTargetButton_clicked(self):
        """Handle move to target button click."""
        if self.motor_worker.running:
            try:
                target = int(self.target_motor_pos_edit.text())
                self.motor_worker.move_to(target)
                self.logger.info(f"Moving motor to position {target}")
            except ValueError:
                self.handle_error("Invalid target position")

    @pyqtSlot()
    def on_motorAscentButton_clicked(self):
        """Handle motor ascent button click."""
        if self.motor_worker.running:
            # Move to max position for ascent
            self.motor_worker.move_to(self.motor_worker.controller.POSITION_MAX)
            self.logger.info("Motor ascent started")

    @pyqtSlot()
    def on_motorToTopButton_clicked(self):
        """Handle motor to top button click."""
        if self.motor_worker.running:
            # Move to max position
            self.motor_worker.move_to(self.motor_worker.controller.POSITION_MAX)
            self.logger.info("Moving motor to top position")

    @pyqtSlot(int)
    def on_motorMacroButton_clicked(self, macro_num: int):
        """Handle motor macro button click.
        
        Args:
            macro_num: Macro number (1-6)
        """
        if self.motor_worker.running:
            try:
                position = self.macro_manager.get_motor_position(macro_num)
                self.motor_worker.move_to(position)
                self.logger.info(f"Executing motor macro {macro_num}")
            except Exception as e:
                self.handle_error(f"Failed to execute motor macro {macro_num}: {e}")

    @pyqtSlot(bool)
    def on_beginSaveButton_clicked(self, checked: bool):
        """Handle begin save button click."""
        if checked:
            save_path = self.savePathEdit.text()
            if not save_path:
                self.handle_error("Please select a save path first")
                self.beginSaveButton.setChecked(False)
                return
                
            try:
                # Use plot widget's export_data method
                self.plot_widget.export_data()
                self.logger.info(f"Started recording data to {save_path}")
            except Exception as e:
                self.handle_error(f"Failed to start recording: {e}")
                self.beginSaveButton.setChecked(False)
        else:
            self.plot_widget.stop_recording()
            self.logger.info("Stopped recording data")

    @pyqtSlot()
    def on_selectSavePathButton_clicked(self):
        """Handle select save path button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Save Location",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.savePathEdit.setText(file_path)
            self.logger.info(f"Save path set to {file_path}")

    @pyqtSlot(int)
    def on_pressureRadioButton_clicked(self, sensor_num: int):
        """Handle pressure sensor radio button click.
        
        Args:
            sensor_num: Pressure sensor number (1-4)
        """
        radio = getattr(self, f"pressure{sensor_num}RadioButton")
        # Adjust index since plot widget uses 0-based indexing
        if sensor_num <= 3:  # Only first 3 sensors are plotted
            self.plot_widget.sensor_toggles[sensor_num - 1].setChecked(radio.isChecked())
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
                macro = self.macro_manager.get_macro(str(macro_num))
                # Convert macro valve states to list of 8 integers (0/1)
                valve_states = [0 if x == 0 else 1 for x in macro.valve_states]
                self.arduino_worker.set_valves(valve_states)
                
                # If macro has a timer, schedule valve reset
                if macro.timer > 0:
                    QTimer.singleShot(
                        int(macro.timer * 1000), 
                        lambda: self.arduino_worker.set_valves([0] * 8)
                    )
                self.logger.info(f"Executing valve macro {macro_num}")
            except Exception as e:
                self.handle_error(f"Failed to execute valve macro {macro_num}: {e}")

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

    def update_sequence_status(self, status: str):
        """Update sequence status display.
        
        Args:
            status: Status message to display
        """
        self.sequence_status_label.setText(f"Status: {status}")

    def update_sequence_info(self, step_type: str, step_time: float, steps_left: int, total_time: float):
        """Update sequence information displays.
        
        Args:
            step_type: Current step type
            step_time: Time remaining in current step (seconds)
            steps_left: Number of steps remaining
            total_time: Total time remaining in sequence (seconds)
        """
        self.currentStepTypeEdit.setText(step_type)
        self.currentStepTimeEdit.setText(f"{step_time:.1f}s")
        self.stepsRemainingEdit.setText(str(steps_left))
        self.totalTimeEdit.setText(f"{total_time:.1f}s")
