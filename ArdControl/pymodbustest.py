#!/usr/bin/env python3
"""Pymodbus synchronous client example.

An example of a single threaded synchronous client.

usage: simple_sync_client.py

All options must be adapted in the code
The corresponding server must be started before e.g. as:
    python3 server_sync.py
"""

# --------------------------------------------------------------------------- #
# import the various client implementations
# --------------------------------------------------------------------------- #
import pymodbus.client as ModbusClient
from pymodbus import (
    ExceptionResponse,
    FramerType,
    ModbusException,
    pymodbus_apply_logging_config,
)
import time

def run_sync_simple_client(comm, host, port, framer=FramerType.SOCKET):
    """Run sync client."""
    # activate debugging
    pymodbus_apply_logging_config("DEBUG")

    print("get client")
    if comm == "tcp":
        client = ModbusClient.ModbusTcpClient(
            host,
            port=port,
            framer=framer,
            # timeout=10,
            # retries=3,
            # source_address=("localhost", 0),
        )
    elif comm == "udp":
        client = ModbusClient.ModbusUdpClient(
            host,
            port=port,
            framer=framer,
            # timeout=10,
            # retries=3,
            # source_address=None,
        )
    elif comm == "serial":
        client = ModbusClient.ModbusSerialClient(
            port,
            framer=framer,
            timeout=3,
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
    client.connect()

    time.sleep(5)


    print("get and verify data")
    try:
        client.write_coil(0, True, slave=10)
        rr = client.read_coils(0, 1, slave=10)
    except ModbusException as exc:
        print(f"Received ModbusException({exc}) from library")
        client.close()
        return
    if rr.isError():
        print(f"Received Modbus library error({rr})")
        client.close()
        return
    if isinstance(rr, ExceptionResponse):
        print(f"Received Modbus library exception ({rr})")
        # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
        client.close()

    print("close connection")
    client.close()


if __name__ == "__main__":
    run_sync_simple_client("serial", "127.0.0.1", "COM6")