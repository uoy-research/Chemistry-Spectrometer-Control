import threading
import serial
import logging
import time
import csv
import os


class MotorController:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        # self.arduino = None
        self.shutdown_flag = False
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
        logging.info("Starting server...")
        self.connect_arduino()
        # logging.info("Arduino is connected? " + str(self.serial_connected))
        if self.serial_connected:
            time.sleep(1.2)  # Wait for Arduino to initialise

            self.send_command('START'.encode())
            # time.sleep(2.2)  # Wait for Arduino to initialise
            logging.info("Arduino started")
            self.last_heartbeat_time = time.time()
            self.start_heartbeat()
        else:
            pass

    def start_heartbeat(self):
        self.heartbeat_thread = threading.Thread(target=self.heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def heartbeat(self):
        while not self.shutdown_flag and self.arduino != None:
            try:
                if self.serial_connected:
                    self.arduino.write('HEARTBEAT'.encode())
                    logging.info("Sent HEARTBEAT")
                    # self.last_heartbeat_time = time.time()
                time.sleep(3)  # Send heartbeat every 3 seconds
            except serial.SerialException as e:
                logging.error(f"Failed to send heartbeat: {e}")
                self.serial_connected = False

    def send_command(self, command):
        if command in self.commands_dict:
            command = self.commands_dict[command]

        if self.serial_connected and self.arduino != None:
            if command in self.commands_dict.values():
                try:
                    self.arduino.write(command.encode())
                    logging.info(f"Sent command: {command}")
                except serial.SerialException as e:
                    logging.error(f"Failed to send command: {e}")
                    self.serial_connected = False
            else:
                logging.error("Invalid command - not a recognised command")
        else:
            logging.error("Cannot send command - not connected to Arduino")

    def stop(self):
        self.shutdown_flag = True
        self.send_command('STOP')
        logging.info("Sent STOP command")
        self.arduino.close()
        logging.info("Closed serial connection")

    def move(self, direction):
        self.send_command(direction)
