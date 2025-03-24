"""
Database models module for defining SQLAlchemy ORM models.

This module contains the SQLAlchemy ORM models for the database tables,
including models for analytes, predictions, and events.

Classes:
    Analyte: Model for storing analyte information
    Prediction: Model for storing prediction results
    Event: Model for storing event information
"""

import constants as const
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Analyte(Base):
    """Model for storing analyte information.
    
    Attributes:
        id: Primary key
        name: Unique name of the analyte
    """
    
    __tablename__ = const.ANALYTE_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)

    def __init__(self, name: str) -> None:
        """Initialize an Analyte instance.
        
        Args:
            name: Name of the analyte
        """
        self.name = name


class Prediction(Base):
    """Model for storing prediction results.
    
    Attributes:
        id: Primary key
        analyte_id: Foreign key to Analyte table
        log_id: ID of the log entry
        value: Predicted value
        date: Date of the prediction
        sent_mqtt_payload: Whether the prediction has been sent via MQTT
        analyte: Relationship to Analyte model
    """
    
    __tablename__ = const.PREDICTION_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    analyte_id = Column(Integer, ForeignKey(f'{const.ANALYTE_TABLE_NAME}.id'))
    log_id = Column(Integer)
    value = Column(Float)
    date = Column(DateTime)
    sent_mqtt_payload = Column(Boolean)

    analyte = relationship('Analyte')

    def __init__(
        self,
        log_id: int,
        analyte_id: int,
        value: float,
        date: DateTime,
        sent_mqtt_payload: bool = False
    ) -> None:
        """Initialize a Prediction instance.
        
        Args:
            log_id: ID of the log entry
            analyte_id: ID of the associated analyte
            value: Predicted value
            date: Date of the prediction
            sent_mqtt_payload: Whether the prediction has been sent via MQTT
        """
        self.log_id = log_id
        self.analyte_id = analyte_id
        self.value = value
        self.date = date
        self.sent_mqtt_payload = sent_mqtt_payload


class Event(Base):
    """Model for storing event information.
    
    Attributes:
        id: Primary key
        event_name: Unique name of the event
        last_state: Current state of the event
        date: Date of the event
        value: Value associated with the event
        temp: Temperature value
        humidity: Humidity value
    """
    
    __tablename__ = const.EVENT_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String, unique=True, nullable=False)
    last_state = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    value = Column(Float)
    temp = Column(Float)
    humidity = Column(Float)

    def __init__(
        self,
        event_name: str,
        state: str,
        date: DateTime,
        value: float = None,
        temp: float = None,
        humidity: float = None
    ) -> None:
        """Initialize an Event instance.
        
        Args:
            event_name: Name of the event
            state: Initial state of the event
            date: Date of the event
            value: Value associated with the event
            temp: Temperature value
            humidity: Humidity value
        """
        self.event_name = event_name
        self.last_state = state
        self.date = date
        self.value = value
        self.temp = temp
        self.humidity = humidity
