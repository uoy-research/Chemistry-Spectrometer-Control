import argparse
import logging
import time
from arduinoController import ArduinoController

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
    # args = parse_arguments()
    
    # Access the arguments
    #port = args.port
    #baudrate = args.baudrate
    #verbose = args.verbose
    #mode = args.mode
    
    # Print the arguments
    #logging.info(f"Port: {port}")
    #logging.info(f"Baudrate: {baudrate}")
    #logging.info(f"Verbose: {verbose}")
    #logging.info(f"Mode: {mode}")

    # Create and start the server

    # Test to manually switch a valve on and off
    server = ArduinoController(3, True, 0)
    server.start()
    while True:
        server.send_heartbeat()
        server.send_command("TURN_ON_OUTPUT_VALVE")
        time.sleep(4)
        server.send_command("TURN_OFF_OUTPUT_VALVE")

if __name__ == "__main__":
    main()