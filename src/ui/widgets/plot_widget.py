"""
File: plot_widget.py
Description: Real-time pressure plotting widget
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox
from PyQt6.QtCore import QTimer
import numpy as np
import time
import logging
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import matplotlib
import csv
matplotlib.use('QtAgg')


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

        # Create matplotlib figure
        self.figure = Figure(figsize=(6, 3))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)

        # Set fixed axis limits
        self.ax.set_xlim(-30, 0)  # Show last 30 seconds
        self.ax.set_ylim(-0.1, 11)  # Set y-axis from -0.1 to 11
        self.ax.set_autoscalex_on(False)  # Disable auto-scaling for x-axis
        self.ax.set_autoscaley_on(False)  # Disable auto-scaling for y-axis

        # Initialize other plot settings
        self.ax.grid(True)
        self.ax.set_ylabel('Pressure')
        self.ax.set_xlabel('Time (s)')

        # Create toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Setup layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # Initialize data
        self.times = np.array([])
        self.pressures = [np.array([]) for _ in range(4)]
        self.lines = [self.ax.plot([], [], label=f'Sensor {i+1}')[0]
                      for i in range(4)]

        # Add legend
        self.ax.legend()

        # Set up update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(update_interval)

        self.max_points = max_points
        self.start_time = time.time()

        self.recording = False
        self.save_file = None
        self.csv_writer = None

    def update_plot(self, readings=None):
        """Update plot with new readings and save if recording."""
        if readings is None:
            return

        current_time = time.time() - self.start_time

        # Add new data point
        self.times = np.append(self.times, current_time)
        for i, reading in enumerate(readings):
            self.pressures[i] = np.append(self.pressures[i], reading)

        # Save data if recording
        if self.recording and self.csv_writer:
            self.csv_writer.writerow([current_time] + readings)
            self.save_file.flush()  # Ensure data is written to disk

        # Remove old data points
        if len(self.times) > self.max_points:
            self.times = self.times[-self.max_points:]
            for i in range(4):
                self.pressures[i] = self.pressures[i][-self.max_points:]

        # Update x-axis to maintain 30-second window
        self.ax.set_xlim(current_time - 30, current_time)

        # Update line data
        for i, line in enumerate(self.lines):
            line.set_data(self.times, self.pressures[i])

        # Force a redraw
        self.canvas.draw()

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
                'Sensor3': list(self.pressure_data[2]),
                'Sensor4': list(self.pressure_data[3])
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

    def start_recording(self, filepath: str):
        """Start recording data to CSV file."""
        try:
            self.save_file = open(filepath, 'w', newline='')
            self.csv_writer = csv.writer(self.save_file)
            # Write header
            self.csv_writer.writerow(
                ['Time'] + [f'Sensor{i+1}' for i in range(4)])
            self.recording = True
            self.start_time = time.time()  # Reset start time for recording
            return True
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            return False

    def stop_recording(self):
        """Stop recording data."""
        if self.recording:
            self.recording = False
            if self.save_file:
                self.save_file.close()
                self.save_file = None
                self.csv_writer = None
