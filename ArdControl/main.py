import argparse
import logging
import time
from arduinoController import ArduinoController


def parse_arguments():
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Process some command-line arguments.")

    # Define arguments
    parser.add_argument('--port', type=int, help='Port number to connect to')
    parser.add_argument('--baudrate', type=int, default=9600,
                        help='Baud rate for the serial connection')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument(
        '--mode', choices=['manual', 'sequence', 'ttl'], default='manual', help='Arduino mode')

    # Parse the arguments
    return parser.parse_args()


def main():
    # args = parse_arguments()

    # Access the arguments
    # port = args.port
    # baudrate = args.baudrate
    # verbose = args.verbose
    # mode = args.mode

    # Print the arguments
    # logging.info(f"Port: {port}")
    # logging.info(f"Baudrate: {baudrate}")
    # logging.info(f"Verbose: {verbose}")
    # logging.info(f"Mode: {mode}")

    # Create and start the server

    # Test to manually switch a valve on and off
    server = ArduinoController(4, True, 0)
    server.start()
    time.sleep(2)
    server.send_command("SWITCH_TO_MANUAL")
    time.sleep(1)
    server.send_command("ENABLE_PRESSURE_LOG")

    # Wait for user input and send command if it exists in commands_dict values
    while True:
        user_input = input("Enter a command: ")
        if user_input in server.commands_dict.values():
            server.send_command(user_input)
            print(f"Command '{user_input}' sent to the server.")
        else:
            print(f"Invalid command: '{user_input}'")


if __name__ == "__main__":
    main()
