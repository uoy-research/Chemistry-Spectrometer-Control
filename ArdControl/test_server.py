import unittest
from unittest.mock import patch, MagicMock
import time
import logging
import serial
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
        self.assertAlmostEqual(self.controller.last_heartbeat_time, time.time(), delta=1)
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

if __name__ == '__main__':
    unittest.main()