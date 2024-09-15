import unittest
from unittest import mock
from unittest.mock import patch, MagicMock, mock_open
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

    # Test the start functions activates heartbeat function
    @patch('serial.Serial')
    def test_start_heartbeat(self, mock_serial):
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        self.controller.arduino = mock_serial_instance
        self.controller.serial_connected = True
        self.controller.start_heartbeat()
        self.assertTrue(self.controller.heartbeat_thread.is_alive())

    # Test the start functions activates reading function
    @patch('serial.Serial')
    def test_start_reading(self, mock_serial):
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        self.controller.arduino = mock_serial_instance
        self.controller.serial_connected = True
        self.controller.start_reading()
        self.assertTrue(self.controller.reading_thread.is_alive())

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

    # Test sending a valid command to the Arduino
    @patch('serial.Serial')
    def test_send_command_valid(self, mock_serial):
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        self.controller.arduino = mock_serial_instance
        self.controller.serial_connected = True

        command = "HEARTBEAT"
        self.controller.send_command(command)
        mock_serial_instance.write.assert_called_with(b'y')

    # Test sending an invalid command string to the Arduino
    @patch('serial.Serial')
    def test_send_command_invalid(self, mock_serial):
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        self.controller.arduino = mock_serial_instance
        self.controller.serial_connected = True

        command = "INVALID_COMMAND"
        self.controller.send_command(command)
        self.controller.arduino.write.assert_not_called()

    @patch('serial.Serial')
    @patch('time.sleep', return_value=None)
    def test_heartbeat(self, mock_sleep, mock_serial):
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        self.controller.arduino = mock_serial_instance
        self.controller.serial_connected = True

        self.controller.start_heartbeat()
        # Ensure time.sleep is called with 3 seconds
        mock_sleep.assert_called_with(3)

        self.controller.arduino.write.assert_called_with(
            self.controller.commands_dict["HEARTBEAT"].encode())

        # Ensure time.sleep is called with 3 seconds
        mock_sleep.assert_called_with(3)

        self.controller.arduino.write.assert_called_with(
            self.controller.commands_dict["HEARTBEAT"].encode())

    @patch('time.time', return_value=1234567890)
    def test_process_response_heartbeat_ack(self, mock_time):
        response = "HEARTBEAT_ACK"
        self.controller.process_response(response)
        self.assertEqual(self.controller.last_heartbeat_time, 1234567890)

    def test_process_response_pressure_reading(self):
        response = "P 1013 1014 1015 1016 1 1 1 1 1 1 0 1 C"
        self.controller.process_response(response)

        expected_pressure_values = ["1013", "1014", "1015", "1016"]
        expected_valve_states = ["1", "1",
                                 "1", "1", "1", "1", "0", "1"]

        self.assertEqual(self.controller.pressure_values,
                         expected_pressure_values)
        self.assertEqual(self.controller.valve_states, expected_valve_states)
        self.assertTrue(self.controller.new_reading)
        self.assertEqual(
            self.controller.readings[-1], expected_pressure_values + expected_valve_states)

    @patch('logging.info')
    def test_process_response_log_message(self, mock_logging_info):
        response = "LOG: This is a test log message"
        self.controller.process_response(response)

        # Check if logging.info was called with the correct message
        mock_logging_info.assert_called_with("Ard: This is a test log message")

    @patch('logging.warning')
    def test_process_response_unknown(self, mock_logging_warning):
        response = "UNKNOWN_RESPONSE"
        self.controller.process_response(response)

        # Check if logging.warning was called with the correct message
        mock_logging_warning.assert_called_with(
            "Unknown response: UNKNOWN_RESPONSE")

    # Test that the controller stops the threads and closes the serial connection when heartbeat times out
    @patch.object(ArduinoController, 'connect_arduino')
    @patch.object(ArduinoController, 'start_heartbeat')
    @patch.object(ArduinoController, 'start_reading')
    @patch.object(ArduinoController, 'stop')
    @patch('serial.Serial')
    @patch('time.time', return_value=1234567890)
    def test_heartbeat_timeout(self, mock_start_reading, mock_start_heartbeat, mock_connect_arduino, mock_stop, mock_serial, mock_time):
        mock_connect_arduino.return_value = mock_serial
        self.controller.serial_connected = True
        self.controller.start()
        self.controller.last_heartbeat_time = time.time() - 10

        # Act
        # This should trigger the stop method due to heartbeat timeout
        self.controller.start_reading()

        # Assert
        mock_stop.assert_called()

        self.controller.stop()

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", side_effect=[False, True])
    @patch("os.makedirs")
    def test_save_pressure_data_creates_file(self, mock_exists, mock_open, mock_makedirs):
        # Arrange
        file_path = "pressure_data.csv"
        self.controller.save_pressure_data(True, "pressure data.csv")

        # Act
        file_created = os.path.exists(file_path)
        self.controller.save_pressure_data(False, "pressure data.csv")
        self.controller.stop()

        # Assert
        mock_open.assert_called_with(file_path)
        self.assertTrue(file_created)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", side_effect=[False, True])
    @patch("os.makedirs")
    @patch("time.time", return_value=1234567890)
    @patch("csv.writer")
    @patch("serial.Serial")
    def test_save_pressure_data_to_csv(self, mock_makedirs, mock_exists, mock_open, mock_time, mock_writer, mock_serial):

        # Arrange
        file_path = "pressure_data.csv"
        self.controller.pressure_values = [1013, 1014, 1015, 1016]
        self.controller.valve_states = [1, 1, 1, 1, 1, 1, 0, 1]

        # Mock in_waiting attribute as an integer

        # Act
        self.controller.save_pressure_data(True, file_path)

        # Assert
        mock_makedirs.assert_called_once_with("C:\\NMR Results")
        mock_open.assert_called_once_with(file_path, 'w')
        mock_writer.return_value.writerow.assert_called_once_with(
            ['1234567890', '1013', '1014', '1015', '1016', '1', '1', '1', '1', '1', '1', '0', '1'])
        self.assertEqual(self.controller.pressure_data_filepath,
                         "C:\\NMR Results\\pressure_data.csv")
        self.controller.pressure_data_thread.start.assert_called_once()

        self.controller.save_pressure_data(False, file_path)
        self.controller.stop()


if __name__ == '__main__':
    unittest.main()
