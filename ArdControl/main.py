import argparse
import logging
from .arduinoController import Server

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