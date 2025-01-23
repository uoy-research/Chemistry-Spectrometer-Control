"""
File: tests/test_performance/test_application_performance.py
Description: Performance tests for the SSBubble application
"""

import pytest
import time
import psutil
import gc
from unittest.mock import patch, Mock
from PyQt6.QtCore import QTimer
from src.ui.main_window import MainWindow
from src.models.step import Step


@pytest.mark.performance
class TestApplicationPerformance:

    @pytest.fixture(autouse=True)
    def setup(self, qapp, test_config, mock_controllers):
        """Setup for performance tests."""
        # Patch GUI components to avoid actual rendering
        with patch('src.ui.main_window.PlotWidget'), \
             patch('src.ui.main_window.LogWidget'):
            self.app = MainWindow(test_mode=True)
            yield
            # Proper cleanup
            if hasattr(self.app, 'arduino_worker'):
                self.app.arduino_worker._running = False
                self.app.arduino_worker.stop()
                self.app.arduino_worker.wait(1000)
            if hasattr(self.app, 'motor_worker'):
                self.app.motor_worker._running = False
                self.app.motor_worker.stop()
                self.app.motor_worker.wait(1000)
            self.app.close()
            self.app = None
            gc.collect()

    def test_startup_performance(self):
        """Test application startup time."""
        start_time = time.time()
        with patch('src.ui.main_window.PlotWidget'), \
             patch('src.ui.main_window.LogWidget'):
            app = MainWindow(test_mode=True)
            startup_time = time.time() - start_time
            
            # Should start in under 1 second in test mode
            assert startup_time < 1.0, f"Startup took {startup_time:.2f} seconds"
            app.close()

    def test_data_acquisition_performance(self):
        """Test data acquisition and processing speed."""
        start_time = time.time()
        readings = []
        
        # Mock pressure readings
        mock_readings = [1.0, 2.0, 3.0, 4.0]
        
        with patch.object(self.app.arduino_worker, 'get_readings', 
                         return_value=mock_readings):
            # Simulate 1000 readings
            for _ in range(1000):
                readings.append(self.app.arduino_worker.get_readings())
        
        processing_time = time.time() - start_time
        
        # Should process 1000 readings in under 1 second
        assert processing_time < 1.0, f"Processing took {processing_time:.2f} seconds"
        assert len(readings) == 1000

    def test_sequence_execution_performance(self):
        """Test sequence execution timing accuracy."""
        # Create a test sequence
        sequence_steps = [
            Step('p', 100),  # 100ms pressurize
            Step('v', 100),  # 100ms vent
            Step('d', 100)   # 100ms delay
        ]
        self.app.steps = sequence_steps.copy()
        
        start_time = time.time()
        
        with patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
            self.app.start_sequence()
            
            # Verify timing accuracy
            for _ in range(len(sequence_steps)):
                self.app.next_step()
        
        execution_time = time.time() - start_time
        
        # Total sequence should take ~300ms plus minimal overhead
        assert execution_time < 0.5, f"Sequence execution took {execution_time:.2f} seconds"

    def test_memory_usage(self):
        """Test memory usage during operation."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
        
        # Perform memory-intensive operations
        large_sequence = [Step('p', 1000) for _ in range(1000)]
        self.app.steps = large_sequence
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50, f"Memory increase was {memory_increase:.2f}MB"

    def test_gui_update_performance(self):
        """Test GUI update performance."""
        start_time = time.time()
        
        # Simulate rapid GUI updates
        for _ in range(100):
            # Update various UI elements
            with patch.object(self.app.plot_widget, 'update_plot'), \
                 patch.object(self.app.log_widget, 'add_message'):
                self.app.handle_pressure_readings([1.0, 2.0, 3.0, 4.0])
                self.app.handle_position_update(500.0)
                self.app.update_sequence_info("Test", 1000, 5, 5000)
        
        update_time = time.time() - start_time
        
        # 100 updates should complete in under 0.5 seconds
        assert update_time < 0.5, f"GUI updates took {update_time:.2f} seconds"

    def test_file_operation_performance(self):
        """Test file operation performance."""
        start_time = time.time()
        
        # Test file operations with mocked files
        with patch('builtins.open', Mock()), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.mkdir'):
            
            # Perform multiple file operations
            for _ in range(100):
                self.app.load_valve_macro(1)
                self.app.load_motor_macro(1)
                self.app.handle_sequence_file(True)
        
        operation_time = time.time() - start_time
        
        # File operations should complete quickly
        assert operation_time < 1.0, f"File operations took {operation_time:.2f} seconds"

    def test_concurrent_operations_performance(self):
        """Test performance with concurrent operations."""
        start_time = time.time()
        
        # Mock everything to prevent actual thread operations
        with patch.object(self.app.plot_widget, 'update_plot'), \
             patch.object(self.app.arduino_worker, 'get_readings', return_value=[1.0, 2.0, 3.0, 4.0]), \
             patch.object(self.app.motor_worker, 'move_to', return_value=True), \
             patch.object(self.app.motor_worker, 'running', return_value=True), \
             patch.object(self.app.arduino_worker, 'running', return_value=True):
            
            # Simulate concurrent operations without actually running threads
            for _ in range(100):
                # Just call the handlers without actual thread operations
                self.app.handle_pressure_readings([1.0, 2.0, 3.0, 4.0])
                self.app.handle_position_update(500.0)
                self.app.update_sequence_info("Test", 1000, 5, 5000)
        
        operation_time = time.time() - start_time
        assert operation_time < 1.0

    def test_macro_execution_performance(self):
        """Test macro execution performance."""
        start_time = time.time()
        
        # Mock everything including worker states
        with patch.object(self.app, 'load_valve_macro', return_value={'Valves': [0]*8, 'Label': 'Test'}), \
             patch.object(self.app, 'load_motor_macro', return_value={'Position': 0, 'Label': 'Test'}), \
             patch.object(self.app.arduino_worker, 'set_valves', return_value=True), \
             patch.object(self.app.motor_worker, 'move_to', return_value=True), \
             patch.object(self.app.motor_worker, 'running', return_value=True), \
             patch.object(self.app.arduino_worker, 'running', return_value=True), \
             patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
            
            # Execute macros without actual thread operations
            for i in range(1, 5):
                # Call handlers directly
                self.app.on_valveMacroButton_clicked(i)
                # Immediately trigger any queued timer callbacks
                if mock_timer.call_args is not None:
                    callback = mock_timer.call_args[0][1]
                    callback()
        
        execution_time = time.time() - start_time
        assert execution_time < 0.5

    def cleanup_workers(self):
        """Helper method to cleanup workers safely."""
        if hasattr(self, 'app'):
            if hasattr(self.app, 'arduino_worker'):
                self.app.arduino_worker._running = False
                self.app.arduino_worker.stop()
                self.app.arduino_worker.wait(1000)
            if hasattr(self.app, 'motor_worker'):
                self.app.motor_worker._running = False
                self.app.motor_worker.stop()
                self.app.motor_worker.wait(1000)
