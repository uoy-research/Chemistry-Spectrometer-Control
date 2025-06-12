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
        self.ax.set_ylabel('Pressure (bar)')
        self.ax.set_xlabel('Time (s)')

        # Initialize data
        self.times = np.array([])
        self.pressures = [np.array([]) for _ in range(4)]
        self.labels = ['Rig', 'Inlet', 'Tube', 'Outlet']
        self.lines = [self.ax.plot([], [], label=f'{self.labels[i]}')[0]
                      for i in range(4)]

        # Track sensor visibility
        self.sensor_visibility = [True] * 4  # All sensors visible by default

        # Add legend with fixed position in top left
        self.ax.legend(
            loc='upper left',  # Position in upper left
            # Fine-tune the position (x=0.02, y=0.98)
            bbox_to_anchor=(0.02, 0.98),
            ncol=2,  # Arrange in 2 columns
            fontsize='small',  # Smaller font size
            framealpha=0.8,  # Slight transparency
            edgecolor='none'  # No edge color
        )

        # Create toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Setup layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # Set up update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(update_interval)

        self.max_points = max_points
        self.start_time = time.time()

        self.recording = False
        self.save_file = None
        self.csv_writer = None

        self.logger = logging.getLogger(__name__)

    def set_sensor_visibility(self, sensor_num: int, visible: bool):
        """Set visibility of a sensor's plot line.

        Args:
            sensor_num: Sensor number (1-4)
            visible: True to show, False to hide
        """
        try:
            idx = sensor_num - 1  # Convert to 0-based index
            if 0 <= idx < len(self.lines):
                self.sensor_visibility[idx] = visible
                self.lines[idx].set_visible(visible)
                self.canvas.draw()
                self.logger.info(
                    f"Sensor {sensor_num} visibility set to {visible}")
        except Exception as e:
            self.logger.error(f"Error setting sensor visibility: {e}")

    def update_plot(self, readings=None):
        """Update plot with new readings and save if recording."""
        if readings is None:
            return

        # Add comprehensive debug logging
        self.logger.debug(
            f"Update plot called - recording={self.recording}, has_writer={self.csv_writer is not None}")
        self.logger.debug(f"Readings received: {readings}")

        current_time = time.time() - self.start_time

        # Add new data point
        self.times = np.append(self.times, current_time)
        for i, reading in enumerate(readings):
            self.pressures[i] = np.append(self.pressures[i], reading)

        # Save data if recording
        if self.recording and self.csv_writer:
            try:
                row = [current_time] + readings
                self.logger.debug(f"Writing row to CSV: {row}")
                self.csv_writer.writerow(row)
                self.save_file.flush()  # Ensure data is written to disk
            except Exception as e:
                self.logger.error(f"Error writing data: {e}")
                # Add detailed error info
                self.logger.error(
                    f"CSV writer state: recording={self.recording}, writer={self.csv_writer}, file={self.save_file}")

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
            # Apply visibility setting
            line.set_visible(self.sensor_visibility[i])

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

            # Get save location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Data",
                "",
                "CSV Files (*.csv)"
            )

            if filename:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    # Write header
                    writer.writerow(
                        ['Time', 'Sensor1', 'Sensor2', 'Sensor3', 'Sensor4'])

                    # Write data rows
                    for i in range(len(self.times)):
                        row = [self.times[i]] + [self.pressures[j][i]
                                                 for j in range(4)]
                        writer.writerow(row)

                self.logger.info(f"Data exported to {filename}")

        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")

    def set_update_interval(self, interval: int):
        """Set plot update interval."""
        self.update_interval = interval

    def start_recording(self, filepath: str):
        """Start recording data to CSV file."""
        try:
            self.logger.info(f"Attempting to start recording to {filepath}")

            # Check if already recording to the same file
            if self.recording and self.save_file and self.save_file.name == filepath:
                self.logger.info(
                    "Already recording to the same file - continuing")
                return True

            # Check if already recording to a different file
            if self.recording:
                self.logger.warning(
                    "Already recording to a different file - stopping current recording")
                self.stop_recording()

            # Reset start time and clear plot data
            self.start_time = time.time()
            self.clear_plot(reset_time=False)  # Don't reset time again since we just did

            # Verify file path
            if not filepath:
                self.logger.error("Empty file path provided")
                return False

            self.save_file = open(filepath, 'w', newline='')
            self.csv_writer = csv.writer(self.save_file)

            # Write header
            header = ['Time', 'Rig', 'Inlet', 'Tube', 'Outlet']
            self.logger.debug(f"Writing CSV header: {header}")
            self.csv_writer.writerow(header)

            # Add a small delay to ensure clean timing
            time.sleep(0.1)  # 100ms delay, adjust this if anomaly persists

            self.recording = True

            # Verify recording state
            self.logger.info(
                f"Recording started successfully - recording={self.recording}, has_writer={self.csv_writer is not None}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            # Add error state info
            self.logger.error(
                f"Error state: recording={getattr(self, 'recording', None)}, writer={getattr(self, 'csv_writer', None)}")
            return False

    def stop_recording(self):
        """Stop recording data."""
        self.logger.info("Stopping recording...")
        if self.recording:
            self.recording = False
            if self.save_file:
                try:
                    self.save_file.flush()  # Ensure all data is written
                    self.save_file.close()
                    self.logger.info("Recording stopped and file closed")
                except Exception as e:
                    self.logger.error(f"Error closing save file: {e}")
                finally:
                    self.save_file = None
                    self.csv_writer = None

    def clear_plot(self, reset_time=False):
        """Clear all plot data and optionally reset the time.

        Args:
            reset_time: If True, resets the start_time. Default is False to maintain time continuity.
        """
        try:
            # Clear data arrays
            self.times = np.array([])
            self.pressures = [np.array([]) for _ in range(4)]

            # Only reset start time if explicitly requested
            if reset_time:
                self.start_time = time.time()
                self.logger.info("Plot time was reset")

            # Clear line data
            for line in self.lines:
                line.set_data([], [])

            # Force redraw
            self.canvas.draw()
            self.logger.info("Plot data cleared")

        except Exception as e:
            self.logger.error(f"Error clearing plot: {e}")
