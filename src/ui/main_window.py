"""
File: main_window.py
Description: Main application window implementation
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSpinBox,
    QGroupBox, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer
import logging

from src.ui.widgets.plot_widget import PlotWidget
from src.ui.widgets.log_widget import LogWidget
from src.ui.dialogs.macro_editor import MacroEditor
from src.workers.arduino_worker import ArduinoWorker
from src.workers.motor_worker import MotorWorker
from src.models.valve_macro import MacroManager
from src.utils.config import Config


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        self.setWindowTitle("SSBubble Control")
        self.resize(1200, 800)

        # Initialize components
        self.config = Config()
        self.macro_manager = MacroManager(self.config.macro_file)
        self.setup_logging()

        # Create workers
        self.arduino_worker = ArduinoWorker(
            port=self.config.arduino_port
        )
        self.motor_worker = MotorWorker(
            port=self.config.motor_port
        )

        # Setup UI
        self.setup_ui()
        self.setup_connections()

        # Start workers
        self.arduino_worker.start()
        self.motor_worker.start()

        self.logger.info("Application started")

    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def setup_ui(self):
        """Setup user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QHBoxLayout(central_widget)

        # Create left panel (controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.create_connection_group())
        left_layout.addWidget(self.create_valve_group())
        left_layout.addWidget(self.create_motor_group())
        left_layout.addStretch()
        left_layout.addWidget(self.create_emergency_group())

        # Create right panel (data display)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Create tab widget for plots and logs
        tab_widget = QTabWidget()
        self.plot_widget = PlotWidget()
        self.log_widget = LogWidget()

        tab_widget.addTab(self.plot_widget, "Pressure Plot")
        tab_widget.addTab(self.log_widget, "Log")

        right_layout.addWidget(tab_widget)

        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

    def create_connection_group(self) -> QGroupBox:
        """Create connection control group."""
        group = QGroupBox("Connections")
        layout = QVBoxLayout(group)

        # Arduino connection
        arduino_layout = QHBoxLayout()
        self.arduino_status = QLabel("Arduino: Not Connected")
        self.arduino_connect_btn = QPushButton("Connect")
        arduino_layout.addWidget(self.arduino_status)
        arduino_layout.addWidget(self.arduino_connect_btn)

        # Motor connection
        motor_layout = QHBoxLayout()
        self.motor_status = QLabel("Motor: Not Connected")
        self.motor_connect_btn = QPushButton("Connect")
        motor_layout.addWidget(self.motor_status)
        motor_layout.addWidget(self.motor_connect_btn)

        layout.addLayout(arduino_layout)
        layout.addLayout(motor_layout)

        return group

    def create_valve_group(self) -> QGroupBox:
        """Create valve control group."""
        group = QGroupBox("Valve Control")
        layout = QVBoxLayout(group)

        # Macro selection
        macro_layout = QHBoxLayout()
        self.macro_combo = QComboBox()
        self.macro_edit_btn = QPushButton("Edit Macros")
        macro_layout.addWidget(QLabel("Macro:"))
        macro_layout.addWidget(self.macro_combo)
        macro_layout.addWidget(self.macro_edit_btn)

        # Macro controls
        control_layout = QHBoxLayout()
        self.macro_run_btn = QPushButton("Run")
        self.macro_stop_btn = QPushButton("Stop")
        control_layout.addWidget(self.macro_run_btn)
        control_layout.addWidget(self.macro_stop_btn)

        layout.addLayout(macro_layout)
        layout.addLayout(control_layout)

        return group

    def create_motor_group(self) -> QGroupBox:
        """Create motor control group."""
        group = QGroupBox("Motor Control")
        layout = QVBoxLayout(group)

        # Position control
        position_layout = QHBoxLayout()
        self.position_spin = QSpinBox()
        self.position_spin.setRange(0, 1000)
        self.move_btn = QPushButton("Move")
        self.home_btn = QPushButton("Home")
        position_layout.addWidget(QLabel("Position:"))
        position_layout.addWidget(self.position_spin)
        position_layout.addWidget(self.move_btn)
        position_layout.addWidget(self.home_btn)

        # Speed control
        speed_layout = QHBoxLayout()
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(0, 1000)
        self.speed_set_btn = QPushButton("Set Speed")
        speed_layout.addWidget(QLabel("Speed:"))
        speed_layout.addWidget(self.speed_spin)
        speed_layout.addWidget(self.speed_set_btn)

        layout.addLayout(position_layout)
        layout.addLayout(speed_layout)

        return group

    def create_emergency_group(self) -> QGroupBox:
        """Create emergency control group."""
        group = QGroupBox("Emergency Controls")
        layout = QHBoxLayout(group)

        self.emergency_btn = QPushButton("EMERGENCY STOP")
        self.emergency_btn.setStyleSheet(
            "background-color: red; color: white;")
        self.emergency_btn.setMinimumHeight(50)

        layout.addWidget(self.emergency_btn)

        return group

    def setup_connections(self):
        """Setup signal/slot connections."""
        # Arduino worker connections
        self.arduino_worker.readings_updated.connect(
            self.plot_widget.update_plot)
        self.arduino_worker.error_occurred.connect(self.handle_error)
        self.arduino_worker.status_changed.connect(self.update_arduino_status)

        # Motor worker connections
        self.motor_worker.position_updated.connect(
            self.update_position_display)
        self.motor_worker.error_occurred.connect(self.handle_error)
        self.motor_worker.status_changed.connect(self.update_motor_status)

        # Button connections
        self.arduino_connect_btn.clicked.connect(self.toggle_arduino)
        self.motor_connect_btn.clicked.connect(self.toggle_motor)
        self.macro_edit_btn.
