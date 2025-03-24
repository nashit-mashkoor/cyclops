"""
Sensor Module for Cyclops

This module provides a Python interface for sensor data collection and processing.
It implements a producer-consumer pattern for efficient data handling and real-time
processing of sensor data through serial communication.

Classes:
    SensorInterface: Main interface for sensor data collection and processing
    DataQueue: Thread-safe FIFO queue for sensor data
    PayloadProcessor: Processes raw sensor data into structured format
    SerialCommunicator: Handles serial communication with the sensor
"""

from .sensor_interface import SensorInterface
from .data_queue import DataQueue
from .payload_processor import PayloadProcessor
from .serial_communicator import SerialCommunicator

__all__ = ['SensorInterface', 'DataQueue', 'PayloadProcessor', 'SerialCommunicator'] 