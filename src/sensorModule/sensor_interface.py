"""
Main sensor interface for Cyclops.

This module provides the primary interface for sensor data collection and processing.
It implements a producer-consumer pattern using a background thread for data collection
and a queue for data processing.

Example:
    >>> sensor = SensorInterface(port="/dev/ttyUSB0", baud_rate=115200)
    >>> sensor.start_collection()
    >>> data = sensor.get_sample()
    >>> sensor.stop_collection()
"""

import threading
from typing import Optional, List, Any
from time import sleep
from queue import Empty
import logging

from .data_queue import DataQueue
from .payload_processor import PayloadProcessor
from .serial_communicator import SerialCommunicator
import constants as const


class SensorInterface:
    """Main interface for sensor data collection and processing.
    
    This class manages the sensor data collection process using a background thread
    and provides methods to control the collection and access the collected data.
    
    Attributes:
        _end_of_payload (bytes): End of payload marker in ASCII
        _nb_of_value_separators (int): Number of telemetry values expected
        _collection_enabled (bool): Flag to control data collection
        _thread_active (bool): Flag to control the background thread
        _buffer_size (int): Size of the internal buffer for data collection
        _logger (logging.Logger): Logger instance for error reporting
    """
    
    def __init__(self, port: str = const.SERIAL_PORT, baud_rate: int = const.SERIAL_BAUD, buffer_size: int = 1000):
        """Initialize the sensor interface.
        
        Args:
            port (str): Serial port to connect to
            baud_rate (int): Baud rate for serial communication
            buffer_size (int): Maximum number of samples to store in the queue
        """
        self._end_of_payload = bytes(const.END_OF_PAYLOAD, "ascii")
        self._nb_of_value_separators = const.NB_OF_TELEMETRY_VALUES
        self._collection_enabled = True
        self._thread_active = True
        self._buffer_size = buffer_size
        self._logger = logging.getLogger(__name__)
        
        self._serial = SerialCommunicator(port, baud_rate)
        self._processor = PayloadProcessor()
        self._queue = DataQueue()
        self._collection_thread = threading.Thread(target=self._collection_loop)
        self._collection_thread.daemon = True
        self._collection_thread.start()
        self._logger.info("Sensor interface initialized successfully")

    def get_sample(self, timeout: float = 0.1) -> Optional[List[Any]]:
        """Get the next sample from the queue.
        
        Args:
            timeout (float): Maximum time to wait for a sample in seconds
            
        Returns:
            Optional[List[Any]]: Processed sensor data or None if queue is empty
        """
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def is_sample_available(self) -> bool:
        """Check if there are samples available in the queue.
        
        Returns:
            bool: True if samples are available, False otherwise
        """
        return self._queue.is_available()

    def get_sample_count(self) -> int:
        """Get the number of samples in the queue.
        
        Returns:
            int: Number of samples in the queue
        """
        return self._queue.size()

    def flush_samples(self) -> None:
        """Clear all samples from the queue and flush the serial buffer."""
        self._serial.flush()
        self._queue.clear()
        self._logger.debug("Samples flushed successfully")

    def start_collection(self) -> None:
        """Enable sample collection."""
        self._serial.flush()
        self._collection_enabled = True
        self._logger.info("Sample collection started")

    def stop_collection(self) -> None:
        """Disable sample collection."""
        self._collection_enabled = False
        self._logger.info("Sample collection stopped")

    def shutdown(self) -> None:
        """Stop the collection thread and clean up resources."""
        self._collection_enabled = False
        self._thread_active = False
        self._collection_thread.join(timeout=1.0)  # Add timeout to prevent hanging
        self._serial.close()
        self._logger.info("Sensor interface shutdown complete")

    def _is_payload_complete(self, payload: str) -> bool:
        """Check if a payload is complete based on separator count.
        
        Args:
            payload (str): Raw payload to check
            
        Returns:
            bool: True if payload is complete, False otherwise
        """
        return payload.count(const.VALUE_SEPARATOR) == self._nb_of_value_separators

    def _process_payload(self) -> None:
        """Process a single payload from the serial connection."""
        if not self._serial.is_data_available():
            return
            
        payload = self._serial.read_until(self._end_of_payload)
        if payload and self._is_payload_complete(payload):
            try:
                processed_data = self._processor.process_payload(payload)
                if self._queue.size() < self._buffer_size:
                    self._queue.put(processed_data)
            except ValueError as e:
                self._logger.error(f"Error processing payload: {e}")

    def _collection_loop(self) -> None:
        """Background thread loop for continuous data collection."""
        while self._thread_active:
            if not self._collection_enabled:
                sleep(0.1)  # Reduce CPU usage when collection is disabled
                continue
                
            self._process_payload()
            sleep(const.SERIAL_COLLECT_INTERVAL)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown() 