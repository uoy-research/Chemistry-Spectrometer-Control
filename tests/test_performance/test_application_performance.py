"""
File: test_application_performance.py
Description: Performance tests for application workflows
"""

import pytest
import time
from unittest.mock import Mock, patch
import numpy as np
from PyQt6.QtCore import QTimer

from src.ui.main_window import MainWindow


@pytest.fixture
def app_window(qtbot, setup_environment):
    """Create main application window with mocked hardware."""
    config_file, _, log_dir = setup_environment

    with patch('src.utils.config.CONFIG_FILE', str(config_file)), \
            patch('src.utils.logger.LOG_DIR', str(log_dir)):
        window = MainWindow()
        qtbot.addWidget(window)
        return window


def measure_execution_time(func):
    """Decorator to measure execution time."""
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        return result, execution_time
    return wrapper


def test_startup_performance(app_window):
    """Test application startup performance."""
    @measure_execution_time
    def startup_sequence():
        app_window.handle_arduino_connection()
        app_window.handle_motor_connection()

    _, execution_time = startup_sequence()
    assert execution_time < 1.0  # Startup should take less than 1 second


def test_data_acquisition_performance(app_window):
    """Test data acquisition and plotting performance."""
    # Prepare test data
    num_samples = 1000
    test_data = [
        [float(i), float(i+1), float(i+2)]
        for i in range(num_samples)
    ]

    start_time = time.perf_counter()

    # Process data
    for readings in test_data:
        app_window.handle_pressure_readings(readings)

    end_time = time.perf_counter()
    processing_time = end_time - start_time

    # Calculate processing rate
    rate = num_samples / processing_time
    assert rate > 100  # Should handle at least 100 samples per second


def test_plot_update_performance(app_window):
    """Test plot widget update performance."""
    @measure_execution_time
    def update_plot():
        for _ in range(100):
            app_window.plot_widget.update_plot([1.0, 2.0, 3.0])

    _, execution_time = update_plot()
    update_rate = 100 / execution_time
    assert update_rate > 30  # Should maintain at least 30 FPS


def test_macro_execution_performance(app_window):
    """Test macro execution performance."""
    # Create test macro
    with patch.object(app_window.macro_manager, 'get_macro') as mock_get_macro:
        mock_get_macro.return_value = Mock(
            valve_states=[1] * 8,
            timer=0.01,
            label="Test Macro"
        )

        @measure_execution_time
        def execute_macros():
            for _ in range(100):
                app_window.run_macro()

        _, execution_time = execute_macros()
        assert execution_time < 2.0  # Should execute 100 macros in under 2 seconds


def test_motor_control_performance(app_window):
    """Test motor control performance."""
    @measure_execution_time
    def motor_operations():
        for position in range(0, 1000, 100):
            app_window.position_spin.setValue(position)
            app_window.move_motor()

    _, execution_time = motor_operations()
    assert execution_time < 1.0  # Motor commands should be processed quickly


def test_memory_usage(app_window):
    """Test memory usage during extended operation."""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Generate load
    for _ in range(1000):
        app_window.handle_pressure_readings([1.0, 2.0, 3.0])

    final_memory = process.memory_info().rss
    memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

    assert memory_increase < 50  # Should not increase by more than 50MB


def test_concurrent_operation_performance(app_window):
    """Test performance under concurrent operations."""
    @measure_execution_time
    def concurrent_operations():
        # Simulate concurrent activities
        app_window.run_macro()
        app_window.move_motor()
        app_window.handle_pressure_readings([1.0, 2.0, 3.0])

    _, execution_time = concurrent_operations()
    assert execution_time < 0.1  # Should handle concurrent ops quickly


def test_data_export_performance(app_window, tmp_path):
    """Test data export performance."""
    # Generate test data
    for _ in range(1000):
        app_window.handle_pressure_readings([1.0, 2.0, 3.0])

    export_file = tmp_path / "test_export.csv"

    @measure_execution_time
    def export_data():
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
                   return_value=(str(export_file), None)):
            app_window.plot_widget.export_data()

    _, execution_time = export_data()
    assert execution_time < 1.0  # Should export quickly


def test_ui_responsiveness(app_window, qtbot):
    """Test UI responsiveness under load."""
    event_times = []

    def record_event_time():
        event_times.append(time.perf_counter())

    # Create timer for UI events
    timer = QTimer()
    timer.timeout.connect(record_event_time)
    timer.start(16)  # ~60 FPS

    # Generate load
    for _ in range(100):
        app_window.handle_pressure_readings([1.0, 2.0, 3.0])
        qtbot.wait(16)

    # Calculate frame times
    frame_times = np.diff(event_times)
    assert np.mean(frame_times) < 0.020  # Average frame time under 20ms


def test_log_performance(app_window):
    """Test logging performance."""
    @measure_execution_time
    def log_messages():
        for i in range(1000):
            app_window.log_widget.add_message(f"Test message {i}", "INFO")

    _, execution_time = log_messages()
    message_rate = 1000 / execution_time
    assert message_rate > 500  # Should log at least 500 messages per second


def test_valve_control_performance(app_window):
    """Test valve control performance."""
    @measure_execution_time
    def valve_operations():
        for _ in range(100):
            app_window.arduino_worker.set_valves([1] * 8)
            app_window.arduino_worker.set_valves([0] * 8)

    _, execution_time = valve_operations()
    operation_rate = 200 / execution_time  # 200 operations (100 * 2)
    assert operation_rate > 100  # Should handle at least 100 valve operations per second


def test_error_handling_performance(app_window):
    """Test error handling performance under load."""
    @measure_execution_time
    def generate_errors():
        for _ in range(100):
            app_window.handle_error(f"Test error {_}")

    _, execution_time = generate_errors()
    assert execution_time < 1.0  # Should handle errors quickly


def test_config_update_performance(app_window):
    """Test configuration update performance."""
    @measure_execution_time
    def update_config():
        for i in range(100):
            app_window.config.update_interval = i
            app_window.config.save()

    _, execution_time = update_config()
    assert execution_time < 1.0  # Config updates should be quick
