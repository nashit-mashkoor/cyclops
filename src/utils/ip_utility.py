"""Utility module for IP address operations."""

import socket
from typing import Optional


class IPUtility:
    """Utility class for IP address operations.
    
    This class provides methods to get the local IP address of the machine.
    It uses a UDP socket to determine the IP address, falling back to localhost
    if the operation fails.
    """
    
    @staticmethod
    def get_ip() -> str:
        """Get the local IP address of the machine.
        
        Returns:
            str: The local IP address. Returns '127.0.0.1' if the operation fails.
            
        Note:
            This method uses a UDP socket to determine the IP address. It attempts
            to connect to a non-existent IP (10.254.254.254) to get the local
            interface address. This is a common technique to get the local IP
            without relying on hostname resolution.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0)
            try:
                # doesn't even have to be reachable
                sock.connect(('10.254.254.254', 1))
                return sock.getsockname()[0]
            except Exception:
                return '127.0.0.1'