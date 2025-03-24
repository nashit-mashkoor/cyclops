"""
Telemetry Database Models Module

This module defines the SQLAlchemy ORM models for the telemetry database.
The database consists of three main tables:
- TelemetryLog: Stores telemetry log entries with device information
- Telemetry: Stores individual telemetry values with their types
- TelemetryType: Defines the types of telemetry data that can be stored

The module uses SQLAlchemy's declarative base for table management and
includes proper relationships between tables for efficient querying.
"""

import constants as const
from sqlalchemy import Boolean, Column, create_engine, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from typing import Optional

# Create database engine and declarative base
engine = create_engine(const.TELEMETRY_DATABASE_NAME, echo=False)
Base = declarative_base()


class TelemetryLog(Base):
    """Model for storing telemetry log entries.
    
    Attributes:
        id (int): Primary key, auto-incrementing
        created_at (str): Timestamp of when the log was created
        bfu_device_id (str): ID of the BFU device that generated the telemetry
        sent_mqtt_payload (bool): Whether the telemetry has been sent via MQTT
    """
    __tablename__ = const.TELEMETRY_LOG_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String)
    bfu_device_id = Column(String)
    sent_mqtt_payload = Column(Boolean)

    def __init__(self, created_at: str, bfu_device_id: str, sent_mqtt_payload: bool) -> None:
        """Initialize a new telemetry log entry.
        
        Args:
            created_at: Timestamp of when the log was created
            bfu_device_id: ID of the BFU device
            sent_mqtt_payload: Whether the telemetry has been sent via MQTT
        """
        self.created_at = created_at
        self.bfu_device_id = bfu_device_id
        self.sent_mqtt_payload = sent_mqtt_payload


class Telemetry(Base):
    """Model for storing individual telemetry values.
    
    Attributes:
        id (int): Primary key, auto-incrementing
        telemetry_log_id (int): Foreign key to TelemetryLog table
        telemetry_type_id (int): Foreign key to TelemetryType table
        value (float): The actual telemetry value
        telemetry_log (TelemetryLog): Relationship to parent log entry
        telemetry_type (TelemetryType): Relationship to telemetry type definition
    """
    __tablename__ = const.TELEMETRY_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    telemetry_log_id = Column(Integer, ForeignKey(
        f'{const.TELEMETRY_LOG_TABLE_NAME}.id'), index=True)
    telemetry_type_id = Column(Integer, ForeignKey(
        f'{const.TELEMETRY_TYPE_TABLE_NAME}.id'))
    value = Column(Float, index=True)

    telemetry_log = relationship('TelemetryLog')
    telemetry_type = relationship('TelemetryType')

    def __init__(self, log_id: int, type_id: int, value: float) -> None:
        """Initialize a new telemetry value.
        
        Args:
            log_id: ID of the parent telemetry log entry
            type_id: ID of the telemetry type
            value: The actual telemetry value
        """
        self.telemetry_log_id = log_id
        self.telemetry_type_id = type_id
        self.value = value


class TelemetryType(Base):
    """Model for defining types of telemetry data.
    
    Attributes:
        id (int): Primary key, auto-incrementing
        value (str): Name/identifier of the telemetry type
        unit (str): Unit of measurement for this telemetry type
    """
    __tablename__ = const.TELEMETRY_TYPE_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String, index=True)
    unit = Column(String)

    def __init__(self, value: str, unit: str) -> None:
        """Initialize a new telemetry type.
        
        Args:
            value: Name/identifier of the telemetry type
            unit: Unit of measurement for this telemetry type
        """
        self.value = value
        self.unit = unit


# Create all tables in the database
Base.metadata.create_all(engine)
