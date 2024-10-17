#!/usr/bin/env python3
"""Pymodbus asynchronous client example.

An example of a single threaded synchronous client.

usage: simple_async_client.py

All options must be adapted in the code
The corresponding server must be started before e.g. as:
    python3 server_sync.py
"""
import asyncio

import pymodbus.client as ModbusClient
from pymodbus import (
    ExceptionResponse,
    FramerType,
    ModbusException,
    pymodbus_apply_logging_config,
)

# Define the coil address for the LED
LED_COIL_ADDRESS = 0

async def blink_led(client):
    """Blink an LED on and off."""
    while True:        
        try:
            # Turn the LED on
            await client.write_coil(0, True, slave=10)
            print("LED ON")
            await asyncio.sleep(1)  # Wait for 1 second

            # Turn the LED off
            await client.write_coil(0, False, slave=10)
            print("LED OFF")
            await asyncio.sleep(1)  # Wait for 1 second

        except ModbusException as e:
            print(f"Modbus error: {e}")
            break


async def run_async_simple_client(comm, host, port, framer=FramerType.SOCKET):
    """Run async client."""
    # activate debugging
    pymodbus_apply_logging_config("DEBUG")

    print("get client")
    if comm == "tcp":
        client = ModbusClient.AsyncModbusTcpClient(
            host,
            port=port,
            framer=framer,
            # timeout=10,
            # retries=3,
            # source_address=("localhost", 0),
        )
    elif comm == "udp":
        client = ModbusClient.AsyncModbusUdpClient(
            host,
            port=port,
            framer=framer,
            # timeout=10,
            # retries=3,
            # source_address=None,
        )
    elif comm == "serial":
        client = ModbusClient.AsyncModbusSerialClient(
            port,
            framer=framer,
            # timeout=10,
            retries=0,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            # handle_local_echo=False,
        )
    else:
        print(f"Unknown client {comm} selected")
        return

    print("connect to server")
    await client.connect()
    # test client is connected
    assert client.connected

    # Start blinking the LED
    await blink_led(client)


if __name__ == "__main__":
    print("Start async client")
    asyncio.run(
        run_async_simple_client("serial", "", "COM6"), debug=False
    )