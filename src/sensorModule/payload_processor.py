"""
Payload processor for sensor data.

This module provides functionality to process raw sensor data into a structured format,
including timestamp addition and data validation.
"""

import time
from typing import List, Any
import constants as const


class PayloadProcessor:
    """Processes raw sensor data into structured format.
    
    This class handles the processing of raw sensor data, including:
    - Removing payload separators
    - Splitting values
    - Adding timestamps
    - Data validation
    
    Attributes:
        _separator (str): The separator used in the payload
    """
    
    def __init__(self):
        """Initialize the payload processor."""
        self._separator = const.VALUE_SEPARATOR

    def process_payload(self, payload: str) -> List[Any]:
        """Process a raw payload into structured data.
        
        Args:
            payload (str): Raw payload string to process
            
        Returns:
            List[Any]: Processed data with timestamp
            
        Raises:
            ValueError: If payload is invalid or empty
        """
        if not payload:
            raise ValueError("Empty payload received")
            
        # Remove the payload separator
        payload = self._remove_separator(payload)
        
        # Split the values
        values = self._split_values(payload)
        
        # Add timestamp
        return self._add_timestamp(values)

    def _remove_separator(self, payload: str) -> str:
        """Remove the payload separator from the end of the payload.
        
        Args:
            payload (str): Raw payload string
            
        Returns:
            str: Payload without the separator
        """
        index = payload.rfind(const.PAYLOAD_SEPARATOR)
        if index == -1:
            return payload
        return payload[:index]

    def _split_values(self, payload: str) -> List[str]:
        """Split the payload into individual values.
        
        Args:
            payload (str): Payload string to split
            
        Returns:
            List[str]: List of individual values
        """
        return payload.split(self._separator, maxsplit=-1)

    def _add_timestamp(self, values: List[str]) -> List[Any]:
        """Add ISO format timestamp to the values.
        
        Args:
            values (List[str]): List of sensor values
            
        Returns:
            List[Any]: Values with timestamp appended
        """
        values.append(time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        return values 