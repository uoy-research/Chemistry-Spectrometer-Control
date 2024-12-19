"""
File: plot_widget.py
Description: Real-time pressure plotting widget
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from collections import deque
from typing import List, Deque
import logging
import time  # Add this import at the top


class PlotWidget(QWidget):
    """
    Widget for real-time pressure data plotting.
    
    Attributes:
        max_points (int): Maximum number of points to display
        update_interval (int): Plot update interval in ms
    """

    def __init__(self, max_points: int = 1000, update_interval: int = 100):
        """Initialize plot widget."""
        super().__init__()

        self.max_points = max_points
        self.update_interval = update_interval

        # Initialize data storage
        self.timestamps: Deque[float] = deque(maxlen=max_points)
        self.pressure_data: List[Deque[float]] = [
            deque(maxlen=max_points) for _ in range(3)
        ]

        self.start_time = time.time()
        self.setup_ui()
        self.logger = logging.getLogger(__name__)

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')  # White background
        self.plot_widget.setTitle("Pressure Readings")
        self.plot_widget.setLabel('left', "Pressure", units='bar')
        self.plot_widget.setLabel('bottom', "Time", units='s')
        self.plot_widget.showGrid(x=True, y=True)

        # Create plot curves
        self.curves = []
        colors = ['b', 'r', 'g']  # Blue, Red, Green for different sensors
        names = ['Sensor 1', 'Sensor 2', 'Sensor 3']

        for color, name in zip(colors, names):
            curve = self.plot_widget.plot(
                pen=pg.mkPen(color=color, width=2),
                name=name
            )
            self.curves.append(curve)

        # Add legend
        self.plot_widget.addLegend()

        # Create control panel
        control_panel = QHBoxLayout()

        # Sensor visibility toggles
        self.sensor_toggles = []
        for i, name in enumerate(names):
            toggle = QCheckBox(name)
            toggle.setChecked(True)
            toggle.stateChanged.connect(self.update_visibility)
            self.sensor_toggles.append(toggle)
            control_panel.addWidget(toggle)

        # Add clear and export buttons
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_data)
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_data)

        control_panel.addStretch()
        control_panel.addWidget(self.clear_btn)
        control_panel.addWidget(self.export_btn)

        # Add auto-range toggle
        self.autorange_cb = QCheckBox("Auto Range")
        self.autorange_cb.setChecked(True)
        control_panel.addWidget(self.autorange_cb)

        # Add widgets to layout
        layout.addWidget(self.plot_widget)
        layout.addLayout(control_panel)

    def update_plot(self, readings: List[float]):
        """
        Update plot with new readings.
        
        Args:
            readings: List of pressure readings from sensors
        """
        try:
            # Add new data points
            current_time = time.time() - self.start_time
            self.timestamps.append(current_time)

            for i, reading in enumerate(readings):
                self.pressure_data[i].append(reading)

            # Update plot curves
            for i, curve in enumerate(self.curves):
                if self.sensor_toggles[i].isChecked():
                    curve.setData(
                        x=list(self.timestamps),
                        y=list(self.pressure_data[i])
                    )

            # Update range if auto-range is enabled
            if self.autorange_cb.isChecked():
                self.plot_widget.enableAutoRange()

        except Exception as e:
            self.logger.error(f"Error updating plot: {e}")

    def clear_data(self):
        """Clear all plot data."""
        try:
            # Clear data storage
            self.timestamps.clear()
            for data in self.pressure_data:
                data.clear()

            # Reset start time
            self.start_time = time.time()

            # Update plot
            for curve in self.curves:
                curve.clear()

            self.logger.info("Plot data cleared")

        except Exception as e:
            self.logger.error(f"Error clearing plot: {e}")

    def update_visibility(self):
        """Update curve visibility based on checkboxes."""
        try:
            for i, (curve, toggle) in enumerate(zip(self.curves, self.sensor_toggles)):
                curve.setVisible(toggle.isChecked())

        except Exception as e:
            self.logger.error(f"Error updating visibility: {e}")

    def export_data(self):
        """Export plot data to CSV file."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import pandas as pd

            # Create DataFrame
            data = {
                'Time': list(self.timestamps),
                'Sensor1': list(self.pressure_data[0]),
                'Sensor2': list(self.pressure_data[1]),
                'Sensor3': list(self.pressure_data[2])
            }
            df = pd.DataFrame(data)

            # Get save location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Data",
                "",
                "CSV Files (*.csv)"
            )

            if filename:
                df.to_csv(filename, index=False)
                self.logger.info(f"Data exported to {filename}")

        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")

    def set_update_interval(self, interval: int):
        """Set plot update interval."""
        self.update_interval = interval

    def set_max_points(self, points: int):
        """Set maximum number of displayed points."""
        try:
            self.max_points = points

            # Update deque maxlen
            new_timestamps = deque(self.timestamps, maxlen=points)
            new_pressure_data = [
                deque(data, maxlen=points)
                for data in self.pressure_data
            ]

            # Replace data storage
            self.timestamps = new_timestamps
            self.pressure_data = new_pressure_data

            self.logger.info(f"Max points set to {points}")

        except Exception as e:
            self.logger.error(f"Error setting max points: {e}")
