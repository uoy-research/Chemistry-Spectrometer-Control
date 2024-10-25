import threading
import serial
import logging
import time
import csv
import os
import minimalmodbus

# 25,600 microsteps per millimeter

class MotorController:
    def __init__(self, port):
        self.port = port
        self.baudrate = 9600
        # self.arduino = None
        self.shutdown_flag = False
        self.serial_connected = False
        self.heartbeat_thread = None
        self.reading_thread = None
        self.lock = threading.Lock()
        self.commands_dict = {
            "HEARTBEAT": 'y',  # Heartbeat response
            "START": 'S',    # Start the Arduino
            "STOP": 's',     # Stop the Arduino
            "DOWN": 'd',     # Move down
            "UP": 'u',       # Move up
            "GOTOPOS": 'p',  # Go to position
            "GETPOS": 'g',   # Get current position
            "GETSTATUS": 't',  # Get status
            "CALIBRATE": 'c',  # Calibrate
        }

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(f"COM{self.port}", self.baudrate)
            logging.info(f"Connected to Arduino on port {self.port}")
            self.serial_connected = True
        except serial.SerialException as e:
            logging.error(f"Failed to connect to Arduino on port {
                          self.port}: {e}")
            self.serial_connected = False

    def start(self):
        print("starting")
        logging.info("Starting server...")
        self.connect_arduino()
        # logging.info("Arduino is connected? " + str(self.serial_connected))
        if self.serial_connected:
            time.sleep(1.2)  # Wait for Arduino to initialise
            self.send_command("START")
            # time.sleep(2.2)  # Wait for Arduino to initialise
            logging.info("Arduino started")
            self.last_heartbeat_time = time.time()
            self.start_heartbeat()
            self.start_reading()
        else:
            pass

    def start_heartbeat(self):
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def send_heartbeat(self):
        while not self.shutdown_flag and self.arduino != None:
            try:
                if self.serial_connected:
                    with self.lock:
                        self.arduino.write(
                            self.commands_dict["HEARTBEAT"].encode())
                        self.arduino.flush()
                    logging.info("Sent HEARTBEAT")
                    # self.last_heartbeat_time = time.time()
                time.sleep(3)  # Send heartbeat every 3 seconds
            except serial.SerialException as e:
                logging.error(f"Failed to send heartbeat: {e}")
                self.serial_connected = False

    def start_reading(self):
        self.reading_thread = threading.Thread(target=self.read_responses)
        self.reading_thread.daemon = True
        self.reading_thread.start()

    def read_responses(self):
        while not self.shutdown_flag and self.arduino != None:

            if self.serial_connected and self.arduino.in_waiting > 0:
                try:
                    response = self.arduino.readline().decode('utf-8').strip()
                    logging.info(f"Received: {response}")
                    self.process_response(response)
                except serial.SerialException as e:
                    logging.error(f"Failed to read from Arduino: {e}")
                    try:
                        self.start_reading()
                    except Exception as e:
                        logging.error(f"Failed to restart reading thread: {e}")
                        self.serial_connected = False
            if self.last_heartbeat_time + self.heartbeat_time < time.time():
                logging.error(
                    "No heartbeat received from Arduino. Stopping server.")
                self.stop()

    def process_response(self, response):
        if isinstance(response, bytes):
            response = response.decode('utf-8').strip()
        else:
            response = response.strip()  # Already a string, just strip whitespace
        # Process the response from Arduino
        if response == "RESET":
            logging.info("Arduino reset")
            self.valve_states = [0, 0, 0, 0, 0, 0, 0, 0]
        # Heartbeat response - "HEARTBEAT_ACK"
        elif response == "HEARTBEATACK":
            self.last_heartbeat_time = time.time()  # Update heartbeat time
            # logging.info("Received HEARTBEAT_ACK")
        elif response == "yes":
            self.last_heartbeat_time = time.time() + 10 # Update heartbeat time
        # Pressure reading - "P <pressure1> ... <valveState1> ... C"
        # Pressure values are in mbar, valve states are 0 or 1
        # P 1013 1014 1015 1016 1 1 1 1 1 1 0 1 C
        # Sequence loaded - "SEQ: <sequence>"
        elif response.startswith("SEQ: "):
            if response.endswith("False"):
                self.sequence_loaded = False
                logging.info(f"Sequence loaded: {
                             response.replace('SEQ: ', '')}")
            else:
                self.sequence_loaded = True
                logging.info(f"Sequence loaded: {
                             response.replace('SEQ: ', '')}")
        elif response.startswith("LOG: "):  # Log message - "LOG <message>"
            log_message = response.replace("LOG: ", "")
            print(log_message)
            logging.info(f"Ard: {log_message}")
        else:
            logging.warning(f"Unknown response: {response}")


    def send_command(self, command):
        if command in self.commands_dict:
            command = self.commands_dict[command]

        if self.serial_connected and self.arduino is not None:
            if command in self.commands_dict.values():
                try:
                    with self.lock:
                        self.arduino.write(command.encode())
                        self.arduino.flush()
                    logging.info(f"Sent command: {command}")
                    return True  # Command sent successfully
                except serial.SerialException as e:
                    logging.error(f"Failed to send command: {e}")
                    self.serial_connected = False
                    return False  # Failed to send command
            else:
                logging.error("Invalid command - not a recognised command")
                logging.error(f"Command: {command}")
                return False  # Invalid command
        else:
            logging.error("Cannot send command - not connected to Arduino")
            return False  # Not connected to Arduino

    def stop(self):
        self.shutdown_flag = True
        self.send_command('STOP')
        logging.info("Sent STOP command")
        self.arduino.close()
        logging.info("Closed serial connection")

    def move_to_target(self, target):
        with self.lock:
            self.arduino.write('p'.encode())
            self.arduino.write(str(target).encode())
            self.arduino.write('\n'.encode())
            self.arduino.flush()
  
    def calibrate(self):
        self.send_command('CALIBRATE')
        logging.info("Sent CALIBRATE command")