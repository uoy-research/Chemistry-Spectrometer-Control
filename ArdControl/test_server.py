import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
import time
import logging
import serial
import os
from arduinoController import ArduinoController

# Configure logging to capture error logs for the tests
logging.basicConfig(level=logging.ERROR)


class TestArduinoController(unittest.TestCase):

    # Set up the test
    def setUp(self):
        self.port = 'COM3'
        self.baudrate = 9600
        self.verbose = True
        self.mode = 0
        self.controller = ArduinoController(self.port, self.verbose, self.mode)

    # Test the initialization of the ArduinoController
    def test_initialization(self):
        self.assertEqual(self.controller.port, self.port)
        self.assertEqual(self.controller.baudrate, self.baudrate)
        self.assertEqual(self.controller.verbose, self.verbose)
        self.assertEqual(self.controller.mode, self.mode)
        self.assertIsNone(self.controller.arduino)
        self.assertFalse(self.controller.serial_connected)
        self.assertFalse(self.controller.shutdown_flag)
        self.assertFalse(self.controller.save_pressure)
        self.assertFalse(self.controller.new_reading)
        self.assertAlmostEqual(
            self.controller.last_heartbeat_time, time.time(), delta=1)
        self.assertEqual(self.controller.heartbeat_time, 5)
        self.assertFalse(self.controller.auto_control)
        self.assertIsInstance(self.controller.commands_dict, dict)

    # Test the serial connection to the Arduino - success
    @patch('serial.Serial')
    def test_connect_arduino_success(self, mock_serial):
        mock_serial.return_value.is_open = True
        self.controller.connect_arduino()
        self.assertTrue(self.controller.serial_connected)
        self.assertIsNotNone(self.controller.arduino)

    # Test the serial connection to the Arduino - failure
    @patch('serial.Serial')
    def test_connect_arduino_failure(self, mock_serial):
        mock_serial.side_effect = serial.SerialException
        self.controller.connect_arduino()
        self.assertFalse(self.controller.serial_connected)
        self.assertIsNone(self.controller.arduino)

    # Test the start function - successfully connected
    @patch.object(ArduinoController, 'connect_arduino')
    @patch.object(ArduinoController, 'start_heartbeat')
    @patch.object(ArduinoController, 'start_reading')
    def test_start(self, mock_start_reading, mock_start_heartbeat, mock_connect_arduino):
        mock_connect_arduino.return_value = None
        self.controller.serial_connected = True
        self.controller.start()
        mock_connect_arduino.assert_called_once()
        mock_start_heartbeat.assert_called_once()
        mock_start_reading.assert_called_once()

    # Test the start function - not connected
    @patch.object(ArduinoController, 'connect_arduino')
    @patch.object(ArduinoController, 'start_heartbeat')
    @patch.object(ArduinoController, 'start_reading')
    def test_start_not_connected(self, mock_start_reading, mock_start_heartbeat, mock_connect_arduino):
        mock_connect_arduino.return_value = None
        self.controller.serial_connected = False
        self.controller.start()
        mock_connect_arduino.assert_called_once()
        mock_start_heartbeat.assert_not_called()
        mock_start_reading.assert_not_called()

    # Test sending a command to the Arduino
    @patch('serial.Serial')
    def test_send_command(self, mock_serial):
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        self.controller.arduino = mock_serial_instance
        self.controller.serial_connected = True

        command = "HEARTBEAT"
        self.controller.send_command(command)
        mock_serial_instance.write.assert_called_with(b'y')

    # Test sending an invalid command string to the Arduino
    @patch('serial.Serial')
    def test_send_invalid_command(self, mock_serial):
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        self.controller.arduino = mock_serial_instance
        self.controller.serial_connected = True

        command = "INVALID_COMMAND"
        self.controller.send_command(command)
        self.controller.arduino.write.assert_not_called()

    # New comprehensive tests
    @patch('arduinoController.time.sleep', return_value=None)
    def test_send_heartbeat(self, mock_sleep):
        self.controller.arduino = MagicMock()
        self.controller.serial_connected = True
        self.controller.shutdown_flag = True  # Ensure loop exits immediately
        self.controller.send_heartbeat()
        self.controller.arduino.write.assert_called_with(b'y')

    def test_start_heartbeat(self):
        with patch.object(self.controller, 'send_heartbeat') as mock_send_heartbeat:
            self.controller.start_heartbeat()
            self.assertTrue(self.controller.heartbeat_thread.is_alive())
            self.controller.shutdown_flag = True  # Ensure thread exits

    def test_start_reading(self):
        with patch.object(self.controller, 'read_responses') as mock_read_responses:
            self.controller.start_reading()
            self.assertTrue(self.controller.reading_thread.is_alive())
            self.controller.shutdown_flag = True  # Ensure thread exits

    @patch('serial.Serial')
    def test_read_responses_success(self, mock_serial):
        self.controller.arduino = MagicMock()
        self.controller.serial_connected = True
        self.controller.arduino.in_waiting = 1
        self.controller.arduino.readline.return_value = b'HEARTBEAT_ACK\n'
        with patch.object(self.controller, 'process_response') as mock_process_response:
            self.controller.read_responses()
            mock_process_response.assert_called_with('HEARTBEAT_ACK')

    @patch('serial.Serial')
    def test_read_responses_failure(self, mock_serial):
        self.controller.arduino = MagicMock()
        self.controller.serial_connected = True
        self.controller.arduino.in_waiting = 1
        self.controller.arduino.readline.side_effect = serial.SerialException(
            "Test Exception")
        self.controller.read_responses()
        self.assertFalse(self.controller.serial_connected)

    def test_process_response_heartbeat_ack(self):
        self.controller.process_response("HEARTBEAT_ACK")
        self.assertEqual(self.controller.last_heartbeat_time,
                         time.time(), delta=1)

    def test_process_response_pressure_reading(self):
        response = "P 1013 1014 1015 1 1 1 1 1 1 0 1 C"
        self.controller.process_response(response)
        self.assertEqual(self.controller.pressure_values,
                         ["1013", "1014", "1015"])
        self.assertEqual(self.controller.valve_states, [
                         "1", "1", "1", "1", "1", "1", "0", "1"])
        self.assertTrue(self.controller.new_reading)

    def test_process_response_sequence_loaded(self):
        response = "SEQ: True"
        self.controller.process_response(response)
        self.assertTrue(self.controller.sequence_loaded)

    def test_process_response_log_message(self):
        response = "LOG: Test message"
        with self.assertLogs(level='INFO') as log:
            self.controller.process_response(response)
            self.assertIn("Arduino: Test message", log.output[0])

    def test_send_command_valid(self):
        self.controller.arduino = MagicMock()
        self.controller.serial_connected = True
        self.controller.send_command("RESET")
        self.controller.arduino.write.assert_called_with(b's')

    def test_send_command_invalid(self):
        with self.assertLogs(level='ERROR') as log:
            self.controller.send_command("INVALID_COMMAND")
            self.assertIn(
                "Invalid command - not a recognised command", log.output[0])

    def test_send_sequence_manual_mode(self):
        with self.assertLogs(level='ERROR') as log:
            self.controller.send_sequence("b100n200")
            self.assertIn("Cannot send sequence in manual mode", log.output[0])

    def test_save_pressure_data(self):
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            self.controller.save_pressure_data(True, "test.csv")
            self.assertTrue(self.controller.save_pressure)
            self.controller.save_pressure_data(False, "test.csv")
            self.assertFalse(self.controller.save_pressure)

    def test_get_pressure_values(self):
        self.controller.pressure_values = ["1013", "1014", "1015"]
        self.assertEqual(self.controller.get_pressure_values(), [
                         "1013", "1014", "1015"])

    def test_get_recent_readings(self):
        self.controller.readings = [
            ["1013", "1014", "1015", "1", "1", "1", "1", "1", "1", "0", "1"]]
        self.assertEqual(self.controller.get_recent_readings(), [
                         ["1013", "1014", "1015", "1", "1", "1", "1", "1", "1", "0", "1"]])

    def test_get_valve_states(self):
        self.controller.valve_states = ["1", "1", "1", "1", "1", "1", "0", "1"]
        self.assertEqual(self.controller.get_valve_states(), [
                         "1", "1", "1", "1", "1", "1", "0", "1"])

    def test_get_auto_control(self):
        self.assertFalse(self.controller.get_auto_control())

    def test_get_sequence_loaded(self):
        self.controller.sequence_loaded = True
        self.assertTrue(self.controller.get_sequence_loaded())

    # Test for handling heartbeat timeout


    def test_heartbeat_timeout(self):
        self.controller.serial_connected = True
        self.controller.last_heartbeat_time = time.time() - 10  # Simulate timeout
        with self.assertLogs(level='ERROR') as log:
            self.controller.read_responses()
            self.assertIn(
                "No heartbeat received from Arduino. Stopping server.", log.output[0])
            self.assertFalse(self.controller.serial_connected)

    # Test for processing an unknown response


    def test_process_response_unknown(self):
        with self.assertLogs(level='WARNING') as log:
            self.controller.process_response("UNKNOWN_RESPONSE")
            self.assertIn("Unknown response: UNKNOWN_RESPONSE", log.output[0])

    # Test file creation in save_pressure_data


    def test_save_pressure_data_creates_file(self):
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            with patch('os.makedirs') as mock_makedirs:
                filename = "test.csv"
                self.controller.save_pressure_data(True, filename)
                mock_makedirs.assert_called_once()
                mock_file.assert_called_with(os.path.join(
                    "C:\\NMR Results", filename), 'w', newline='')

    # Test stopping the controller


    @patch('serial.Serial')
    def test_stop_controller(self, mock_serial):
        self.controller.arduino = MagicMock()
        self.controller.serial_connected = True
        self.controller.heartbeat_thread = MagicMock()
        self.controller.reading_thread = MagicMock()
        self.controller.heartbeat_thread.is_alive.return_value = True
        self.controller.reading_thread.is_alive.return_value = True

        self.controller.stop()
        self.controller.arduino.close.assert_called_once()
        self.controller.heartbeat_thread.join.assert_called_once()
        self.controller.reading_thread.join.assert_called_once()
        self.assertFalse(self.controller.serial_connected)

    # Test sending a sequence in auto-control mode


    @patch('serial.Serial')
    def test_send_sequence_auto_control(self, mock_serial):
        self.controller.auto_control = True
        self.controller.mode = 1
        self.controller.arduino = mock_serial.return_value
        self.controller.serial_connected = True
        sequence = "b100n200"

        with patch.object(self.controller, 'send_command') as mock_send_command:
            self.controller.send_sequence(sequence)
            self.controller.arduino.write.assert_any_call(b'i')
            self.controller.arduino.write.assert_any_call(sequence.encode())
            self.controller.arduino.write.assert_any_call(b'\n')

    # Test edge cases for sequence processing


    @patch('serial.Serial')
    def test_send_sequence_invalid(self, mock_serial):
        self.controller.auto_control = True
        self.controller.mode = 1
        self.controller.arduino = mock_serial.return_value
        self.controller.serial_connected = True

        long_sequence = "b100n200d300b300" * 10  # Exceeds typical length
        with self.assertLogs(level='ERROR') as log:
            self.controller.send_sequence(long_sequence)
            self.assertIn("Failed to send sequence", log.output[0])

        invalid_sequence = "b100x200"  # Contains invalid characters
        with self.assertLogs(level='ERROR') as log:
            self.controller.send_sequence(invalid_sequence)
            self.assertIn("Failed to send sequence", log.output[0])

if __name__ == '__main__':
    unittest.main()
