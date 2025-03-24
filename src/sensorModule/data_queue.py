"""
Thread-safe FIFO queue implementation for sensor data.

This module provides a thread-safe queue implementation using Python's deque
with proper synchronization for concurrent access.
"""

from collections import deque
from typing import Any, Optional
import threading
import time
from queue import Empty


class DataQueue:
    """Thread-safe FIFO queue for sensor data.
    
    This class implements a thread-safe queue using Python's deque with proper
    synchronization for concurrent access. It provides methods for adding and
    retrieving data in a first-in-first-out manner.
    
    Attributes:
        _queue (deque): The underlying data structure
        _lock (threading.Lock): Lock for thread synchronization
        _not_empty (threading.Condition): Condition for waiting on data
    """
    
    def __init__(self):
        """Initialize an empty thread-safe queue."""
        self._queue = deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def put(self, data: Any) -> None:
        """Add data to the queue.
        
        Args:
            data: The data to add to the queue
        """
        with self._lock:
            self._queue.appendleft(data)
            self._not_empty.notify()

    def get(self, timeout: float = None) -> Optional[Any]:
        """Get and remove the next item from the queue.
        
        Args:
            timeout (float, optional): Maximum time to wait for data in seconds
            
        Returns:
            Optional[Any]: The next item in the queue or None if timeout occurred
            
        Raises:
            Empty: If timeout occurred and no data was available
        """
        with self._lock:
            if timeout is not None:
                endtime = time.time() + timeout
                while not self._queue:
                    remaining = endtime - time.time()
                    if remaining <= 0:
                        raise Empty
                    self._not_empty.wait(timeout=remaining)
            else:
                while not self._queue:
                    self._not_empty.wait()
                    
            if not self._queue:
                return None
            return self._queue.pop()

    def size(self) -> int:
        """Get the current size of the queue.
        
        Returns:
            int: Number of items in the queue
        """
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Check if the queue is empty.
        
        Returns:
            bool: True if queue is empty, False otherwise
        """
        with self._lock:
            return len(self._queue) == 0

    def is_available(self) -> bool:
        """Check if there is data available in the queue.
        
        Returns:
            bool: True if data is available, False otherwise
        """
        with self._lock:
            return len(self._queue) > 0

    def clear(self) -> None:
        """Remove all items from the queue."""
        with self._lock:
            self._queue.clear() 