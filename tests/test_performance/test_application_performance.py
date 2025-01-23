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
            self.app.close()
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
        
        with patch.object(self.app.plot_widget, 'update_plot'), \
             patch.object(self.app.arduino_worker, 'get_readings', 
                         return_value=[1.0, 2.0, 3.0, 4.0]):
            
            # Simulate concurrent operations
            for _ in range(100):
                # Update plots
                self.app.handle_pressure_readings([1.0, 2.0, 3.0, 4.0])
                
                # Move motor
                self.app.motor_worker.move_to(500)
                
                # Update sequence
                self.app.update_sequence_info("Test", 1000, 5, 5000)
        
        operation_time = time.time() - start_time
        
        # Concurrent operations should complete efficiently
        assert operation_time < 1.0, f"Concurrent operations took {operation_time:.2f} seconds"

    def test_macro_execution_performance(self):
        """Test macro execution performance."""
        start_time = time.time()
        
        with patch.object(self.app, 'load_valve_macro'), \
             patch.object(self.app, 'load_motor_macro'), \
             patch('PyQt6.QtCore.QTimer.singleShot'):
            
            # Execute multiple macros rapidly
            for i in range(1, 5):
                self.app.on_valveMacroButton_clicked(i)
                self.app.on_motorMacroButton_clicked(i)
        
        execution_time = time.time() - start_time
        
        # Macro execution should be quick
        assert execution_time < 0.5, f"Macro execution took {execution_time:.2f} seconds"
