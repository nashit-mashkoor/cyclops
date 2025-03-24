"""Payload models for ThingsBoard MQTT communication.

This module defines the data structures used for creating MQTT payloads
that will be sent to ThingsBoard. The models are implemented as dataclasses
for better type safety.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union


@dataclass
class Assembly:
    """Represents a device assembly component.
    
    This class describes a physical component of the device, such as
    the SBC (Single Board Computer), BFU, or LCD.
    
    Attributes:
        type: The type/name of the component (e.g., "SBC", "BFU", "LCD").
        manufacturer: The manufacturer of the component.
        serial_number: The serial number of the component (optional).
        hardware_version: The hardware version of the component (optional).
        firmware_version: The firmware version of the component (optional).
    """
    type: str
    manufacturer: str
    serial_number: Optional[str] = None
    hardware_version: Optional[str] = None
    firmware_version: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert the assembly to a dictionary format.
        
        Returns:
            Dict: Dictionary representation of the assembly for JSON serialization.
        """
        return {
            'type': self.type,
            'sn': self.serial_number,
            'manufacturer': self.manufacturer,
            'hv': self.hardware_version,
            'fv': self.firmware_version
        }


@dataclass
class Telemetry:
    """Represents a telemetry data point.
    
    Each telemetry point has a type, value and optional unit.
    
    Attributes:
        type: The type of telemetry (e.g., "RRF0", "CHR0", "T0").
        value: The value of the telemetry reading.
        unit: The unit of measurement (e.g., "OHM", "C").
    """
    type: str
    value: Union[int, float, str, bool]
    unit: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert the telemetry to a dictionary format.
        
        Returns:
            Dict: Dictionary representation of the telemetry for JSON serialization.
        """
        return {
            'type': self.type,
            'value': self.value,
            'unit': self.unit
        }


@dataclass
class Statistics:
    """Represents device statistics.
    
    Contains operational statistics about the device.
    
    Attributes:
        boot_count: Number of times the device has booted.
        boot_at: Timestamp of the last boot.
        time_since_boot: Time since boot in seconds.
        warmup_time: Warmup time in seconds.
        device_status: Current status of the device.
        debug: Flag indicating if the device is in debug mode.
    """
    boot_count: int
    boot_at: str
    time_since_boot: int
    warmup_time: int
    device_status: str = "ACTIVE"
    debug: bool = False

    def to_dict(self) -> Dict:
        """Convert the statistics to a dictionary format.
        
        Returns:
            Dict: Dictionary representation of the statistics for JSON serialization.
        """
        return {
            'bootCount': self.boot_count,
            'bootAt': self.boot_at,
            'timeSinceBoot': self.time_since_boot,
            'warmupTime': self.warmup_time,
            'deviceStatus': self.device_status,
            'debug': self.debug
        }


@dataclass
class Metadata:
    """Represents device metadata.
    
    Contains metadata about the device, including version information
    and assembly components.
    
    Attributes:
        payload_version: Version of the payload format.
        assembled_by: Entity that assembled the device.
        assembly_version: Version of the assembly.
        manufactured_at: Date of manufacture.
        assemblies: List of assembly components.
    """
    payload_version: str
    assembled_by: str
    assembly_version: str
    manufactured_at: str
    assemblies: List[Assembly] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert the metadata to a dictionary format.
        
        Returns:
            Dict: Dictionary representation of the metadata for JSON serialization.
        """
        return {
            'payloadVersion': self.payload_version,
            'assembledBy': self.assembled_by,
            'assemblyVersion': self.assembly_version,
            'manufacturedAt': self.manufactured_at,
            'assembly': [assembly.to_dict() for assembly in self.assemblies]
        }


@dataclass
class TelemetryPayload:
    """Main telemetry payload structure.
    
    This is the top-level container for telemetry data sent to ThingsBoard.
    
    Attributes:
        device_type: Type of the device.
        serial_number: Serial number of the device.
        manufacturer: Manufacturer of the device.
        hardware_version: Hardware version of the device.
        created_at: Timestamp when the payload was created.
        metadata: Metadata about the device.
        statistics: Statistical information about the device.
        telemetry: List of telemetry values.
        cid: Unique identifier for this payload (auto-generated).
    """
    device_type: str
    serial_number: str
    manufacturer: str
    hardware_version: str
    created_at: datetime
    metadata: Metadata
    statistics: Statistics
    telemetry: List[Telemetry] = field(default_factory=list)
    cid: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict:
        """Convert the payload to a dictionary format.
        
        Returns:
            Dict: Dictionary representation of the payload for JSON serialization.
        """
        return {
            'cid': self.cid,
            'deviceType': self.device_type,
            'serialNumber': self.serial_number,
            'manufacturer': self.manufacturer,
            'hv': self.hardware_version,
            'createdAt': self.created_at.isoformat(),
            'metadata': self.metadata.to_dict(),
            'statistics': self.statistics.to_dict(),
            'telemetry': [t.to_dict() for t in self.telemetry]
        }


@dataclass
class PredictionPayload:
    """Payload structure for prediction data.
    
    Used to send prediction results to ThingsBoard.
    
    Attributes:
        predictions: Dictionary mapping timestamps to prediction values.
        cid: Unique identifier for this payload (auto-generated).
    """
    predictions: Dict[datetime, float] = field(default_factory=dict)
    cid: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> List[Dict]:
        """Convert the predictions to a list of dictionaries.
        
        Returns:
            List[Dict]: List of dictionaries for JSON serialization.
        """
        return [
            {
                'cid': self.cid,
                'd': timestamp.strftime("%Y-%m-%dT%H:%M:%S%z"),
                'p': prediction
            }
            for timestamp, prediction in self.predictions.items()
        ]
