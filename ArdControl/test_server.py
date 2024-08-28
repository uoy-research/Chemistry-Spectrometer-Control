import unittest
from unittest.mock import patch, MagicMock
from ArdControl.arduinoController import Server
import serial

class TestServer(unittest.TestCase):

    # Test the server start method
    @patch('server.serial.Serial')
    def test_connect_arduino_success(self, mock_serial):
        # Arrange
        mock_serial.return_value = MagicMock()
        server = Server(port=1, baudrate=9600, verbose=False, mode='test')

        # Act
        server.connect_arduino()

        # Assert
        self.assertTrue(server.serial_connected)
        self.assertEqual(server.error, "Connected to Arduino on port 1")

    @patch('server.serial.Serial')
    def test_connect_arduino_failure(self, mock_serial):
        # Arrange
        mock_serial.side_effect = serial.SerialException("Connection failed")
        server = Server(port=1, baudrate=9600, verbose=False, mode='test')

        # Act
        server.connect_arduino()

        # Assert
        self.assertFalse(server.serial_connected)
        self.assertIn("Failed to connect to Arduino on port 1", server.error)

    @patch('server.threading.Thread')
    def test_start_heartbeat(self, mock_thread):
        # Arrange
        server = Server(port=1, baudrate=9600, verbose=False, mode='test')
        server.serial_connected = True

        # Act
        server.start_heartbeat()

        # Assert
        mock_thread.assert_called_once()
        self.assertTrue(mock_thread.return_value.daemon)
        mock_thread.return_value.start.assert_called_once()

    @patch('server.threading.Thread')
    def test_start_reading(self, mock_thread):
        # Arrange
        server = Server(port=1, baudrate=9600, verbose=False, mode='test')
        server.serial_connected = True

        # Act
        server.start_reading()

        # Assert
        mock_thread.assert_called_once()
        self.assertTrue(mock_thread.return_value.daemon)
        mock_thread.return_value.start.assert_called_once()

    @patch('server.logging')
    def test_stop(self, mock_logging):
        # Arrange
        server = Server(port=1, baudrate=9600, verbose=False, mode='test')
        
        # Mock the arduino attribute
        mock_arduino = MagicMock()
        server.arduino = mock_arduino
        
        # Mock the reading_thread attribute
        mock_reading_thread = MagicMock()
        mock_reading_thread.is_alive.return_value = True
        server.reading_thread = mock_reading_thread
        
        # Mock the heartbeat_thread attribute
        mock_heartbeat_thread = MagicMock()
        mock_heartbeat_thread.is_alive.return_value = True
        server.heartbeat_thread = mock_heartbeat_thread
        
        server.serial_connected = True

        # Act
        server.stop()

        # Assert
        self.assertTrue(server.shutdown_flag)

        # Assert arduino.close() is called
        mock_arduino.close.assert_called_once()
        
        # Assert logging message
        mock_logging.info.assert_called_with("Server stopped.")
        
        # Check if the server's attributes are cleaned up
        self.assertIsNone(server.arduino)

        # Assert reading_thread.join() is called
        mock_reading_thread.join.assert_called_once()
        
        # Assert heartbeat_thread.join() is called
        mock_heartbeat_thread.join.assert_called_once()

    # Test the process_response method

    def setUp(self):
        self.server = Server(port=1, baudrate=9600, verbose=False, mode='test')
        self.server.serial_connected = True

    @patch('server.time.time', return_value=1234567890)
    @patch('server.logging')
    def test_process_response_heartbeat_ack(self, mock_logging, mock_time):
        # Arrange
        response = "HEARTBEAT_ACK"

        # Act
        self.server.process_response(response)

        # Assert
        self.assertEqual(self.server.last_heartbeat_time, 1234567890)
        mock_logging.info.assert_called_with("Received HEARTBEAT_ACK")

    @patch('server.logging')
    def test_process_response_pressure_reading(self, mock_logging):
        # Arrange
        response = "P 1013 1014 1015 1 0 1 C"

        # Act
        self.server.process_response(response)

        # Assert
        self.assertEqual(self.server.pressure_values, ['1013', '1014', '1015'])
        self.assertEqual(self.server.valve_states, ['1', '0', '1'])
        mock_logging.info.assert_any_call("Pressure reading: ['1013', '1014', '1015']")
        mock_logging.info.assert_any_call("Valve states: ['1', '0', '1']")

    @patch('server.logging')
    def test_process_response_log_message(self, mock_logging):
        # Arrange
        response = "LOG: Test log message"

        # Act
        self.server.process_response(response)

        # Assert
        mock_logging.info.assert_called_with("Arduino: Test log message")

    @patch('server.logging')
    def test_process_response_unknown(self, mock_logging):
        # Arrange
        response = "UNKNOWN_RESPONSE"

        # Act
        self.server.process_response(response)

        # Assert
        mock_logging.warning.assert_called_with("Unknown response: UNKNOWN_RESPONSE")

if __name__ == '__main__':
    unittest.main()