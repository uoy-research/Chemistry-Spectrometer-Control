import threading
import serial
import logging
import time
import csv
import os

class Step:
    def __init__(self, step_type, time_length):
        self.step_type = step_type
        self.time_length = time_length

class ArduinoController:
    def __init__(self, port, verbose, mode):
        self.port = port    # Port number to connect to arduino
        self.baudrate = 9600    # Baudrate for serial connection
        self.verbose = verbose  # Verbose mode
        # Mode of operation (0 = manual, 1 = sequence, 2 = TTL)
        self.mode = mode
        self.arduino = None  # Container for arduino object
        # Container for valve states
        self.valve_states = [0, 0, 0, 0, 0, 0, 0, 0]
        self.pressure_values = [0, 0, 0, 0]   # Container for pressure values
        self.readings = []  # Container for pressure readings
        self.serial_connected = False   # Flag to indicate serial connection
        self.shutdown_flag = False  # Flag to indicate server shutdown
        self.save_pressure = False  # Flag to indicate saving pressure data
        self.new_reading = False  # Flag to indicate new pressure reading
        self.new_plot = False  # Flag to indicate new plot data
        self.sequence_loaded = False    # Flag to indicate sequence loaded
        self.last_heartbeat_time = time.time()
        self.heartbeat_time = 5  # Time in seconds between heartbeats
        self.auto_control = False
        self.steps = []
        self.prev_step = None
        self.lock = threading.Lock()

        self.pressure_data_thread = threading.Thread(
            target=self.read_pressure_data)
        self.pressure_data_filepath = ""
        self.commands_dict = {
            "HEARTBEAT": 'y',  # Heartbeat response
            "DECODE_SEQUENCE": 'i',  # Decode a sequence INLET
            "EXECUTE_SEQUENCE": 'R',  # Execute the current loaded sequence
            "ENABLE_PRESSURE_LOG": 'K',  # Enable pressure logging
            "DISABLE_PRESSURE_LOG": 'k',  # Disable pressure logging
            "SWITCH_TO_MANUAL": 'm',  # Switch to manual control (TN = 0)
            "SWITCH_TO_AUTO_CONTROL": 'M',  # Switch to spec'r control (TN = 1)
            "ENABLE_TTL_CONTROL": 'T',  # Enable TTL control
            "DISABLE_TTL_CONTROL": 't',  # Disable TTL control
            "TURN_ON_SHORT_VALVE": 'Z',  # Turn on short valve
            "TURN_OFF_SHORT_VALVE": 'z',  # Turn off short valve
            "TURN_ON_INLET_VALVE": 'C',  # Turn on INLET valve
            "TURN_OFF_INLET_VALVE": 'c',  # Turn off INLET valve
            "TURN_ON_OUTLET_VALVE": 'V',  # Turn on OUTLET valve
            "TURN_OFF_OUTLET_VALVE": 'v',  # Turn off OUTLET valve
            "TURN_ON_VENT_VALVE": 'X',  # Turn on VENT valve
            "TURN_OFF_VENT_VALVE": 'x',  # Turn off VENT valve
            "TURN_ON_SWITCH_VALVE": 'H',  # Turn on SWITCH valve
            "TURN_OFF_SWITCH_VALVE": 'h',  # Turn off SWITCH valve
            "RESET": 's',    # Reset the Arduino
            "START": 'S',    # Start the Arduino
            "DEPRESSURISE": 'd',    # Depressurise the system
            "LOAD_STEP": 'l'    # Load a step into the sequence
        }

        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        if mode == 0:
            self.auto_control = False
        elif mode == 1:
            self.auto_control = True
            logging.info("Magritek mode enabled")
        elif mode == 2:
            self.auto_control = True
            logging.info("TTL mode enabled")
        else:
            logging.error("Invalid mode, defaulting to manual mode")
            self.mode = 0
            self.auto_control = False

    def start(self):
        logging.info("Starting server...")
        self.connect_arduino()
        # logging.info("Arduino is connected? " + str(self.serial_connected))
        if self.serial_connected:
            time.sleep(1.2)  # Wait for Arduino to initialise
           
            self.send_command("START")
            #time.sleep(2.2)  # Wait for Arduino to initialise
            logging.info("Arduino started") 
            self.last_heartbeat_time = time.time()
            self.start_heartbeat()
            self.start_reading()
            if self.mode == 0:
                # Should be in manual by default, but just in case
                self.send_command("SWITCH_TO_MANUAL")
            elif self.mode == 1:
                self.send_command("SWITCH_TO_AUTO_CONTROL")
            elif self.mode == 2:
                self.send_command("ENABLE_TTL_CONTROL")
            else:
                logging.error("Invalid mode, defaulting to manual mode")
                self.mode = 0
                self.auto_control = False
                self.send_command("SWITCH_TO_MANUAL")
        else:
            # logging.error("Failed to connect to Arduino. Server not started.")
            # self.stop()
            pass

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(f"COM{self.port}", self.baudrate)
            logging.info(f"Connected to Arduino on port {self.port}")
            self.serial_connected = True
        except serial.SerialException as e:
            logging.error(f"Failed to connect to Arduino on port {
                          self.port}: {e}")
            self.serial_connected = False

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
                    #logging.info(f"Received: {response}")
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
        elif response == "HEARTBEAT_ACK":
            self.last_heartbeat_time = time.time()  # Update heartbeat time
            # logging.info("Received HEARTBEAT_ACK")
        elif response == "NEWSEQ":  # next step requested by arduino
            if self.steps != []:
                self.send_step(self.steps[0])
                self.prev_step = self.steps[0]
                self.steps.pop(0)
        elif response == "WAITSEQ":  # step sent too early, attempt to resend later
            if self.prev_step:
                self.steps.insert(0, self.prev_step)
        # Pressure reading - "P <pressure1> ... <valveState1> ... C"
        # Pressure values are in mbar, valve states are 0 or 1
        # P 1013 1014 1015 1016 1 1 1 1 1 1 0 1 C
        elif response.startswith("P "):
            self.pressure_values = response.split(
                " ")[1:5]  # Currently only 4 pressure values
            #logging.info(f"Pressure reading: {self.pressure_values}")
            self.valve_states = response.split(
                " ")[5:-1]   # Currently only 8 valve states
            #logging.info(f"Valve states: {self.valve_states}")

            self.readings.append(
                [time.time(), *self.pressure_values, *self.valve_states])
            while len(self.readings) > 20:
                # Remove the oldest reading
                self.readings.pop(0)
            # Set flag to indicate new reading available
            self.new_reading = True
            self.new_plot = True
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
            logging.info(f"Ard: {log_message}")
        else:
            logging.warning(f"Unknown response: {response}")

    def stop(self):
        self.serial_connected = False
        if self.arduino != None:
            self.send_command("RESET")
            self.arduino.close()
            self.arduino = None
        logging.info("Server stopped.")

        self.shutdown_flag = True

        # Join the reading thread to ensure it has finished
        if hasattr(self, 'reading_thread') and self.reading_thread.is_alive():
            if threading.current_thread() is not self.reading_thread:
                self.reading_thread.join()

        # Join the heartbeat thread to ensure it has finished
        if hasattr(self, 'heartbeat_thread') and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join()

        # Join the pressure data thread to ensure it has finished
        if hasattr(self, 'pressure_data_thread') and self.pressure_data_thread.is_alive():
            self.pressure_data_thread.join()

    def save_pressure_data(self, save, filename):
        if save:
            if filename == "":  # If no filename specified, save in NMR Results folder with timestamp
                if not os.path.exists("C:\\NMR Results"):
                    os.makedirs("C:\\NMR Results")
                filename = os.path.join("C:\\NMR Results", f"pressure_data_{
                                        time.strftime('%m%d-%H%M')}.csv")
            # If filename doesn't end in .csv, add it
            elif not filename.endswith(".csv"):
                filename = filename + ".csv"
            # If no location specified, save in NMR Results folder
            if os.path.dirname(filename) == "":
                filename = os.path.join("C:\\NMR Results", filename)
            # If location doesn't exist, create it
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            self.pressure_data_filepath = filename
            self.save_pressure = True
            if not self.pressure_data_thread or not self.pressure_data_thread.is_alive():
                self.pressure_data_thread.start()
            else:
                logging.error("Pressure data thread already running")
        else:
            self.save_pressure = False
            if self.pressure_data_thread and self.pressure_data_thread.is_alive():
                self.pressure_data_thread.join()

    def read_pressure_data(self):
        # Check if the file exists
        file_exists = os.path.isfile(self.pressure_data_filepath)

        if not file_exists:
            with open(self.pressure_data_filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Time", "Pressure1", "Pressure2", "Pressure3", "ValveState1", "ValveState2",
                                "ValveState3", "ValveState4", "ValveState5", "ValveState6", "ValveState7", "ValveState8"])

        while self.save_pressure:
            if self.new_reading:
                with open(self.pressure_data_filepath, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(
                        [self.readings[-1][0], *self.readings[-1][1:]])
                self.new_reading = False
            time.sleep(0.1)

    def get_pressure_values(self):
        return self.pressure_values

    def get_recent_readings(self):
        return self.readings

    def get_valve_states(self):
        return self.valve_states

    def get_auto_control(self):
        return self.auto_control

    def get_sequence_loaded(self):
        return self.sequence_loaded

    def send_command(self, command):
        if command in self.commands_dict:
            command = self.commands_dict[command]

        if self.serial_connected and self.arduino != None:
            if command in self.commands_dict.values():
                try:
                    with self.lock:
                        self.arduino.write(command.encode())
                        self.arduino.flush()
                    logging.info(f"Sent command: {command}")
                except serial.SerialException as e:
                    logging.error(f"Failed to send command: {e}")
                    self.serial_connected = False
            else:
                logging.error("Invalid command - not a recognised command")
        else:
            logging.error("Cannot send command - not connected to Arduino")

    # Sequence e.g. b100n200d300b300 -- current max 9 "steps" in sequence
    def send_sequence(self, sequence):
        """
        if not self.get_auto_control():
            logging.error("Cannot send sequence in manual mode")
            return
        if self.mode == 2:
            logging.error("Cannot send sequence in TTL mode")
            return
        """
        if self.serial_connected and self.arduino != None:
            try:
                self.arduino.write(b'i')
                self.arduino.write(sequence.encode())
                self.arduino.write(b'\n')
                logging.info(f"Sent sequence: {sequence}")
            except serial.SerialException as e:
                logging.error(f"Failed to send sequence: {e}")
                self.serial_connected = False

    def execute_sequence(self):
        """
        if not self.get_auto_control():
            logging.error("Cannot execute sequence in manual mode")
            return
        if self.mode == 2:
            logging.error("Cannot execute sequence in TTL mode")
            return
        """
        if self.serial_connected and self.arduino != None:
            if self.sequence_loaded:
                try:
                    with self.lock:
                        self.arduino.write(b'R')
                        self.arduino.flush()
                    logging.info("Sent execute sequence command")
                except serial.SerialException as e:
                    logging.error(f"Failed to execute sequence: {e}")
                    self.serial_connected = False
            else:
                logging.error("No sequence loaded")

    def send_step(self, step):
        if self.serial_connected and self.arduino != None:
            try:
                with self.lock:
                    self.arduino.write(b'l')
                    self.arduino.write(step.step_type.encode())
                    self.arduino.write(str(step.time_length).encode())
                    self.arduino.write(b'\n')
                    self.arduino.flush()
                logging.info(f"Sent step: {step.step_type} {step.time_length}")
            except serial.SerialException as e:
                logging.error(f"Failed to send step: {e}")
                self.serial_connected = False