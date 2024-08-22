import threading
import socket
import serial
import logging
import time

class Server:
    def __init__(self, port, baudrate, verbose, mode):
        self.port = port
        self.baudrate = baudrate
        self.verbose = verbose
        self.mode = mode
        self.arduino
        self.error = ""
        self.serial_connected = False
        self.shutdown_flag = False  # Flag to indicate server shutdown
        self.save_pressure = False  # Flag to indicate saving pressure data

        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    def start(self):  
        self.connect_arduino()
        if self.serial_connected:
            self.start_heartbeat()
            self.start_reading()

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(f"COM{self.port}", self.baudrate)
            self.error = f"Connected to Arduino on port {self.port}"
            logging.info(self.error)
            self.serial_connected = True
        except serial.SerialException as e:
            self.error = f"Failed to connect to Arduino on port {self.port}: {e}"
            logging.error(self.error)
            self.serial_connected = False

    def start_heartbeat(self):
        heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

    def send_heartbeat(self):
        while not self.shutdown_flag:
            try:
                if self.serial_connected:
                    self.arduino.write(b'y')
                    logging.info("Sent HEARTBEAT")
                time.sleep(5)  # Send heartbeat every 5 seconds
            except serial.SerialException as e:
                logging.error(f"Failed to send heartbeat: {e}")
                self.serial_connected = False

    def start_reading(self):
        reading_thread = threading.Thread(target=self.read_responses)
        reading_thread.daemon = True
        reading_thread.start()

    def read_responses(self):
        while not self.shutdown_flag:
            try:
                if self.serial_connected and self.arduino.in_waiting > 0:
                    response = self.arduino.readline().decode('utf-8').strip()
                    logging.info(f"Received: {response}")
                    self.process_response(response)
            except serial.SerialException as e:
                logging.error(f"Failed to read from Arduino: {e}")
                self.serial_connected = False

    def process_response(self, response):
        # Process the response from Arduino
        if response == "HEARTBEAT_ACK":
            self.last_heartbeat_time = time.time()
            logging.info("Received HEARTBEAT_ACK")
        elif response.startswith("P "):   # Pressure reading - "P <pressure1> ... <valveState1> ... C"
            pressure_value = response.split(" ")[1:4]
            logging.info(f"Pressure reading: {pressure_value}")
            valve_states = response.split(" ")[4:-1]
            logging.info(f"Valve states: {valve_states}")
        elif response.startswith("LOG "):  # Log message - "LOG <message>"
            log_message = response.replace("LOG ", "")
            logging.info(f"Arduino: {log_message}")
        else:
            logging.info(f"Unknown response: {response}")

    def stop(self):
        self.shutdown_flag = True
        if self.arduino:
            self.arduino.close()
        logging.info("Server stopped.")