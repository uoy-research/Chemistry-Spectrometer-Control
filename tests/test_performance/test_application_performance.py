"""
File: tests/test_performance/test_application_performance.py
"""

import pytest
import time
import psutil
import gc


@pytest.mark.performance
class TestApplicationPerformance:

    @pytest.fixture(autouse=True)
    def setup(self, qapp, test_config, mock_controllers):
        """Setup for performance tests."""
        self.app = MainWindow(config=test_config)
        self.app.arduino_controller = mock_controllers["arduino"]
        self.app.motor_controller = mock_controllers["motor"]
        yield
        self.app.close()
        gc.collect()

    def test_startup_performance(self):
        """Test application startup time."""
        start_time = time.time()
        app = MainWindow(config=test_config)
        startup_time = time.time() - start_time
        assert startup_time < 2.0  # Should start in under 2 seconds
        app.close()

    def test_data_acquisition_performance(self):
        """Test data acquisition speed."""
        start_time = time.time()
        for _ in range(100):
            self.app.update_readings()
        processing_time = time.time() - start_time
        assert processing_time < 1.0  # 100 readings in under 1 second
