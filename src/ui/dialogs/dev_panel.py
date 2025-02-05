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

        # Step button configurations
        step_buttons = [
            ("+50", 50),
            ("+10", 10),
            ("+1", 1),
            ("-1", -1),
            ("-10", -10),
            ("-50", -50)
        ]

        # Create step buttons with consistent font
        button_font = QFont()
        button_font.setPointSize(10)
        
        self.step_buttons = []
        for text, step in step_buttons:
            btn = QPushButton(text)
            btn.setFont(button_font)
            btn.setMinimumSize(0, 45)
            btn.setMaximumSize(45, 16777215)
            btn.clicked.connect(lambda checked, s=step: self.step_motor(s))
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
        self.accel_spinbox.setRange(0, 6500)
        control_layout.addWidget(self.accel_spinbox)

        accel_btn = QPushButton("Set Accel")
        accel_btn.setFont(button_font)
        accel_btn.setMinimumHeight(32)
        accel_btn.clicked.connect(self.set_motor_accel)
        control_layout.addWidget(accel_btn)

        h_layout.addLayout(control_layout)
        main_layout.addLayout(h_layout)

        self.setLayout(main_layout)

    def step_motor(self, step_size: int):
        """Step the motor by the given amount (placeholder)."""
        self.parent.logger.info(f"Step motor by {step_size} (not implemented)")
        # TODO: Implement motor stepping

    def toggle_motor_limits(self, enabled: bool):
        """Toggle motor limits (placeholder)."""
        self.parent.logger.info(
            f"Motor limits {'enabled' if enabled else 'disabled'} (not implemented)")
        # TODO: Implement motor limits toggle

    def set_motor_speed(self):
        """Set the motor speed."""
        speed = self.speed_spinbox.value()
        if self.parent.motor_worker.set_speed(speed):
            self.parent.logger.info(f"Motor speed set to {speed}")
        else:
            self.parent.logger.error("Failed to set motor speed")

    def set_motor_accel(self):
        """Set the motor acceleration (placeholder)."""
        accel = self.accel_spinbox.value()
        self.parent.logger.info(f"Set motor acceleration to {accel} (not implemented)")
        # TODO: Implement motor acceleration setting 