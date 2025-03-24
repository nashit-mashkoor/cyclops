"""
RGB1602 LCD Driver

This module provides low-level driver functionality for the Waveshare LCD1602 RGB Module.
It handles direct I2C communication with the display and RGB backlight.

Reference:
    https://www.waveshare.com/wiki/LCD1602_RGB_Module
"""

import time
from dataclasses import dataclass
from typing import Optional, Union

from smbus import SMBus
from .lcd import LCDInterface


class LCDError(Exception):
    """Base exception for LCD-related errors."""
    pass


class I2CError(LCDError):
    """Exception raised for I2C communication errors."""
    pass


@dataclass
class LCDRegisters:
    """LCD register addresses and flags."""
    # Device I2C Addresses
    LCD_ADDRESS: int = 0x7c >> 1
    RGB_ADDRESS: int = 0xc0 >> 1

    # RGB Backlight Registers
    REG_RED: int = 0x04
    REG_GREEN: int = 0x03
    REG_BLUE: int = 0x02
    REG_MODE1: int = 0x00
    REG_MODE2: int = 0x01
    REG_OUTPUT: int = 0x08

    # LCD Commands
    LCD_CLEARDISPLAY: int = 0x01
    LCD_RETURNHOME: int = 0x02
    LCD_ENTRYMODESET: int = 0x04
    LCD_DISPLAYCONTROL: int = 0x08
    LCD_CURSORSHIFT: int = 0x10
    LCD_FUNCTIONSET: int = 0x20
    LCD_SETCGRAMADDR: int = 0x40
    LCD_SETDDRAMADDR: int = 0x80

    # Display Entry Mode Flags
    LCD_ENTRYRIGHT: int = 0x00
    LCD_ENTRYLEFT: int = 0x02
    LCD_ENTRYSHIFTINCREMENT: int = 0x01
    LCD_ENTRYSHIFTDECREMENT: int = 0x00

    # Display Control Flags
    LCD_DISPLAYON: int = 0x04
    LCD_DISPLAYOFF: int = 0x00
    LCD_CURSORON: int = 0x02
    LCD_CURSOROFF: int = 0x00
    LCD_BLINKON: int = 0x01
    LCD_BLINKOFF: int = 0x00

    # Display/Cursor Shift Flags
    LCD_DISPLAYMOVE: int = 0x08
    LCD_CURSORMOVE: int = 0x00
    LCD_MOVERIGHT: int = 0x04
    LCD_MOVELEFT: int = 0x00

    # Function Set Flags
    LCD_8BITMODE: int = 0x10
    LCD_4BITMODE: int = 0x00
    LCD_2LINE: int = 0x08
    LCD_1LINE: int = 0x00
    LCD_5x8DOTS: int = 0x00


class RGB1602(LCDInterface):
    """
    Driver class for the Waveshare LCD1602 RGB Module.
    
    This class handles the low-level communication with the LCD display and RGB backlight
    through I2C interface.
    
    Attributes:
        _bus (SMBus): I2C bus interface
        _registers (LCDRegisters): Register addresses and flags
        _num_lines (int): Number of display lines
        _curr_line (int): Current cursor line
        _show_function (int): Display function flags
        _show_control (int): Display control flags
        _show_mode (int): Display mode flags
        _last_rgb (tuple): Last set RGB color values
    """

    # Timing constants (in seconds)
    INIT_DELAY: float = 0.05
    COMMAND_DELAY: float = 0.005
    CLEAR_DELAY: float = 0.002

    def __init__(self, columns: int, rows: int) -> None:
        """
        Initialize the RGB1602 driver.
        
        Args:
            columns: Number of columns (16)
            rows: Number of rows (2)
            
        Raises:
            I2CError: If I2C communication fails
        """
        try:
            self._bus = SMBus(1)
            self._registers = LCDRegisters()
            self._num_lines = rows
            self._curr_line = 0
            self._show_function = self._registers.LCD_4BITMODE | self._registers.LCD_1LINE | self._registers.LCD_5x8DOTS
            self._last_rgb = (255, 255, 255)  # Default white
            self.begin(rows, columns)
        except Exception as e:
            raise I2CError(f"Failed to initialize I2C bus: {str(e)}")

    def _safe_write(self, address: int, register: int, value: int) -> None:
        """
        Safely write a value to an I2C register with error handling.
        
        Args:
            address: I2C device address
            register: Register address
            value: Value to write
            
        Raises:
            I2CError: If write operation fails
        """
        try:
            self._bus.write_byte_data(address, register, value)
        except Exception as e:
            raise I2CError(f"Failed to write to I2C register: {str(e)}")

    def command(self, cmd: int) -> None:
        """
        Send a command to the LCD.
        
        Args:
            cmd: Command byte to send
            
        Raises:
            I2CError: If command fails
        """
        self._safe_write(self._registers.LCD_ADDRESS, 0x80, cmd)

    def write(self, data: int) -> None:
        """
        Write data to the LCD.
        
        Args:
            data: Data byte to write
            
        Raises:
            I2CError: If write fails
        """
        self._safe_write(self._registers.LCD_ADDRESS, 0x40, data)

    def set_reg(self, reg: int, data: int) -> None:
        """
        Set a register value for the RGB backlight.
        
        Args:
            reg: Register address
            data: Data to write to register
            
        Raises:
            I2CError: If register write fails
        """
        self._safe_write(self._registers.RGB_ADDRESS, reg, data)

    def clear(self) -> None:
        """
        Clear the display.
        
        Implements the abstract method from LCDInterface.
        
        Raises:
            I2CError: If clear operation fails
        """
        try:
            self.command(self._registers.LCD_CLEARDISPLAY)
            time.sleep(self.CLEAR_DELAY)
        except Exception as e:
            raise I2CError(f"Failed to clear display: {str(e)}")

    def set_cursor(self, column: int, row: int) -> None:
        """
        Set the cursor position.
        
        Implements the abstract method from LCDInterface.
        
        Args:
            column: Column position (0-15)
            row: Row position (0-1)
            
        Raises:
            I2CError: If cursor positioning fails
        """
        try:
            if row == 0:
                column |= 0x80
            else:
                column |= 0xc0
            self.command(column)
        except Exception as e:
            raise I2CError(f"Failed to set cursor: {str(e)}")

    def printout(self, text: Union[str, int]) -> None:
        """
        Print text to the display.
        
        Implements the abstract method from LCDInterface.
        
        Args:
            text: Text or number to display
            
        Raises:
            I2CError: If text printing fails
        """
        try:
            if isinstance(text, int):
                text = str(text)
            for char in text.encode('utf-8'):
                self.write(char)
        except Exception as e:
            raise I2CError(f"Failed to print text: {str(e)}")

    def set_rgb(self, red: int, green: int, blue: int) -> None:
        """
        Set the RGB backlight color.
        
        Implements the abstract method from LCDImplementation.
        
        Args:
            red: Red component (0-255)
            green: Green component (0-255)
            blue: Blue component (0-255)
            
        Raises:
            I2CError: If color setting fails
        """
        try:
            # Only update if color has changed
            if (red, green, blue) != self._last_rgb:
                self.set_reg(self._registers.REG_RED, red)
                self.set_reg(self._registers.REG_GREEN, green)
                self.set_reg(self._registers.REG_BLUE, blue)
                self._last_rgb = (red, green, blue)
        except Exception as e:
            raise I2CError(f"Failed to set RGB color: {str(e)}")

    def begin(self, rows: int, columns: int) -> None:
        """
        Initialize the display.
        
        Args:
            rows: Number of rows
            columns: Number of columns
            
        Raises:
            I2CError: If initialization fails
        """
        try:
            if rows > 1:
                self._show_function |= self._registers.LCD_2LINE

            self._num_lines = rows
            self._curr_line = 0

            time.sleep(self.INIT_DELAY)

            # Send function set command sequence
            for _ in range(3):
                self.command(self._registers.LCD_FUNCTIONSET | self._show_function)
                time.sleep(self.COMMAND_DELAY)
            
            # Set display lines, font size, etc.
            self.command(self._registers.LCD_FUNCTIONSET | self._show_function)
            
            # Turn on display with no cursor or blinking
            self._show_control = self._registers.LCD_DISPLAYON | self._registers.LCD_CURSOROFF | self._registers.LCD_BLINKOFF
            self.display()
            
            # Clear display
            self.clear()
            
            # Set text direction (left to right)
            self._show_mode = self._registers.LCD_ENTRYLEFT | self._registers.LCD_ENTRYSHIFTDECREMENT
            self.command(self._registers.LCD_ENTRYMODESET | self._show_mode)

            # Initialize RGB backlight
            self.set_reg(self._registers.REG_MODE1, 0)
            self.set_reg(self._registers.REG_OUTPUT, 0xFF)
            self.set_reg(self._registers.REG_MODE2, 0x20)

            self.set_color_white()
        except Exception as e:
            raise I2CError(f"Failed to initialize display: {str(e)}")

    def display(self) -> None:
        """
        Turn on the display.
        
        Raises:
            I2CError: If display control fails
        """
        try:
            self._show_control |= self._registers.LCD_DISPLAYON
            self.command(self._registers.LCD_DISPLAYCONTROL | self._show_control)
        except Exception as e:
            raise I2CError(f"Failed to control display: {str(e)}")

    def set_color_white(self) -> None:
        """
        Set the backlight to white.
        
        Raises:
            I2CError: If color setting fails
        """
        self.set_rgb(255, 255, 255)

    def __del__(self) -> None:
        """Cleanup when the object is destroyed."""
        if hasattr(self, '_bus'):
            try:
                del self._bus
            except Exception:
                pass  # Ignore cleanup errors
