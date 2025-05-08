"""
File: dev_panel.py
Description: Developer panel dialog implementation
"""

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import time


class DevPanel(QDialog):
    """Development panel dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Developer Panel")
        self.setFixedSize(226, 300)
        self.parent = parent
        
        # Set window stylesheet to match main window
        self.setStyleSheet("""
            QPushButton:disabled {
                background-color: grey;
                color: white;
            }
            QSpinBox:disabled {
                background-color: grey;
                color: black;
            }
        """)

        # Create central widget and layout
        central_widget = QWidget(self)
        main_layout = QVBoxLayout(central_widget)

        # Create horizontal layout for step buttons and controls
        h_layout = QHBoxLayout()

        # Create left side step buttons
        step_layout = QVBoxLayout()
        step_layout.setSpacing(0)

        # Step button configurations with commands
        step_buttons = [
            ("+50", "q"),
            ("+10", "w"),
            ("+1", "d"),
            ("-1", "r"),
            ("-10", "f"),
            ("-50", "v")
        ]

        # Create step buttons with consistent font
        button_font = QFont()
        button_font.setPointSize(10)
        
        self.step_buttons = []
        for text, cmd in step_buttons:
            btn = QPushButton(text)
            btn.setFont(button_font)
            btn.setMinimumSize(0, 45)
            btn.setMaximumSize(45, 16777215)
            btn.clicked.connect(lambda checked, c=cmd: self.step_motor(c))
            step_layout.addWidget(btn)
            self.step_buttons.append(btn)

        h_layout.addLayout(step_layout)

        # Create right side controls
        control_layout = QVBoxLayout()
        control_layout.setSpacing(0)

        # Motor limits checkbox
        self.limits_checkbox = QCheckBox("Motor Limits")
        self.limits_checkbox.setFont(button_font)
        self.limits_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.limits_checkbox.setChecked(True)
        self.limits_checkbox.setMinimumHeight(35)
        self.limits_checkbox.toggled.connect(self.toggle_motor_limits)
        control_layout.addWidget(self.limits_checkbox, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Speed controls
        speed_label = QLabel("Motor Speed")
        speed_label.setFont(button_font)
        speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_label.setMaximumHeight(50)
        control_layout.addWidget(speed_label)

        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setFont(button_font)
        self.speed_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.speed_spinbox.setRange(0, 6500)
        control_layout.addWidget(self.speed_spinbox)

        speed_btn = QPushButton("Set Speed")
        speed_btn.setFont(button_font)
        speed_btn.setMinimumHeight(32)
        speed_btn.clicked.connect(self.set_motor_speed)
        control_layout.addWidget(speed_btn)

        # Acceleration controls
        accel_label = QLabel("Motor Accel")
        accel_label.setFont(button_font)
        accel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        accel_label.setMaximumHeight(50)
        control_layout.addWidget(accel_label)

        self.accel_spinbox = QSpinBox()
        self.accel_spinbox.setFont(button_font)
        self.accel_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.accel_spinbox.setRange(0, 23250)
        control_layout.addWidget(self.accel_spinbox)

        accel_btn = QPushButton("Set Accel")
        accel_btn.setFont(button_font)
        accel_btn.setMinimumHeight(32)
        accel_btn.clicked.connect(self.set_motor_accel)
        control_layout.addWidget(accel_btn)

        h_layout.addLayout(control_layout)
        main_layout.addLayout(h_layout)

        self.setLayout(main_layout)

    def check_motor_connection(self) -> bool:
        """Check if motor is connected and running.
        
        Returns:
            bool: True if motor is connected and running, False otherwise
        """
        if not self.parent.motor_worker or not self.parent.motor_worker.running:
            self.parent.logger.error("Please connect the motor before using developer controls")
            return False
        return True

    def step_motor(self, step_char: str):
        """Step the motor by sending step command."""
        if not self.check_motor_connection():
            return
            
        if self.parent.motor_worker.step_motor(step_char):
            self.parent.logger.info(f"Sent motor step command: {step_char}")
        else:
            self.parent.logger.error(f"Failed to send motor step command: {step_char}")

    def toggle_motor_limits(self, enabled: bool):
        """Toggle motor limits."""
        if not self.check_motor_connection():
            # Block signals while resetting checkbox to prevent recursion
            self.limits_checkbox.blockSignals(True)
            self.limits_checkbox.setChecked(not enabled)  # Revert checkbox state
            self.limits_checkbox.blockSignals(False)
            return
            
        self.parent.motor_worker.set_limits_enabled(enabled)
        self.parent.logger.info(f"Motor limits {'enabled' if enabled else 'disabled'}")

    def set_motor_speed(self):
        """Set the motor speed."""
        if not self.check_motor_connection():
            return
            
        speed = self.speed_spinbox.value()
        if self.parent.motor_worker.set_speed(speed):
            self.parent.logger.info(f"Motor speed set to {speed}")
        else:
            self.parent.logger.error("Failed to set motor speed")
            # Disconnect motor on failure
            self.parent.cleanup_motor_worker()
            self.parent.motor_connect_btn.setText("Connect")
            self.parent.motor_warning_label.setText("Warning: Motor not connected")
            self.parent.motor_warning_label.setVisible(True)
            self.parent.disable_motor_controls(True)
            self.close()  # Close dev panel

    def set_motor_accel(self):
        """Set the motor acceleration."""
        if not self.check_motor_connection():
            return
            
        accel = self.accel_spinbox.value()
        if self.parent.motor_worker.set_acceleration(accel):
            self.parent.logger.info(f"Motor acceleration set to {accel}")
        else:
            self.parent.logger.error("Failed to set motor acceleration")
            # Disconnect motor on failure
            self.parent.cleanup_motor_worker()
            self.parent.motor_connect_btn.setText("Connect")
            self.parent.motor_warning_label.setText("Warning: Motor not connected")
            self.parent.motor_warning_label.setVisible(True)
            self.parent.disable_motor_controls(True)
            self.close()  # Close dev panel

    def closeEvent(self, event):
        """Re-enable motor limits and reset speed/acceleration when panel is closed."""
        try:
            if not self.check_motor_connection():
                super().closeEvent(event)
                return
                
            # Reset motor limits
            self.limits_checkbox.setChecked(True)  # Reset checkbox
            self.parent.motor_worker.set_limits_enabled(True)  # Force enable limits
            self.parent.logger.info("Motor limits re-enabled")
            
            # Add delay before speed reset
            time.sleep(0.2)  # 200ms delay
            
            # Reset speed based on main window combo box
            speed_map = {
                'Fast': 6500,    # Maximum speed
                'Medium': 4000,  # 60% speed
                'Slow': 2000     # 30% speed
            }
            selected_speed = self.parent.motor_speed_combo.currentText()
            speed = speed_map.get(selected_speed, 4000)  # Default to Medium if not found
            if self.parent.motor_worker.set_speed(speed):
                self.parent.logger.info(f"Motor speed reset to {selected_speed} ({speed})")
            else:
                self.parent.logger.error("Failed to reset motor speed")
                # Disconnect motor on failure
                self.parent.cleanup_motor_worker()
                self.parent.motor_connect_btn.setText("Connect")
                self.parent.motor_warning_label.setText("Warning: Motor not connected")
                self.parent.motor_warning_label.setVisible(True)
                self.parent.disable_motor_controls(True)
                super().closeEvent(event)
                return
            
            # Add delay before acceleration reset
            time.sleep(0.2)  # 200ms delay
            
            # Reset acceleration to maximum
            if self.parent.motor_worker.set_acceleration(self.parent.motor_worker.controller.ACCEL_MAX):
                self.parent.logger.info(f"Motor acceleration reset to maximum ({self.parent.motor_worker.controller.ACCEL_MAX})")
            else:
                self.parent.logger.error("Failed to reset motor acceleration")
                # Disconnect motor on failure
                self.parent.cleanup_motor_worker()
                self.parent.motor_connect_btn.setText("Connect")
                self.parent.motor_warning_label.setText("Warning: Motor not connected")
                self.parent.motor_warning_label.setVisible(True)
                self.parent.disable_motor_controls(True)
                super().closeEvent(event)
                return
            
            self.parent.logger.info("Motor limits, speed, and acceleration reset on panel close")
            super().closeEvent(event)
            
        except Exception as e:
            self.parent.logger.error(f"Error resetting motor parameters on panel close: {e}")
            # Disconnect motor on any error
            self.parent.cleanup_motor_worker()
            self.parent.motor_connect_btn.setText("Connect")
            self.parent.motor_warning_label.setText("Warning: Motor not connected")
            self.parent.motor_warning_label.setVisible(True)
            self.parent.disable_motor_controls(True)
            super().closeEvent(event) 