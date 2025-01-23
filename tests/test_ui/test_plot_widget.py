"""
File: test_plot_widget.py
Description: Tests for plot widget
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
import numpy as np

from src.ui.widgets.plot_widget import PlotWidget


@pytest.fixture
def app():
    """Create QApplication instance."""
    return QApplication([])


@pytest.fixture
def plot_widget(app):
    """Create plot widget instance."""
    return PlotWidget(max_points=1000, update_interval=100)


def test_initialization(plot_widget):
    """Test widget initialization."""
    assert plot_widget.max_points == 1000
    assert len(plot_widget.pressures) == 4
    assert len(plot_widget.lines) == 4
    assert plot_widget.recording is False


def test_update_plot(plot_widget):
    """Test plot update with new readings."""
    readings = [1.0, 2.0, 3.0, 4.0]
    plot_widget.update_plot(readings)
    
    assert len(plot_widget.times) == 1
    for i, pressure in enumerate(plot_widget.pressures):
        assert len(pressure) == 1
        assert pressure[0] == readings[i]


def test_clear_data(plot_widget):
    """Test clearing plot data."""
    # Add some data first
    readings = [1.0, 2.0, 3.0, 4.0]
    plot_widget.update_plot(readings)
    
    plot_widget.clear_data()
    assert len(plot_widget.times) == 0
    for pressure in plot_widget.pressures:
        assert len(pressure) == 0


def test_recording(plot_widget, tmp_path):
    """Test data recording functionality."""
    test_file = tmp_path / "test_data.csv"
    
    # Start recording
    assert plot_widget.start_recording(str(test_file)) is True
    assert plot_widget.recording is True
    
    # Add some data
    readings = [1.0, 2.0, 3.0, 4.0]
    plot_widget.update_plot(readings)
    
    # Stop recording
    plot_widget.stop_recording()
    assert plot_widget.recording is False
    
    # Verify file exists and contains data
    assert test_file.exists()
    content = test_file.read_text()
    assert "Time,Sensor1,Sensor2,Sensor3,Sensor4" in content


def test_max_points_limit(plot_widget):
    """Test maximum points limit."""
    # Add more points than max_points
    for i in range(1100):  # max_points is 1000
        plot_widget.update_plot([1.0, 2.0, 3.0, 4.0])
    
    assert len(plot_widget.times) <= plot_widget.max_points
    for pressure in plot_widget.pressures:
        assert len(pressure) <= plot_widget.max_points
