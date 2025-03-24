"""
LCD Module Interface

This module provides a high-level interface for controlling an RGB LCD display.
It implements the Facade pattern to simplify the interaction with the underlying
LCD implementations (physical or mock).

Classes:
    LCD: Main interface class for LCD operations
    LCDColor: Enum-like class for predefined colors
    EventState: Enumeration of possible event states
    DisplayData: Data structure for display information
    LCDInterface: Abstract base class for LCD implementations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union, Tuple, Type

from .rgb1602 import RGB1602, I2CError
from .mock_lcd import MockLCD


class LCDError(Exception):
    """Base exception for LCD-related errors."""
    pass


class LCDColor:
    """Predefined colors for LCD backlight."""
    RED: Tuple[int, int, int] = (255, 0, 0)
    GREEN: Tuple[int, int, int] = (0, 255, 0)
    BLUE: Tuple[int, int, int] = (0, 0, 255)
    WHITE: Tuple[int, int, int] = (255, 255, 255)
    PURPLE: Tuple[int, int, int] = (255, 0, 255)
    YELLOW: Tuple[int, int, int] = (255, 209, 0)
    PALE_BLUE: Tuple[int, int, int] = (0, 128, 60)
    DARK_BLUE: Tuple[int, int, int] = (80, 80, 145)
    GREEN_WHITE: Tuple[int, int, int] = (144, 249, 15)
    DARK_VIOLET: Tuple[int, int, int] = (148, 0, 110)
    GHOST_WHITE: Tuple[int, int, int] = (248, 248, 60)


class EventState(Enum):
    """Enumeration of possible event states."""
    GREEN = auto()
    YELLOW = auto()
    RED = auto()
    BLACK = auto()
    UNKNOWN = auto()


@dataclass
class DisplayData:
    """Data structure for display information."""
    event_name: str
    event_state: EventState
    event_value: float
    temperature: float
    humidity: float
    cpu_usage: float


class LCDInterface(ABC):
    """
    Abstract base class for LCD implementations.
    
    This class defines the interface that all LCD implementations must follow,
    whether they are physical hardware or mock implementations.
    """
    
    @abstractmethod
    def clear(self) -> None:
        """Clear the display."""
        pass

    @abstractmethod
    def set_cursor(self, column: int, row: int) -> None:
        """Set the cursor position."""
        pass

    @abstractmethod
    def printout(self, text: Union[str, int]) -> None:
        """Print text to the display."""
        pass

    @abstractmethod
    def set_rgb(self, red: int, green: int, blue: int) -> None:
        """Set the RGB backlight color."""
        pass


class LCD:
    """
    High-level interface for controlling the RGB LCD display.
    
    This class implements the Facade pattern to provide a simplified interface
    for controlling the LCD display, handling all the low-level details internally.
    
    Attributes:
        MAX_COLUMNS (int): Maximum number of columns (16)
        MAX_ROWS (int): Maximum number of rows (2)
        _lcd (LCDInterface): Underlying LCD implementation instance
    """

    MAX_COLUMNS: int = 16
    MAX_ROWS: int = 2

    def __init__(self, implementation: Optional[LCDInterface] = None) -> None:
        """
        Initialize the LCD interface.
        
        Args:
            implementation: An instance of LCDInterface implementation (default: creates RGB1602)
            
        Raises:
            LCDError: If LCD initialization fails
        """
        try:
            self._lcd = implementation if implementation is not None else RGB1602(self.MAX_COLUMNS, self.MAX_ROWS)
            self._lcd.set_cursor(0, 0)
        except Exception as e:
            raise LCDError(f"Failed to initialize LCD: {str(e)}")

    def display_message(self, line1: str, line2: str) -> None:
        """
        Display a two-line message on the LCD screen.
        
        Args:
            line1: First line of text (max 16 chars)
            line2: Second line of text (max 16 chars)
            
        Note:
            Messages longer than 16 characters will be truncated.
            
        Raises:
            LCDError: If display operation fails
        """
        if len(str(line1)) > self.MAX_COLUMNS or len(str(line2)) > self.MAX_COLUMNS:
            return
        try:
            self.clear()
            self._write_line(line1, 0)
            self._write_line(line2, 1)
        except Exception as e:
            raise LCDError(f"Failed to display message: {str(e)}")

    def _write_line(self, message: str, line: int) -> None:
        """
        Write a message to a specific line of the LCD.
        
        Args:
            message: Text to display
            line: Line number (0 or 1)
            
        Raises:
            LCDError: If write operation fails
        """
        try:
            self._lcd.set_cursor(0, line)
            self._lcd.printout(message)
        except Exception as e:
            raise LCDError(f"Failed to write line: {str(e)}")

    def clear(self) -> None:
        """
        Clear the LCD screen.
        
        Raises:
            LCDError: If clear operation fails
        """
        try:
            self._lcd.clear()
        except Exception as e:
            raise LCDError(f"Failed to clear display: {str(e)}")

    def set_cursor(self, column: int, line: int) -> None:
        """
        Move the cursor to the specified position.
        
        Args:
            column: Column position (0-15)
            line: Line number (0-1)
            
        Raises:
            LCDError: If cursor positioning fails
        """
        if 0 <= column < self.MAX_COLUMNS and 0 <= line < self.MAX_ROWS:
            try:
                self._lcd.set_cursor(column, line)
            except Exception as e:
                raise LCDError(f"Failed to set cursor: {str(e)}")

    def set_backlight_color(self, color: Tuple[int, int, int]) -> None:
        """
        Set the backlight color using RGB values.
        
        Args:
            color: Tuple of (red, green, blue) values (0-255)
            
        Raises:
            LCDError: If color setting fails
        """
        try:
            self._lcd.set_rgb(*color)
        except Exception as e:
            raise LCDError(f"Failed to set backlight color: {str(e)}")

    def _set_background_color(self, event_state: EventState) -> None:
        """
        Set the background color based on event state.
        
        Args:
            event_state: Current event state from EventState enum
            
        Raises:
            LCDError: If color setting fails
        """
        color_map = {
            EventState.GREEN: LCDColor.GREEN,
            EventState.YELLOW: LCDColor.YELLOW,
            EventState.RED: LCDColor.RED,
            EventState.BLACK: LCDColor.DARK_VIOLET,
            EventState.UNKNOWN: LCDColor.GHOST_WHITE
        }
        self.set_backlight_color(color_map.get(event_state, LCDColor.GHOST_WHITE))

    def _format_row_1(self, event_name: str, event_value: float) -> str:
        """
        Format the first row of the display.
        
        Args:
            event_name: Name of the event
            event_value: Value of the event
            
        Returns:
            Formatted string for first row
        """
        formatted_value = str(round(event_value, 2))
        return f"{event_name}: {formatted_value}" if len(event_name) + len(formatted_value) < self.MAX_COLUMNS else "Truncated Output"

    def _format_row_2(self, temp: float, humidity: float, cpu: float) -> str:
        """
        Format the second row of the display.
        
        Args:
            temp: Temperature value
            humidity: Humidity value
            cpu: CPU usage value
            
        Returns:
            Formatted string for second row
        """
        temp = int(temp % 100)
        humidity = int(humidity % 101)
        cpu = int(cpu % 101)
        
        return f"T{temp:02d}*C H{humidity:02d}% P{cpu:03d}%"

    def update(self, data: DisplayData) -> None:
        """
        Update the display with new information.
        
        Args:
            data: DisplayData object containing all display information
            
        Raises:
            LCDError: If update operation fails
        """
        try:
            self.clear()
            self._set_background_color(data.event_state)

            self._write_line(self._format_row_1(data.event_name, data.event_value), 0)
            self._write_line(self._format_row_2(data.temperature, data.humidity, data.cpu_usage), 1)
        except Exception as e:
            raise LCDError(f"Failed to update display: {str(e)}")

    def __del__(self) -> None:
        """Cleanup when the object is destroyed."""
        if hasattr(self, '_lcd'):
            try:
                del self._lcd
            except Exception:
                pass  # Ignore cleanup errors
