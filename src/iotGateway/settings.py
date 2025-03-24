"""Configuration settings for the ThingsBoard MQTT communication module.

This module provides type-safe configuration management using Pydantic models.
All environment variables are loaded and validated here.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Load environment variables from .env file
load_dotenv()


class ThingsBoardSettings(BaseSettings):
    """ThingsBoard connection settings."""
    host: str = Field(..., env='THINGSBOARD_HOST')
    port: int = Field(..., env='THINGSBOARD_PORT')
    device_token: str = Field(..., env='THINGSBOARD_DEVICE_TOKEN')
    connection_timeout: int = 2
    keepalive: int = 2


class DeviceSettings(BaseSettings):
    """Device-specific settings."""
    type: str = Field(..., env='EDGE_DEVICE_TYPE')
    serial_number: str = Field(..., env='EDGE_DEVICE_SERIAL_NUMBER')
    manufacturer: str = Field(..., env='EDGE_DEVICE_MANUFACTURER')
    hardware_version: str = Field(..., env='EDGE_DEVICE_HW_VERSION')
    payload_version: str = Field(..., env='MQTT_PAYLOAD_VERSION')
    assembled_by: str = Field(..., env='DEVICE_ASSEMBLED_BY')
    assembly_version: str = Field(..., env='DEVICE_ASSEMBLY_VERSION')
    manufactured_at: str = Field(..., env='DEVICE_MANUFACTURED_AT')


class ComponentSettings(BaseSettings):
    """Settings for various device components."""
    sbc_type: str = Field(..., env='SBC_TYPE')
    sbc_manufacturer: str = Field(..., env='SBC_MANUFACTURER')
    sbc_hardware_version: str = Field(..., env='SBC_HARDWARE_VERSION')
    sbc_serial_number_location: str = Field(..., env='SBC_SERIAL_NUMBER_LOCATION')
    
    bfu_type: str = Field(..., env='BFU_TYPE')
    bfu_manufacturer: str = Field(..., env='BFU_MANUFACTURER')
    bfu_hardware_version: str = Field(..., env='BFU_HARDWARE_VERSION')
    bfu_firmware_version: str = Field(..., env='BFU_FIRMWARE_VERSION')
    
    lcd_type: str = Field(..., env='LCD_TYPE')
    lcd_manufacturer: str = Field(..., env='LCD_MANUFACTURER')


class StatisticsSettings(BaseSettings):
    """Device statistics settings."""
    boot_count_location: str = Field(..., env='STAT_BOOT_COUNT')
    boot_at_location: str = Field(..., env='STAT_BOOT_AT')
    time_since_boot_location: str = Field(..., env='STAT_TIME_SINCE_BOOT')
    warmup_time: int = Field(..., env='STAT_WARMUP_TIME')
    
    # Read values from system and provide fallbacks
    def get_boot_count(self) -> int:
        """Get the boot count with fallback.
        
        Returns:
            int: The boot count value or 0 if unavailable.
        """
        try:
            return int(os.popen(self.boot_count_location).read())
        except Exception:
            return 0
    
    def get_boot_at(self) -> str:
        """Get the boot timestamp with fallback.
        
        Returns:
            str: The boot timestamp or current time if unavailable.
        """
        try:
            return str(os.popen(self.boot_at_location).read()).replace("\n", "")
        except Exception:
            from datetime import datetime
            return datetime.now().isoformat()
    
    def get_time_since_boot(self) -> int:
        """Get time since boot with fallback.
        
        Returns:
            int: The time since boot in seconds or 0 if unavailable.
        """
        try:
            import re
            time_str = os.popen(self.time_since_boot_location).read()
            return int(re.sub("[^0-9]", "", time_str))
        except Exception:
            return 0


class ConnectionSettings(BaseSettings):
    """Connection settings."""
    test_wifi_command: str = Field(default="iwconfig", env='TEST_WIFI_CONNECTION')
    
    def test_wifi_connection(self) -> bool:
        """Test if WiFi is connected.
        
        Returns:
            bool: True if WiFi is connected, False otherwise.
        """
        try:
            result = str(os.popen(self.test_wifi_command).read())
            return "state UP" in result
        except Exception:
            return False


class Settings(BaseSettings):
    """Main configuration settings class."""
    thingsboard: ThingsBoardSettings = ThingsBoardSettings()
    device: DeviceSettings = DeviceSettings()
    components: ComponentSettings = ComponentSettings()
    statistics: StatisticsSettings = StatisticsSettings()
    connection: ConnectionSettings = ConnectionSettings()
    
    class Config:
        env_file = '.env'
        case_sensitive = True


# Global settings instance
settings = Settings()
