"""
File: main_window.py
Description: Main application window implementation
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QGroupBox, QMenuBar,
    QStatusBar, QMessageBox, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize
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
        self.setFixedSize(1050, 680)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)

        # Create top section (y < 300)
        self.setup_arduino_section(main_layout)
        self.setup_feedback_section(main_layout)
        self.setup_motor_section(main_layout)
        self.setup_motor_position_section(main_layout)
        self.setup_motor_macro_section(main_layout)

        # Create bottom section (y > 300)
        self.setup_valve_section(main_layout)
        self.setup_graph_section(main_layout)
        self.setup_monitor_section(main_layout)

        # Create menu and status bars
        self.setup_menu_bar()
        self.setup_status_bar()

    def setup_arduino_section(self, layout):
        """Setup Arduino connection controls."""
        arduino_group = QGroupBox("Arduino Connection")
        arduino_layout = QVBoxLayout(arduino_group)
        arduino_layout.setContentsMargins(0, 0, 0, 0)

        self.arduino_port_label = QLabel("Port:")
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

        self.arduino_auto_connect_radio = QRadioButton("Auto Connect")
        self.arduino_auto_connect_radio.setChecked(True)
        self.arduino_ttl_radio = QRadioButton("TTL")
        self.arduino_ttl_radio.setChecked(False)
        self.arduino_manual_radio = QRadioButton("Manual")
        self.arduino_manual_radio.setChecked(False)

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
        layout.addWidget(arduino_group, 0, 0)

    def setup_feedback_section(self, layout):
        """Setup feedback display area."""
        feedback_group = QGroupBox("System Feedback")
        feedback_layout = QVBoxLayout(feedback_group)

        self.log_widget = LogWidget()
        feedback_layout.addWidget(self.log_widget)

        layout.addWidget(feedback_group, 0, 1)

    def setup_motor_section(self, layout):
        """Setup motor controls."""
        motor_group = QGroupBox("Motor Control")
        motor_layout = QVBoxLayout(motor_group)

        self.motor_connect_btn = QPushButton("Connect Motor")
        self.motor_connect_btn.clicked.connect(self.handle_motor_connection)

        motor_layout.addWidget(self.motor_connect_btn)
        layout.addWidget(motor_group, 0, 2)

    def setup_valve_section(self, layout):
        """Setup valve controls."""
        valve_group = QGroupBox("Valve Control")
        valve_layout = QVBoxLayout(valve_group)

        # Add valve controls here
        layout.addWidget(valve_group, 1, 0)

    def setup_graph_section(self, layout):
        """Setup graph display."""
        graph_group = QGroupBox("Pressure Monitor")
        graph_layout = QVBoxLayout(graph_group)

        self.plot_widget = PlotWidget(
            max_points=self.config.max_data_points,
            update_interval=self.config.update_interval
        )
        graph_layout.addWidget(self.plot_widget)

        layout.addWidget(graph_group, 1, 1, 1, 2)

    def setup_monitor_section(self, layout):
        """Setup monitoring controls."""
        monitor_group = QGroupBox("System Monitor")
        monitor_layout = QVBoxLayout(monitor_group)

        # Add monitoring controls here
        layout.addWidget(monitor_group, 1, 3)

    def setup_motor_position_section(self, layout):
        """Setup motor position controls."""
        position_group = QGroupBox("Motor Position")
        position_layout = QVBoxLayout(position_group)

        self.position_spin = QSpinBox()
        self.position_spin.setRange(0, 1000)
        self.move_btn = QPushButton("Move")
        self.move_btn.clicked.connect(self.move_motor)

        position_layout.addWidget(self.position_spin)
        position_layout.addWidget(self.move_btn)

        layout.addWidget(position_group, 0, 3)

    def setup_motor_macro_section(self, layout):
        """Setup motor macro controls."""
        macro_group = QGroupBox("Motor Macros")
        macro_layout = QVBoxLayout(macro_group)

        self.edit_macro_btn = QPushButton("Edit Macros")
        self.edit_macro_btn.clicked.connect(self.edit_macros)

        macro_layout.addWidget(self.edit_macro_btn)
        layout.addWidget(macro_group, 0, 4)

    def setup_menu_bar(self):
        """Setup application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        macro_action = tools_menu.addAction("Macro Editor")
        macro_action.triggered.connect(self.edit_macros)

    def setup_status_bar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")

    def setup_connections(self):
        """Setup signal connections."""
        # Arduino worker connections
        self.arduino_worker.readings_updated.connect(
            self.handle_pressure_readings)
        self.arduino_worker.error_occurred.connect(self.handle_error)
        self.arduino_worker.status_changed.connect(self.handle_status_message)

        # Motor worker connections
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
            # Stop workers
            self.arduino_worker.stop()
            self.motor_worker.stop()

            # Save configuration
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
        # Update configuration
        self.config.arduino_port = port
        self.config.save()
        
        # Update worker port
        if self.arduino_worker.running:
            self.arduino_worker.stop()
            self.arduino_connect_button.setText("Connect")
            self.logger.info("Disconnected from Arduino due to port change")
        
        self.arduino_worker = ArduinoWorker(port=f"COM{port}")
        self.setup_connections()  # Reconnect signals
        self.logger.info(f"Arduino port updated to COM{port}")
