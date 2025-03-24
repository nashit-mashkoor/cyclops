"""Main ThingsBoard communication module.

This module provides the main interface for communicating with ThingsBoard,
handling both telemetry and prediction data.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import constants as const
from tb_device_mqtt import TBDeviceMqttClient

from .settings import settings
from .models import (
    Assembly,
    Metadata,
    PredictionPayload,
    Statistics,
    Telemetry,
    TelemetryPayload
)

logger = logging.getLogger(__name__)


class MQTTInterface:
    """Async interface for MQTT communication with ThingsBoard."""

    def __init__(self):
        """Initialize the MQTT interface."""
        self._client = TBDeviceMqttClient(
            host=settings.thingsboard.host,
            port=settings.thingsboard.port,
            token=settings.thingsboard.device_token
        )
        self._connected = False
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Connect to ThingsBoard MQTT broker.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._client.connect,
                settings.thingsboard.connection_timeout,
                settings.thingsboard.keepalive
            )
            self._connected = True
            logger.info("Successfully connected to ThingsBoard MQTT broker")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ThingsBoard: {str(e)}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from ThingsBoard MQTT broker."""
        if not self._connected:
            return

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._client.disconnect
            )
            self._connected = False
            logger.info("Successfully disconnected from ThingsBoard MQTT broker")
        except Exception as e:
            logger.error(f"Error disconnecting from ThingsBoard: {str(e)}")

    @property
    def is_connected(self) -> bool:
        """Check if connected to ThingsBoard.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected and self._client.is_connected()

    async def send_telemetry(self, payload: Dict[str, Any]) -> Optional[Dict]:
        """Send telemetry data to ThingsBoard.

        Args:
            payload: The telemetry data to send.

        Returns:
            Optional[Dict]: Response from ThingsBoard if successful, None otherwise.
        """
        if not self.is_connected:
            logger.error("Not connected to ThingsBoard")
            return None

        async with self._lock:
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._client.send_telemetry,
                    payload,
                    0  # QoS level
                )
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    result.get
                )
            except Exception as e:
                logger.error(f"Failed to send telemetry: {str(e)}")
                return None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class ThingsBoardClient:
    """Client for communicating with ThingsBoard."""

    def __init__(self):
        """Initialize the ThingsBoard client."""
        self._mqtt = MQTTInterface()
        self._connected = False
        # Number of connection attempts
        self._max_connection_attempts = const.NB_OF_THINGSBOARD_CONNECT_ATTEMPTS

    @property
    def is_connected(self) -> bool:
        """Check if connected to ThingsBoard MQTT broker.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected and self._mqtt.is_connected

    async def connect(self) -> bool:
        """Connect to ThingsBoard.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        if self._connected:
            return True

        # First check if WiFi is connected
        if not settings.connection.test_wifi_connection():
            logger.error("WiFi is not connected")
            return False

        # Try connecting multiple times
        for attempt in range(self._max_connection_attempts):
            logger.info(f"Connection attempt {attempt + 1}/{self._max_connection_attempts}")
            self._connected = await self._mqtt.connect()
            if self._connected:
                logger.info("Successfully connected to ThingsBoard")
                return True
            await asyncio.sleep(1)  # Wait before retrying

        logger.error(f"Failed to connect after {self._max_connection_attempts} attempts")
        return False

    async def disconnect(self) -> None:
        """Disconnect from ThingsBoard."""
        if not self._connected:
            return

        await self._mqtt.disconnect()
        self._connected = False

    def _create_assemblies(self, bfu_device_id: str) -> List[Assembly]:
        """Create assembly objects for device components.

        Args:
            bfu_device_id: The BFU device ID.

        Returns:
            List[Assembly]: List of assembly objects.
        """
        assemblies = [
            Assembly(
                type=settings.components.sbc_type,
                manufacturer=settings.components.sbc_manufacturer,
                serial_number=os.popen(settings.components.sbc_serial_number_location).read().rstrip('\x00'),
                hardware_version=settings.components.sbc_hardware_version
            ),
            Assembly(
                type=settings.components.bfu_type,
                manufacturer=settings.components.bfu_manufacturer,
                serial_number=bfu_device_id,
                hardware_version=settings.components.bfu_hardware_version,
                firmware_version=settings.components.bfu_firmware_version
            ),
            Assembly(
                type=settings.components.lcd_type,
                manufacturer=settings.components.lcd_manufacturer
            )
        ]
        return assemblies

    def _create_telemetry_objects(self, telemetry_data: List[Union[int, float, str, bool]]) -> List[Telemetry]:
        """Create telemetry objects from data values.

        Args:
            telemetry_data: List of telemetry values.

        Returns:
            List[Telemetry]: List of telemetry objects.
        """
        telemetry_list = []
        for i in range(min(const.NB_OF_TELEMETRY_VALUES, len(telemetry_data))):
            telemetry = Telemetry(
                type=const.TELEMETRY_TYPE_AND_UNIT[i]["type"],
                value=telemetry_data[i],
                unit=const.TELEMETRY_TYPE_AND_UNIT[i]["unit"]
            )
            telemetry_list.append(telemetry)
        return telemetry_list

    async def send_telemetry(self, payload: List[Any]) -> bool:
        """Send telemetry data to ThingsBoard.

        Args:
            payload: The complete payload list containing telemetry values and metadata.
                The payload must include telemetry values followed by BFU device ID and timestamp:
                - payload[0:NB_OF_TELEMETRY_VALUES-1]: Telemetry values
                - payload[BFU_DEVICE_ID_INDEX]: BFU device ID
                - payload[CREATED_AT_INDEX]: Created timestamp

        Returns:
            bool: True if data was sent successfully, False otherwise.

        Raises:
            IndexError: If the payload doesn't contain all required elements.
            ConnectionError: If there's an issue with the network connection.
            ValueError: If the telemetry data format is invalid.
        """
        if not self._connected:
            logger.error("Not connected to ThingsBoard")
            return False

        try:
            # Extract metadata from payload as per original implementation
            if len(payload) <= const.CREATED_AT_INDEX:
                raise IndexError("Payload doesn't contain all required elements")

            created_at = payload[const.CREATED_AT_INDEX]
            bfu_device_id = payload[const.BFU_DEVICE_ID_INDEX]
            telemetry_data = payload[:const.NB_OF_TELEMETRY_VALUES]

            # Create telemetry objects using the constants
            telemetry = self._create_telemetry_objects(telemetry_data)

            # Create metadata
            metadata = Metadata(
                payload_version=settings.device.payload_version,
                assembled_by=settings.device.assembled_by,
                assembly_version=settings.device.assembly_version,
                manufactured_at=settings.device.manufactured_at,
                assemblies=self._create_assemblies(bfu_device_id)
            )

            # Create statistics using the helper methods from settings
            statistics = Statistics(
                boot_count=settings.statistics.get_boot_count(),
                boot_at=settings.statistics.get_boot_at(),
                time_since_boot=settings.statistics.get_time_since_boot(),
                warmup_time=settings.statistics.warmup_time
            )

            # Create payload - UUID is auto-generated in the model
            telemetry_payload = TelemetryPayload(
                device_type=settings.device.type,
                serial_number=settings.device.serial_number,
                manufacturer=settings.device.manufacturer,
                hardware_version=settings.device.hardware_version,
                created_at=created_at if isinstance(created_at, datetime) else datetime.now(),
                metadata=metadata,
                statistics=statistics,
                telemetry=telemetry
            )

            # Send payload
            result = await self._mqtt.send_telemetry(telemetry_payload.to_dict())
            return result is not None

        except Exception as e:
            logger.error(f"Failed to send telemetry: {str(e)}")
            return False

    async def send_predictions(self, predictions: Dict[datetime, float]) -> bool:
        """Send prediction data to ThingsBoard.

        Args:
            predictions: Dictionary mapping timestamps (datetime objects) to prediction
                values (floats between 0 and 1). Example: {datetime.now(): 0.95}.

        Returns:
            bool: True if data was sent successfully, False otherwise.

        Raises:
            ConnectionError: If there's an issue with the network connection.
            ValueError: If the prediction data format is invalid.
        """
        if not self._connected:
            logger.error("Not connected to ThingsBoard")
            return False

        try:
            # UUID is auto-generated in the model
            payload = PredictionPayload(predictions=predictions)
            result = await self._mqtt.send_telemetry(payload.to_dict())
            return result is not None
        except Exception as e:
            logger.error(f"Failed to send predictions: {str(e)}")
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Singleton instance
_thingsboard_client: Optional[ThingsBoardClient] = None


def get_thingsboard_client() -> ThingsBoardClient:
    """Get the singleton ThingsBoard client instance.

    Returns:
        ThingsBoardClient: The singleton ThingsBoard client instance.
    """
    global _thingsboard_client
    if _thingsboard_client is None:
        _thingsboard_client = ThingsBoardClient()
    return _thingsboard_client
