"""
Serial communication interface for sensor data collection.

This module provides a robust interface for serial communication with the sensor,
including proper error handling and resource management.
"""

import serial
from typing import Optional
from serial.serialutil import SerialException
import logging


class SerialCommunicator:
    """Handles serial communication with the sensor.
    
    This class provides a clean interface for serial communication, including:
    - Connection management
    - Data reading
    - Buffer management
    - Error handling
    
    Attributes:
        _port (str): Serial port to connect to
        _baud_rate (int): Baud rate for communication
        _serial (serial.Serial): Serial connection object
        _logger (logging.Logger): Logger instance for error reporting
    """
    
    def __init__(self, port: str, baud_rate: int):
        """Initialize the serial communicator.
        
        Args:
            port (str): Serial port to connect to
            baud_rate (int): Baud rate for communication
            
        Raises:
            SerialException: If connection fails
        """
        self._port = port
        self._baud_rate = baud_rate
        self._serial = None
        self._logger = logging.getLogger(__name__)
        self._connect()

    def _connect(self) -> None:
        """Establish serial connection.
        
        Raises:
            SerialException: If connection fails
        """
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baud_rate,
                timeout=None,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            self._logger.info(f"Successfully connected to {self._port} at {self._baud_rate} baud")
        except SerialException as e:
            self._logger.error(f"Failed to connect to {self._port}: {str(e)}")
            raise

    def is_data_available(self) -> bool:
        """Check if data is available to read.
        
        Returns:
            bool: True if data is available, False otherwise
            
        Raises:
            SerialException: If connection is lost
        """
        try:
            return self._serial.in_waiting > 0
        except SerialException:
            self._logger.warning("Connection lost, attempting to reconnect")
            self._reconnect()
            return False

    def read_until(self, terminator: bytes) -> Optional[str]:
        """Read data until terminator is found.
        
        Args:
            terminator (bytes): Bytes to read until
            
        Returns:
            Optional[str]: Read data or None if no data available
            
        Raises:
            SerialException: If connection is lost
        """
        if not self.is_data_available():
            return None
            
        try:
            data = str(self._serial.read_until(terminator))
            return data.replace("b'", "")  # Remove b' added by serial comm
        except SerialException:
            self._logger.warning("Connection lost while reading, attempting to reconnect")
            self._reconnect()
            return None

    def read(self) -> Optional[bytes]:
        """Read a single byte.
        
        Returns:
            Optional[bytes]: Read byte or None if no data available
            
        Raises:
            SerialException: If connection is lost
        """
        if not self.is_data_available():
            return None
            
        try:
            return self._serial.read()
        except SerialException:
            self._logger.warning("Connection lost while reading, attempting to reconnect")
            self._reconnect()
            return None

    def flush(self) -> None:
        """Flush the serial buffer.
        
        Raises:
            SerialException: If connection is lost
        """
        try:
            self._serial.flush()
        except SerialException:
            self._logger.warning("Connection lost while flushing, attempting to reconnect")
            self._reconnect()

    def _reconnect(self) -> None:
        """Attempt to reconnect to the serial port.
        
        Raises:
            SerialException: If reconnection fails
        """
        self.close()
        self._connect()

    def close(self) -> None:
        """Close the serial connection."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
                self._logger.info(f"Closed connection to {self._port}")
            except SerialException as e:
                self._logger.error(f"Error closing connection: {str(e)}")
            finally:
                self._serial = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 