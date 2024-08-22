import sys
import argparse
import socket
import threading
import serial

class Server:
    def __init__(self, port, baudrate, verbose, mode):
        self.port = port
        self.baudrate = baudrate
        self.verbose = verbose
        self.mode = mode
        self.arduino = None
        self.server_socket = None
        self.error = ""
        self.client_connected = False   # Flag to indicate if a client is connected
        self.serial_connected = False
        self.shutdown = False   # Flag to indicate if the server should shut down

    def start(self):  
        self.connect_arduino()
        self.start_server()

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', 9999))
        self.server_socket.listen(5)
        print("Server listening on port 9999")

        while not self.shutdown:
            client_socket, addr = self.server_socket.accept()
            if self.client_connected:
                # Send error message to additional clients
                error_message = "Server is already connected to another client."
                client_socket.sendall(error_message.encode('utf-8'))
                client_socket.close()
                print(f"Rejected connection from {addr}: {error_message}")
            elif self.serial_connected == False:
                # Send error message to additional clients
                # error_message = "Arduino is already connected to another client."
                client_socket.sendall(self.error.encode('utf-8'))
                client_socket.close()
                print(f"Rejected connection from {addr}: {error_message}")
                self.server_socket.close()
                print("Server shut down.")
                return
            else:
                print(f"Accepted connection from {addr}")
                self.client_connected = True
                client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_handler.start()
                client_handler.join()  # Wait for the client handler to finish
                self.client_connected = False
        
        self.server_socket.close()
        print("Server shut down.")

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(f"COM{self.port}", self.baudrate)
            self.error = f"Connected to Arduino on port {self.port}"
            print(self.error)
            self.serial_connected = True
        except serial.SerialException as e:
            self.error = f"Failed to connect to Arduino on port {self.port}: {e}"
            self.error += "\nExiting..."
            print(self.error)
            self.serial_connected = False

    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break   # Client disconnected
                if message == "SHUTDOWN":
                    response = "Server is shutting down."
                    client_socket.sendall(response.encode('utf-8'))
                    self.shutdown_flag = True
                    break
                else:
                    response = self.process_command(message)
                    client_socket.sendall(response.encode('utf-8'))
            except ConnectionResetError:
                break   # Client disconnected
        client_socket.close()

    def process_command(self, command):
        # Dummy implementation of command processing
        # Replace with actual command processing logic
        if command == "PING":
            return "PONG"
        else:
            return f"Unknown command: {command}"

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Process some command-line arguments.")
    
    # Define arguments
    parser.add_argument('--port', type=int, help='Port number to connect to')
    parser.add_argument('--baudrate', type=int, default=9600, help='Baud rate for the serial connection')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--mode', choices=['manual', 'sequence', 'ttl'], default='manual', help='Arduino mode')
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Access the arguments
    port = args.port
    baudrate = args.baudrate
    verbose = args.verbose
    mode = args.mode
    
    # Print the arguments
    print(f"Port: {port}")
    print(f"Baudrate: {baudrate}")
    print(f"Verbose: {verbose}")
    print(f"Mode: {mode}")

    # Create and start the server
    server = Server(port, baudrate, verbose, mode)
    server.start()

if __name__ == "__main__":
    main()import argparse
import threading
import socket
import serial
import logging

class Server:
    def __init__(self, port, baudrate, verbose, mode):
        self.port = port
        self.baudrate = baudrate
        self.verbose = verbose
        self.mode = mode
        self.arduino = None
        self.server_socket = None
        self.error = ""
        self.client_connected = False  # Flag to track connection status
        self.serial_connected = False
        self.shutdown_flag = False  # Flag to indicate server shutdown

        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    def start(self):  
        self.connect_arduino()
        self.start_server()

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.server_socket:
            self.server_socket.bind(('localhost', 9999))
            self.server_socket.listen(5)
            logging.info("Server listening on port 9999")

            while not self.shutdown_flag:
                client_socket, addr = self.server_socket.accept()
                if self.client_connected:
                    # Send error message to additional clients
                    error_message = "Server is already connected to another client."
                    client_socket.sendall(error_message.encode('utf-8'))
                    client_socket.close()
                    logging.info(f"Rejected connection from {addr}: {error_message}")
                elif not self.serial_connected:
                    # Send error message if Arduino is not connected
                    client_socket.sendall(self.error.encode('utf-8'))
                    client_socket.close()
                    logging.info(f"Rejected connection from {addr}: {self.error}")
                    self.server_socket.close()
                    logging.info("Server shut down.")
                    return
                else:
                    logging.info(f"Accepted connection from {addr}")
                    self.client_connected = True
                    client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_handler.start()
                    client_handler.join()  # Wait for the client handler to finish
                    self.client_connected = False

            logging.info("Server shut down.")

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(f"COM{self.port}", self.baudrate)
            self.error = f"Connected to Arduino on port {self.port}"
            logging.info(self.error)
            self.serial_connected = True
        except serial.SerialException as e:
            self.error = f"Failed to connect to Arduino on port {self.port}: {e}"
            self.error += "\nExiting..."
            logging.error(self.error)
            self.serial_connected = False

    def handle_client(self, client_socket):
        with client_socket:
            while True:
                try:
                    message = client_socket.recv(1024).decode('utf-8')
                    if not message:
                        break   # Client disconnected
                    logging.info(f"Received command: {message}")
                    if message == "SHUTDOWN":
                        response = "Server is shutting down."
                        client_socket.sendall(response.encode('utf-8'))
                        self.shutdown_flag = True
                        break
                    else:
                        response = self.process_command(message)
                        client_socket.sendall(response.encode('utf-8'))
                except ConnectionResetError:
                    break   # Client disconnected

    def process_command(self, command):
        # Dummy implementation of command processing
        # Replace with actual command processing logic
        if command == "PING":
            return "PONG"
        else:
            return f"Unknown command: {command}"

def parse_arguments():
    # Create the parser
    parser = argparse.ArgumentParser(description="Process some command-line arguments.")
    
    # Define arguments
    parser.add_argument('--port', type=int, help='Port number to connect to')
    parser.add_argument('--baudrate', type=int, default=9600, help='Baud rate for the serial connection')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--mode', choices=['manual', 'sequence', 'ttl'], default='manual', help='Arduino mode')
    
    # Parse the arguments
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Access the arguments
    port = args.port
    baudrate = args.baudrate
    verbose = args.verbose
    mode = args.mode
    
    # Print the arguments
    logging.info(f"Port: {port}")
    logging.info(f"Baudrate: {baudrate}")
    logging.info(f"Verbose: {verbose}")
    logging.info(f"Mode: {mode}")

    # Create and start the server
    server = Server(port, baudrate, verbose, mode)
    server.start()

if __name__ == "__main__":
    main()