"""ThingsBoard MQTT Communication Package.

This package provides a Pythonic interface for communicating with ThingsBoard
using MQTT protocol. It supports:
- Telemetry data transmission with device metadata
- Prediction data transmission
- Asynchronous communication for better performance
- Proper error handling and logging
- Type-safe configuration management

The main entry point is the ThingsBoardClient class, which can be accessed
via the get_thingsboard_client() function. The module uses constants
defined in the root constants.py file.
"""

from .client import ThingsBoardClient, get_thingsboard_client

__all__ = [
    'ThingsBoardClient', 
    'get_thingsboard_client'
] 