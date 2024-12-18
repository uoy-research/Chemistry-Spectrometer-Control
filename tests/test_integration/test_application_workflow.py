"""
File: test_application_workflow.py
"""

# ... (keep existing imports and fixtures) ...


def test_calibration_workflow(app_window, qtbot):
    """Test complete calibration workflow."""
    # Connect devices
    app_window.handle_arduino_connection()
    app_window.handle_motor_connection()

    # Perform zero calibration
    with patch.object(app_window.arduino_worker, 'get_readings',
                      return_value=[0.0, 0.0, 0.0]):
        app_window.calibrate_sensors()

        # Verify calibration values stored
        assert all(offset == 0.0 for offset in app_window.sensor_offsets)

        # Verify calibration logged
        assert "calibration" in app_window.log_widget.log_display.toPlainText().lower()


def test_step_sequence_workflow(app_window, qtbot):
    """Test step-by-step sequence workflow."""
    # Create test steps
    steps = [
        Step(position=100, valve_states=[
             1, 0, 1, 0, 1, 0, 1, 0], duration=1.0),
        Step(position=200, valve_states=[
             0, 1, 0, 1, 0, 1, 0, 1], duration=1.0),
        Step(position=300, valve_states=[1, 1, 0, 0, 1, 1, 0, 0], duration=1.0)
    ]

    # Execute sequence
    for step in steps:
        # Move to position
        app_window.position_spin.setValue(step.position)
        app_window.move_motor()

        # Set valve states
        app_window.arduino_worker.set_valves(step.valve_states)

        # Simulate readings
        app_window.handle_pressure_readings([1.0, 2.0, 3.0])

        # Verify step execution
        assert app_window.motor_worker.current_position == step.position
        assert app_window.arduino_worker.last_valve_states == step.valve_states


def test_data_analysis_workflow(app_window, qtbot):
    """Test data analysis and visualization workflow."""
    # Generate test data
    test_data = [
        [1.0, 1.5, 2.0],
        [2.0, 2.5, 3.0],
        [3.0, 3.5, 4.0]
    ]

    # Process data
    for readings in test_data:
        app_window.handle_pressure_readings(readings)

    # Verify plot features
    plot = app_window.plot_widget
    assert len(plot.timestamps) == len(test_data)
    assert all(len(data) == len(test_data) for data in plot.pressure_data)

    # Test plot controls
    plot.autorange_cb.setChecked(True)
    plot.clear_data()
    assert len(plot.timestamps) == 0


def test_macro_sequence_workflow(app_window, qtbot):
    """Test executing multiple macros in sequence."""
    # Create test macros
    macros = [
        Mock(valve_states=[1]*8, timer=1.0, label="Macro 1"),
        Mock(valve_states=[0]*8, timer=1.0, label="Macro 2"),
        Mock(valve_states=[1, 0]*4, timer=1.0, label="Macro 3")
    ]

    with patch.object(app_window.macro_manager, 'get_macro') as mock_get_macro:
        for macro in macros:
            mock_get_macro.return_value = macro
            app_window.run_macro()

            # Verify macro execution
            assert app_window.arduino_worker.last_valve_states == macro.valve_states


def test_error_recovery_workflow(app_window, qtbot):
    """Test error recovery workflow."""
    # Simulate connection error
    with patch.object(app_window.arduino_worker, 'start',
                      side_effect=Exception("Connection failed")):
        app_window.handle_arduino_connection()

        # Verify error state
        assert not app_window.arduino_worker.running
        assert "Connection failed" in app_window.log_widget.log_display.toPlainText()

        # Attempt recovery
        with patch.object(app_window.arduino_worker, 'start', return_value=True):
            app_window.handle_arduino_connection()
            assert app_window.arduino_worker.running


def test_data_validation_workflow(app_window, qtbot):
    """Test data validation workflow."""
    # Test invalid readings
    invalid_cases = [
        None,
        [],
        [1.0],  # Too few values
        [1.0]*4,  # Too many values
        ["invalid", "data", "type"]
    ]

    for readings in invalid_cases:
        app_window.handle_pressure_readings(readings)
        # Verify error logged
        assert "error" in app_window.log_widget.log_display.toPlainText().lower()


def test_motor_limits_workflow(app_window, qtbot):
    """Test motor limits and safety workflow."""
    # Test position limits
    invalid_positions = [-1, 1001]  # Assuming 0-1000 range

    for pos in invalid_positions:
        app_window.position_spin.setValue(pos)
        app_window.move_motor()

        # Verify movement prevented
        assert app_window.motor_worker.current_position != pos
        assert "invalid position" in app_window.log_widget.log_display.toPlainText().lower()


def test_valve_timing_workflow(app_window, qtbot):
    """Test valve timing and synchronization workflow."""
    # Create timed valve sequence
    sequence = [
        ([1]*8, 0.1),  # All open for 0.1s
        ([0]*8, 0.1),  # All closed for 0.1s
        ([1, 0]*4, 0.1)  # Alternating for 0.1s
    ]

    for states, duration in sequence:
        # Set valve states
        app_window.arduino_worker.set_valves(states)

        # Verify timing
        with patch('time.sleep') as mock_sleep:
            app_window.arduino_worker.wait(duration)
            mock_sleep.assert_called_with(duration)


def test_sensor_monitoring_workflow(app_window, qtbot):
    """Test continuous sensor monitoring workflow."""
    # Start monitoring
    readings_sequence = [
        [1.0, 2.0, 3.0],
        [1.5, 2.5, 3.5],
        [2.0, 3.0, 4.0]
    ]

    with patch.object(app_window.arduino_worker, 'get_readings') as mock_readings:
        for readings in readings_sequence:
            mock_readings.return_value = readings
            app_window.update_readings()

            # Verify display updates
            for i, reading in enumerate(readings):
                assert f"{reading:.1f}" in app_window.sensor_labels[i].text()


def test_config_update_workflow(app_window, qtbot):
    """Test configuration update workflow."""
    # Update various settings
    settings_updates = {
        "update_interval": 200,
        "max_data_points": 2000,
        "log_level": "DEBUG"
    }

    for setting, value in settings_updates.items():
        # Update config
        setattr(app_window.config, setting, value)
        app_window.config.save()

        # Verify changes applied
        if setting == "update_interval":
            assert app_window.plot_widget.update_interval == value
        elif setting == "max_data_points":
            assert app_window.plot_widget.max_points == value
        elif setting == "log_level":
            assert app_window.log_widget.logger.level == getattr(
                logging, value)
