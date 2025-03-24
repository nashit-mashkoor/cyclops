"""
Database interface module for managing analyte predictions and events.

This module provides a singleton database interface using SQLAlchemy for managing
analyte predictions, events, and their associated data. It implements the
Singleton pattern to ensure a single database connection is maintained throughout
the application lifecycle.

Classes:
    Database: Main database interface class implementing the Singleton pattern.
"""

import datetime as dt
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any, Union

import constants as const
import numpy as np
import sqlalchemy
import utils
from dotenv import load_dotenv
from envs import env
from ..miDatabase.models import Analyte, Event, Prediction
from sqlalchemy import create_engine, text, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()


class Database:
    """Singleton database interface for managing analyte predictions and events.
    
    This class implements the Singleton pattern to ensure a single database
    connection is maintained throughout the application lifecycle. It provides
    methods for managing analyte predictions, events, and their associated data.
    
    Attributes:
        _engine: SQLAlchemy engine instance for database connections
        _Base: SQLAlchemy declarative base for table management
        _Session: SQLAlchemy session factory
        __instance: Singleton instance of the Database class
    """
    
    _engine = create_engine(
        const.MI_DATABASE_NAME,
        echo=False,
        poolclass=NullPool,
        connect_args={'timeout': 15}
    )
    _Base = declarative_base()
    _Session = sessionmaker(bind=_engine)
    __instance = None
    
    # Enable Write-Ahead Logging for better performance
    sqlalchemy.event.listen(_engine, 'connect', lambda c, _: c.execute('pragma journal_mode=WAL'))

    @classmethod
    def get_instance(cls) -> 'Database':
        """Get the singleton instance of the Database class.
        
        Returns:
            Database: The singleton instance of the Database class.
        """
        if cls.__instance is None:
            cls()
        return cls.__instance

    def __init__(self) -> None:
        """Initialize the Database singleton instance.
        
        Raises:
            Exception: If attempting to create multiple instances.
        """
        if Database.__instance is not None:
            raise Exception("This class is a singleton!")
        
        Database.__instance = self
        self._config = utils.load_config()
        self.populate_supported_analytes()
        self.populate_events()

    def get_db_size(self) -> int:
        """Get the size of the database file in bytes.
        
        Returns:
            int: Size of the database file in bytes.
        """
        return os.path.getsize(const.MI_DATABASE_PATH)

    def clean_mi_db(self) -> None:
        """Clean the database by removing sent MQTT predictions and optimizing the database.
        
        This method removes all predictions that have been sent via MQTT and
        performs database optimization using VACUUM.
        """
        with self._Session() as session:
            session.query(Prediction).filter(Prediction.sent_mqtt_payload == True).delete()
            session.commit()
            self._restructure_db(session)

    def _get_prediction_times(self, session: Session, limit: Optional[int] = None) -> Optional[List[datetime]]:
        """Get prediction timestamps ordered by date.
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of timestamps to return
            
        Returns:
            Optional[List[datetime]]: List of prediction timestamps or None if no predictions exist
        """
        result = session.query(Prediction.date).order_by(
            Prediction.date.desc()).limit(limit).all()
        return result if result else None

    def _get_event_count(self, session: Session) -> int:
        """Get the total count of events in the database.
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            int: Total number of events
        """
        return session.query(Event).count()

    def _get_events(self, session: Session, limit: Optional[int] = None) -> List[Event]:
        """Get events ordered by date.
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: List of event objects
        """
        return session.query(Event).order_by(
            Event.date.desc()).limit(limit).all()

    def get_event_state(self, event_name: str) -> Optional[str]:
        """Get the current state of an event.
        
        Args:
            event_name: Name of the event
            
        Returns:
            Optional[str]: Current state of the event or None if event not found
        """
        with self._Session() as session:
            events = session.query(Event).where(
                Event.event_name == event_name).all()
        return events[0].last_state if events else None

    def get_event_details(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get detailed information about events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing event details
        """
        with self._Session() as session:
            events = session.query(Event).order_by(
                Event.date.desc()).limit(limit).all()
        return [{
            "event_name": x.event_name,
            "event_state": x.last_state,
            "value": x.value,
            "temp": x.temp,
            "humidity": x.humidity
        } for x in events]

    def _update_event_attributes(
        self,
        session: Session,
        event_name: str,
        state: Optional[str] = None,
        value: Optional[float] = None,
        date: Optional[datetime] = None,
        temp: Optional[float] = None,
        humidity: Optional[float] = None
    ) -> None:
        """Update attributes of an event.
        
        Args:
            session: SQLAlchemy session
            event_name: Name of the event to update
            state: New state of the event
            value: New value for the event
            date: New date for the event
            temp: New temperature value
            humidity: New humidity value
        """
        kwargs = {}
        if state:
            kwargs['last_state'] = state
        if date:
            kwargs['date'] = date
        if value is not None and value > -1:
            kwargs['value'] = value
        if temp is not None and temp > -1:
            kwargs['temp'] = temp
        if humidity is not None and humidity > -1:
            kwargs['humidity'] = humidity
            
        query = update(Event).where(
            Event.event_name == event_name).values(**kwargs)
        session.execute(query)

    def _add_event(
        self,
        session: Session,
        event_name: str,
        state: str,
        date: datetime,
        value: Optional[float] = None,
        temp: Optional[float] = None,
        humidity: Optional[float] = None
    ) -> None:
        """Add a new event to the database.
        
        Args:
            session: SQLAlchemy session
            event_name: Name of the event
            state: Initial state of the event
            date: Date of the event
            value: Value associated with the event
            temp: Temperature value
            humidity: Humidity value
        """
        session.add(Event(
            event_name=event_name,
            last_state=state,
            date=date,
            value=value,
            temp=temp,
            humidity=humidity
        ))

    def populate_supported_analytes(self) -> bool:
        """Populate the database with supported analytes.
        
        Returns:
            bool: True if analytes were populated, False otherwise
        """
        supported_analytes = self._config['supported_analytes']
        with self._Session() as session:
            try:
                if session.query(Analyte).count() != 0:
                    return False
                self._add_analytes(session, supported_analytes)
                session.commit()
                return True
            except Exception:
                return False

    def get_supported_analytes(self) -> List[Analyte]:
        """Get all supported analytes from the database.
        
        Returns:
            List[Analyte]: List of analyte objects
        """
        with self._Session() as session:
            return session.query(Analyte).all()

    def save_prediction(self, last_log_id: int, results: Dict[str, float], date: datetime) -> bool:
        """Save prediction results to the database.
        
        Args:
            last_log_id: ID of the last log entry
            results: Dictionary mapping analyte names to their predicted values
            date: Date of the prediction
            
        Returns:
            bool: True if predictions were saved successfully, False otherwise
        """
        with self._Session() as session:
            try:
                if not results:
                    return False
                    
                for analyte_name, result in results.items():
                    analyte_id = self._get_analyte_id(session, analyte_name)
                    if analyte_id is not None:
                        self._add_prediction(session, last_log_id, analyte_id, result, date)
                session.commit()
                return True
            except Exception as e:
                print(f"Error saving prediction: {e}")
                session.rollback()
                return False

    def get_prediction_value(self, analyte_name: str) -> Optional[float]:
        """Get the most recent prediction value for an analyte.
        
        Args:
            analyte_name: Name of the analyte
            
        Returns:
            Optional[float]: Most recent prediction value or None if no predictions exist
        """
        with self._Session() as session:
            predictions = self._get_predictions(session, analyte_name=analyte_name, limit=1)
        return predictions[0].value if predictions else None

    def get_last_prediction_time(self) -> Optional[datetime]:
        """Get the timestamp of the most recent prediction.
        
        Returns:
            Optional[datetime]: Timestamp of the most recent prediction or None if no predictions exist
        """
        with self._Session() as session:
            prediction_time = self._get_prediction_times(session, 1)
            return prediction_time[0].date if prediction_time else None

    def populate_events(self) -> bool:
        """Populate the database with supported event types.
        
        Returns:
            bool: True if events were populated successfully, False otherwise
        """
        supported_event_types = self._config['event_config']['supported_event_types']
        try:
            with self._Session() as session:
                if self._get_event_count(session) != 0:
                    return False
                    
                for event_type in supported_event_types:
                    if event_type == 'analyte_based':
                        self._populate_analyte_events(session)
                    elif event_type == 'tobacco':
                        self._populate_tobacco_event(session)
                session.commit()
            return True
        except Exception:
            return False

    def _populate_analyte_events(self, session: Session) -> None:
        """Populate events for supported analytes.
        
        Args:
            session: SQLAlchemy session
        """
        supported_analytes = self._config['supported_analytes']
        default_state = self._config['event_config']['default_state']
        current_datetime = dt.datetime.now()
        
        for analyte_name in supported_analytes:
            self._add_event(
                session,
                analyte_name,
                default_state,
                current_datetime,
                0.0,
                0.0,
                0.0
            )

    def _populate_tobacco_event(self, session: Session) -> None:
        """Populate the tobacco event.
        
        Args:
            session: SQLAlchemy session
        """
        current_datetime = dt.datetime.now()
        default_state = self._config['event_config']['default_state']
        self._add_event(
            session,
            'tobacco',
            default_state,
            current_datetime,
            0.0,
            0.0,
            0.0
        )

    def is_analyte_event(self, event_name: str) -> bool:
        """Check if an event is analyte-based.
        
        Args:
            event_name: Name of the event to check
            
        Returns:
            bool: True if the event is analyte-based, False otherwise
        """
        return event_name in self._config['supported_analytes']

    def get_associated_analyte(self, event_name: str) -> str:
        """Get the analyte associated with an event.
        
        For analyte-based events, the event name is the same as the associated analyte.
        
        Args:
            event_name: Name of the event
            
        Returns:
            str: Name of the associated analyte
        """
        return event_name

    def is_supported_state(self, state: Optional[str]) -> bool:
        """Check if a state is supported by the system.
        
        Args:
            state: State to check
            
        Returns:
            bool: True if the state is supported, False otherwise
        """
        supported_state = self._config['event_config']['supported_states']
        return state in supported_state

    def get_latest_event(self) -> Optional[Tuple[str, datetime]]:
        """Get the most recent event.
        
        Returns:
            Optional[Tuple[str, datetime]]: Tuple of (event_name, date) or None if no events exist
        """
        with self._Session() as session:
            latest_event = self._get_events(session, 1)
            if not latest_event:
                return None
            return latest_event[0].event_name, latest_event[0].date

    def get_event_names(self) -> List[str]:
        """Get all event names from the database.
        
        Returns:
            List[str]: List of event names
        """
        with self._Session() as session:
            events = self._get_events(session)
            return [event.event_name for event in events]

    def update_event(
        self,
        event_name: str,
        state: Optional[str] = None,
        value: Optional[float] = None,
        date: Optional[datetime] = None,
        temp: Optional[float] = None,
        humidity: Optional[float] = None
    ) -> bool:
        """Update an event's attributes.
        
        Args:
            event_name: Name of the event to update
            state: New state of the event
            value: New value for the event
            date: New date for the event
            temp: New temperature value
            humidity: New humidity value
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        with self._Session() as session:
            try:
                if self.is_supported_state(state=state):
                    self._update_event_attributes(
                        session,
                        event_name,
                        state,
                        value,
                        date,
                        temp,
                        humidity
                    )
                    session.commit()
                    return True
            except Exception as e:
                session.rollback()
                return False

    def _get_analyte_id(self, session: Session, name: str) -> Optional[int]:
        """Get the ID of an analyte by name.
        
        Args:
            session: SQLAlchemy session
            name: Name of the analyte
            
        Returns:
            Optional[int]: ID of the analyte or None if not found
        """
        analyte_obj = session.query(Analyte).filter(Analyte.name == name).first()
        return analyte_obj.id if analyte_obj else None

    def _add_analytes(self, session: Session, analytes: List[str]) -> None:
        """Add multiple analytes to the database.
        
        Args:
            session: SQLAlchemy session
            analytes: List of analyte names to add
        """
        objects = [Analyte(name=analyte_name) for analyte_name in analytes]
        session.add_all(objects)

    def _add_prediction(
        self,
        session: Session,
        last_log_id: int,
        analyte_id: int,
        value: float,
        date: datetime
    ) -> None:
        """Add a prediction to the database.
        
        Args:
            session: SQLAlchemy session
            last_log_id: ID of the last log entry
            analyte_id: ID of the analyte
            value: Predicted value
            date: Date of the prediction
        """
        session.add(Prediction(
            log_id=last_log_id,
            analyte_id=analyte_id,
            value=value,
            date=date,
            sent_mqtt_payload=False
        ))

    def _get_predictions(
        self,
        session: Session,
        analyte_name: str,
        limit: Optional[int] = None
    ) -> List[Prediction]:
        """Get predictions for an analyte.
        
        Args:
            session: SQLAlchemy session
            analyte_name: Name of the analyte
            limit: Maximum number of predictions to return
            
        Returns:
            List[Prediction]: List of prediction objects
        """
        query = session.query(Prediction.value)\
            .join(Prediction.analyte)\
            .order_by(Prediction.date.desc())\
            .where(Analyte.name == analyte_name)\
            .limit(limit)
        return query.all()

    def get_unsent_mqtt_predictions(self) -> Dict[str, Any]:
        """Get predictions that haven't been sent via MQTT.
        
        Returns:
            Dict[str, Any]: Dictionary containing prediction IDs and logs
        """
        with self._Session() as session:
            results = session.query(
                Prediction.id,
                Analyte.name,
                Prediction.value,
                Prediction.date
            ).join(
                Analyte,
                Prediction.analyte_id == Analyte.id
            ).filter(
                Prediction.sent_mqtt_payload == False
            ).all()
            
        prediction_logs = {}
        prediction_ids = []
        
        for result in results:
            result_dict = result._asdict()
            current_date = result_dict["date"]
            prediction_ids.append(result_dict["id"])
            current_log = prediction_logs.get(current_date, {})
            current_log[result_dict["name"]] = result_dict["value"]
            prediction_logs[current_date] = current_log
            
        return {"ids": prediction_ids, "logs": prediction_logs}

    def update_sent_mqtt_predictions(self, prediction_id: int, mqtt_sent: bool) -> None:
        """Update the MQTT sent status of a prediction.
        
        Args:
            prediction_id: ID of the prediction to update
            mqtt_sent: New MQTT sent status
        """
        with self._Session() as session:
            query = update(Prediction).where(
                Prediction.id == prediction_id
            ).values(sent_mqtt_payload=mqtt_sent)
            session.execute(query)
            session.commit()

    def _restructure_db(self, session: Session) -> None:
        """Optimize the database using VACUUM.
        
        Args:
            session: SQLAlchemy session
        """
        with session.connection() as conn:
            conn.execute(text("VACUUM;"))
