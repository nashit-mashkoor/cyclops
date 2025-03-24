"""
Mock LCD Implementation

This module provides a mock implementation of the LCD interface for development
and testing purposes. It simulates the behavior of a physical LCD display
using terminal output with ANSI escape codes for colors.

This implementation is useful for:
- Development without physical hardware
- Testing LCD interface functionality
- Debugging display logic
- CI/CD environments
"""

import os
from typing import Optional, Union

from .lcd import LCDInterface, EventState


class MockLCD(LCDInterface):
    """
    Mock implementation of the LCD interface using terminal output.
    
    This class simulates the behavior of a physical LCD display by:
    - Using terminal output instead of physical hardware
    - Simulating RGB backlight with ANSI escape codes
    - Maintaining a virtual display buffer
    - Providing visual feedback for all LCD operations
    
    Attributes:
        MAX_COLUMNS (int): Maximum number of columns (16)
        MAX_ROWS (int): Maximum number of rows (2)
        _current_row1 (str): Current content of first row
        _current_row2 (str): Current content of second row
        _current_color (tuple): Current RGB color values
    """

    MAX_COLUMNS: int = 16
    MAX_ROWS: int = 2

    def __init__(self, columns: int, rows: int) -> None:
        """
        Initialize the mock LCD.
        
        Args:
            columns: Number of columns (16)
            rows: Number of rows (2)
        """
        self._current_row1 = ""
        self._current_row2 = ""
        self._current_color = (255, 255, 255)  # Default white
        self._clear_screen()

    def _clear_screen(self) -> None:
        """Clear the terminal screen using ANSI escape codes."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _set_background_color(self, event_state: EventState) -> None:
        """
        Set the terminal background color based on event state.
        
        Args:
            event_state: Current event state
        """
        color_map = {
            EventState.GREEN: (0, 255, 0),
            EventState.YELLOW: (255, 255, 0),
            EventState.RED: (255, 0, 0),
            EventState.BLACK: (0, 0, 0),
            EventState.UNKNOWN: (128, 128, 128)
        }
        self.set_rgb(*color_map.get(event_state, (128, 128, 128)))

    def _format_row_1(self, event_name: str, event_state: EventState) -> str:
        """
        Format the first row of the display.
        
        Args:
            event_name: Name of the event
            event_state: Current event state
            
        Returns:
            Formatted string for first row
        """
        state_str = event_state.name[:4]  # First 4 chars of state name
        return f"{event_name[:8]:<8} {state_str:>4}"

    def _format_row_2(self, event_value: float, temperature: float,
                     humidity: float, cpu_usage: float) -> str:
        """
        Format the second row of the display.
        
        Args:
            event_value: Current event value
            temperature: Current temperature
            humidity: Current humidity
            cpu_usage: Current CPU usage
            
        Returns:
            Formatted string for second row
        """
        # Ensure values are within valid ranges
        event_value = max(0, min(999, event_value))
        temperature = max(-99, min(99, temperature))
        humidity = max(0, min(99, humidity))
        cpu_usage = max(0, min(99, cpu_usage))
        
        return f"{event_value:3.0f} {temperature:2.0f}C {humidity:2.0f}% {cpu_usage:2.0f}%"

    def clear(self) -> None:
        """
        Clear the display.
        
        Implements the abstract method from LCDInterface.
        """
        self._current_row1 = ""
        self._current_row2 = ""
        self._clear_screen()

    def set_cursor(self, column: int, row: int) -> None:
        """
        Set the cursor position (simulated).
        
        Implements the abstract method from LCDInterface.
        
        Args:
            column: Column position (0-15)
            row: Row position (0-1)
        """
        # In mock implementation, cursor position is handled internally
        pass

    def printout(self, text: Union[str, int]) -> None:
        """
        Print text to the display.
        
        Implements the abstract method from LCDInterface.
        
        Args:
            text: Text or number to display
        """
        if isinstance(text, int):
            text = str(text)
        # In mock implementation, text is stored in the current row
        if len(self._current_row1) < self.MAX_COLUMNS:
            self._current_row1 += text[:self.MAX_COLUMNS - len(self._current_row1)]
        elif len(self._current_row2) < self.MAX_COLUMNS:
            self._current_row2 += text[:self.MAX_COLUMNS - len(self._current_row2)]

    def set_rgb(self, red: int, green: int, blue: int) -> None:
        """
        Set the RGB backlight color using ANSI escape codes.
        
        Implements the abstract method from LCDInterface.
        
        Args:
            red: Red component (0-255)
            green: Green component (0-255)
            blue: Blue component (0-255)
        """
        self._current_color = (red, green, blue)
        # ANSI escape code for background color
        print(f"\033[48;2;{red};{green};{blue}m", end='')

    def display_message(self, row1: str, row2: str) -> None:
        """
        Display a two-line message on the mock LCD.
        
        Args:
            row1: Text for first row
            row2: Text for second row
        """
        # Truncate messages if too long
        row1 = row1[:self.MAX_COLUMNS]
        row2 = row2[:self.MAX_COLUMNS]
        
        # Pad with spaces if too short
        row1 = row1.ljust(self.MAX_COLUMNS)
        row2 = row2.ljust(self.MAX_COLUMNS)
        
        self._current_row1 = row1
        self._current_row2 = row2
        
        # Clear screen and display message
        self._clear_screen()
        print(f"{row1}\n{row2}")
        # Reset color
        print("\033[0m", end='')

    def update(self, data: 'DisplayData') -> None:
        """
        Update the display with new information.
        
        Args:
            data: DisplayData object containing new information
        """
        # Format and display the message
        row1 = self._format_row_1(data.event_name, data.event_state)
        row2 = self._format_row_2(
            data.event_value,
            data.temperature,
            data.humidity,
            data.cpu_usage
        )
        
        # Set background color based on event state
        self._set_background_color(data.event_state)
        
        # Display the formatted message
        self.display_message(row1, row2)