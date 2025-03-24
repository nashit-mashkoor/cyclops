#!/usr/bin/env python3
"""
Telemetry Database Interface Module

This module provides a singleton interface for interacting with the telemetry database.
It handles all database operations related to telemetry data, including:
- Storing and retrieving telemetry logs
- Managing telemetry types and values
- Handling MQTT payload status
- Database cleanup and maintenance

The module uses SQLAlchemy for database operations and implements proper session
management for efficient database access.
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import constants as const
from sqlalchemy import create_engine, event, text, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from .models import Base, Telemetry, TelemetryLog, TelemetryType


class Database:
    """Singleton class for managing telemetry database operations.
    
    This class provides a thread-safe interface for all telemetry database operations.
    It implements the singleton pattern to ensure only one database connection is
    maintained throughout the application lifecycle.
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        """Create a new instance of TelemetryDatabase if one doesn't exist.
        
        Returns:
            TelemetryDatabase: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the database connection and session factory.
        
        This method is called only once when the singleton is first created.
        It sets up the database engine and session factory for database operations.
        """
        if not self._initialized:
            # Create engine with connection pooling and WAL mode
            self._engine = create_engine(
                const.TELEMETRY_DATABASE_NAME,
                echo=False,
                poolclass=NullPool,
                connect_args={'timeout': 15}
            )
            # Enable Write-Ahead Logging for better performance
            event.listen(self._engine, 'connect', lambda c, _: c.execute('pragma journal_mode=WAL'))
            self._Session = sessionmaker(bind=self._engine)
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'Database':
        """Get the singleton instance of TelemetryDatabase.
        
        Returns:
            TelemetryDatabase: The singleton instance
        """
        return cls()

    def get_db_size(self) -> int:
        """Get the current size of the database in bytes.
        
        Returns:
            int: Size of the database in bytes
        """
        return os.path.getsize(const.TELEMETRY_DATABASE_NAME)

    def clean_telemetry_db(self) -> None:
        """Clean up the telemetry database by removing old data.
        
        This method removes telemetry logs that have been sent via MQTT and
        are older than the configured retention period. It also performs
        database optimization using VACUUM.
        """
        with self._Session() as session:
            try:
                # Delete old telemetry logs that have been sent
                log_ids = session.query(TelemetryLog.id).filter(
                    TelemetryLog.sent_mqtt_payload == True,
                    TelemetryLog.id > 30
                ).all()
                log_ids = set(map(lambda x: x.id, log_ids))
                
                # Delete related telemetry values in bulk
                session.query(Telemetry).filter(
                    Telemetry.telemetry_log_id.in_(log_ids)
                ).delete(synchronize_session=False)
                
                # Delete old logs in bulk
                session.query(TelemetryLog).filter(
                    TelemetryLog.sent_mqtt_payload == True,
                    TelemetryLog.id > 30
                ).delete()
                
                session.commit()
                
                # Optimize database
                session.execute(text("VACUUM"))
                session.commit()
            except Exception as e:
                session.rollback()
                raise e

    def populate_supported_telemetry_types(self) -> None:
        """Populate the telemetry types table with supported types.
        
        This method adds predefined telemetry types to the database if they
        don't already exist. It uses a set of supported types defined in
        constants.py.
        """
        with self._Session() as session:
            try:
                # Get existing types for efficient lookup
                existing_types = {t.value for t in session.query(TelemetryType).all()}
                
                # Add new types in bulk
                new_types = [
                    TelemetryType(value=telemetry_type, unit="")
                    for telemetry_type in const.SUPPORTED_TELEMETRY_TYPES
                    if telemetry_type not in existing_types
                ]
                
                if new_types:
                    session.bulk_save_objects(new_types)
                    session.commit()
            except Exception as e:
                session.rollback()
                raise e

    def get_supported_telemetry_types(self) -> List[str]:
        """Get a list of all supported telemetry types.
        
        Returns:
            List[str]: List of supported telemetry type names
        """
        with self._Session() as session:
            return [t.value for t in session.query(TelemetryType).all()]

    def get_unsent_mqtt_predictions(self, limit: int = 100) -> Dict[str, Any]:
        """Get telemetry logs that haven't been sent via MQTT.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            Dict[str, Any]: Dictionary containing prediction IDs and logs
        """
        # Keep the original query as requested
        query = f"""
                SELECT
                    TELEMETRY_LOG.id,
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR0' THEN TELEMETRY.value
                        END) 's0',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR1' THEN TELEMETRY.value
                        END) 's1',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR2' THEN TELEMETRY.value
                        END) 's2',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR3' THEN TELEMETRY.value
                        END) 's3',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR4' THEN TELEMETRY.value
                        END) 's4',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR5' THEN TELEMETRY.value
                        END) 's5',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR6' THEN TELEMETRY.value
                        END) 's6',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR7' THEN TELEMETRY.value
                        END) 's7',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR8' THEN TELEMETRY.value
                        END) 's8',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR9' THEN TELEMETRY.value
                        END) 's9',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR10' THEN TELEMETRY.value
                        END) 's10',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR11' THEN TELEMETRY.value
                        END) 's11',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR12' THEN TELEMETRY.value
                        END) 's12',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR13' THEN TELEMETRY.value
                        END) 's13',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR14' THEN TELEMETRY.value
                        END) 's14',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR15' THEN TELEMETRY.value
                        END) 's15',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR16' THEN TELEMETRY.value
                        END) 's16',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR17' THEN TELEMETRY.value
                        END) 's17',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR18' THEN TELEMETRY.value
                        END) 's18',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR19' THEN TELEMETRY.value
                        END) 's19',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR20' THEN TELEMETRY.value
                        END) 's20',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR21' THEN TELEMETRY.value
                        END) 's21',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR22' THEN TELEMETRY.value
                        END) 's22',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR23' THEN TELEMETRY.value
                        END) 's23',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR24' THEN TELEMETRY.value
                        END) 's24',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR25' THEN TELEMETRY.value
                        END) 's25',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR26' THEN TELEMETRY.value
                        END) 's26',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR27' THEN TELEMETRY.value
                        END) 's27',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR28' THEN TELEMETRY.value
                        END) 's28',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR29' THEN TELEMETRY.value
                        END) 's29',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR30' THEN TELEMETRY.value
                        END) 's30',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR31' THEN TELEMETRY.value
                        END) 's31'
                FROM TELEMETRY
                INNER JOIN TELEMETRY_LOG
                    ON TELEMETRY_LOG.id = TELEMETRY.telemetryLogId
                INNER JOIN TELEMETRY_TYPE
                    ON TELEMETRY.telemetryTypeId = TELEMETRY_TYPE.id
                LEFT JOIN PREDICTION
                    ON TELEMETRY_LOG.id = PREDICTION.logId
                GROUP BY TELEMETRY_LOG.id
                HAVING PREDICTION.logId IS NULL
                ORDER BY TELEMETRY_LOG.id
                LIMIT {limit};
        """
        
        with self._Session() as session:
            try:
                results = session.execute(text(query)).fetchall()
                
                prediction_logs = {}
                prediction_ids = []
                
                for result in results:
                    result_dict = result._asdict()
                    current_date = result_dict["id"]
                    prediction_ids.append(result_dict["id"])
                    current_log = prediction_logs.get(current_date, {})
                    for i in range(32):
                        current_log[f"s{i}"] = result_dict[f"s{i}"]
                    prediction_logs[current_date] = current_log
                    
                return {"ids": prediction_ids, "logs": prediction_logs}
            except Exception as e:
                session.rollback()
                raise e

    def update_sent_mqtt_predictions(self, prediction_id: int, mqtt_sent: bool) -> None:
        """Update the MQTT sent status of a telemetry log.
        
        Args:
            prediction_id: ID of the telemetry log to update
            mqtt_sent: New MQTT sent status
        """
        with self._Session() as session:
            try:
                query = update(TelemetryLog).where(
                    TelemetryLog.id == prediction_id
                ).values(sent_mqtt_payload=mqtt_sent)
                session.execute(query)
                session.commit()
            except Exception as e:
                session.rollback()
                raise e

    def get_telemetry_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get telemetry logs with optional limit.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List[Dict[str, Any]]: List of telemetry log entries
        """
        with self._Session() as session:
            try:
                query = session.query(TelemetryLog)
                if limit:
                    query = query.limit(limit)
                return [{
                    "id": log.id,
                    "created_at": log.created_at,
                    "bfu_device_id": log.bfu_device_id,
                    "sent_mqtt_payload": log.sent_mqtt_payload
                } for log in query.all()]
            except Exception as e:
                session.rollback()
                raise e

    def get_telemetry_values(self, log_id: int) -> List[Dict[str, Any]]:
        """Get all telemetry values for a specific log entry.
        
        Args:
            log_id: ID of the telemetry log entry
            
        Returns:
            List[Dict[str, Any]]: List of telemetry values with their types
        """
        with self._Session() as session:
            try:
                return [{
                    "id": t.id,
                    "type": t.telemetry_type.value,
                    "value": t.value
                } for t in session.query(Telemetry).filter_by(
                    telemetry_log_id=log_id
                ).all()]
            except Exception as e:
                session.rollback()
                raise e

    def write(self, payload: List[Any]) -> None:
        """Write telemetry data to the database.
        
        Args:
            payload: List containing telemetry values and metadata
        """
        if payload is None:
            return
            
        with self._Session() as session:
            try:
                # Add telemetry log
                log = TelemetryLog(
                    created_at=payload[const.CREATED_AT_INDEX-1],
                    bfu_device_id=payload[const.BFU_DEVICE_ID_INDEX-1],
                    sent_mqtt_payload=False
                )
                session.add(log)
                session.flush()  # Get the log ID
                
                # Add telemetry values in bulk
                telemetry_values = [
                    Telemetry(
                        telemetry_log_id=log.id,
                        telemetry_type_id=i+1,
                        value=float(payload[i])
                    )
                    for i in range(const.NB_OF_TELEMETRY_VALUES)
                ]
                session.bulk_save_objects(telemetry_values)
                session.commit()
            except Exception as e:
                session.rollback()
                raise e

    def update_log_sent_mqtt(self, log_id: int, mqtt_sent: bool) -> None:
        """Update the MQTT sent status of a telemetry log.
        
        This is an alias for update_sent_mqtt_predictions for backward compatibility.
        
        Args:
            log_id: ID of the telemetry log to update
            mqtt_sent: New MQTT sent status
        """
        self.update_sent_mqtt_predictions(log_id, mqtt_sent)

    def get_baseline(self, base_line_count: int) -> Optional[Any]:
        """Get baseline data for calibration.
        
        Args:
            base_line_count: Number of samples to include in baseline
            
        Returns:
            Optional[Any]: Baseline data or None if insufficient data
        """
        if self.get_nb_of_telemetry_log() < base_line_count:
            return None
            
        with self._Session() as session:
            try:
                telemetry_values = self.get_telemetry(session, base_line_count, 'ASC')
                return telemetry_values
            except Exception as e:
                session.rollback()
                raise e

    def get_last_log_and_sensor_Values(self) -> Tuple[Optional[int], Optional[Any]]:
        """Get the most recent log entry and sensor values.
        
        Returns:
            Tuple[Optional[int], Optional[Any]]: Tuple of (log_id, sensor_values)
        """
        with self._Session() as session:
            try:
                telemetry_values = self.get_telemetry(session, 1)
                if telemetry_values == []:
                    return None, None
                telemetry_log = telemetry_values[0][0]
                return telemetry_log, telemetry_values
            except Exception as e:
                session.rollback()
                raise e

    def get_latest_meta_data(self) -> Dict[str, float]:
        """Get the latest temperature and humidity data.
        
        Returns:
            Dict[str, float]: Dictionary containing temperature and humidity values
        """
        with self._Session() as session:
            try:
                meta_data = self._get_meta_data(session)
                if meta_data == []:
                    return {"temp": 0, "humidity": 0}
                return {"temp": meta_data[0][0], "humidity": meta_data[0][1]}
            except Exception as e:
                session.rollback()
                raise e

    def get_unsent_mqtt_logs(self) -> List[int]:
        """Get IDs of logs that haven't been sent via MQTT.
        
        Returns:
            List[int]: List of unsent log IDs
        """
        with self._Session() as session:
            try:
                return [s.id for s in session.query(TelemetryLog.id).filter(
                    TelemetryLog.sent_mqtt_payload == False
                )]
            except Exception as e:
                session.rollback()
                raise e

    def get_unsent_mqtt_log(self, log_id: int) -> List[Dict[str, Any]]:
        """Get telemetry data for a specific log entry.
        
        Args:
            log_id: ID of the log entry
            
        Returns:
            List[Dict[str, Any]]: List of telemetry values with their types
        """
        with self._Session() as session:
            try:
                return [{
                    "type": s[0],
                    "value": s[1],
                    "unit": s[2]
                } for s in session.query(
                    TelemetryType.value,
                    Telemetry.value,
                    TelemetryType.unit,
                    TelemetryLog.bfu_device_id,
                    TelemetryLog.created_at
                ).join(
                    TelemetryLog,
                    Telemetry.telemetry_log_id == TelemetryLog.id
                ).join(
                    TelemetryType,
                    Telemetry.telemetry_type_id == TelemetryType.id
                ).where(
                    Telemetry.telemetry_log_id == log_id
                )]
            except Exception as e:
                session.rollback()
                raise e

    def get_nb_of_telemetry_log(self) -> int:
        """Get the total number of telemetry logs.
        
        Returns:
            int: Number of telemetry logs
        """
        with self._Session() as session:
            try:
                return session.query(TelemetryLog).count()
            except Exception as e:
                session.rollback()
                raise e

    def _get_meta_data(self, session: Session, limit: int = 1, order: str = 'DESC') -> List[Tuple[float, float]]:
        """Get temperature and humidity metadata.
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of records to return
            order: Sort order ('ASC' or 'DESC')
            
        Returns:
            List[Tuple[float, float]]: List of (temperature, humidity) tuples
        """
        query = f"""
                SELECT
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'T0' THEN TELEMETRY.value
                        END) 'T0',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'H0' THEN TELEMETRY.value
                        END) 'H0'
                FROM TELEMETRY
                INNER JOIN TELEMETRY_LOG
                ON TELEMETRY_LOG.id = TELEMETRY.telemetryLogId
                INNER JOIN TELEMETRY_TYPE ON TELEMETRY.telemetryTypeId = TELEMETRY_TYPE.id
                GROUP BY TELEMETRY_LOG.id
                ORDER BY TELEMETRY_LOG.id {order}
                LIMIT {limit};
        """
        return session.execute(text(query)).fetchall()

    def get_telemetry(self, session: Session, limit: int, order: str = 'DESC') -> List[Tuple[Any, ...]]:
        """Get telemetry data with optional limit and order.
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of records to return
            order: Sort order ('ASC' or 'DESC')
            
        Returns:
            List[Tuple[Any, ...]]: List of telemetry records
        """
        query = f"""
                SELECT
                    TELEMETRY_LOG.id,
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR0' THEN TELEMETRY.value
                        END) 's0',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR1' THEN TELEMETRY.value
                        END) 's1',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR2' THEN TELEMETRY.value
                        END) 's2',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR3' THEN TELEMETRY.value
                        END) 's3',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR4' THEN TELEMETRY.value
                        END) 's4',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR5' THEN TELEMETRY.value
                        END) 's5',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR6' THEN TELEMETRY.value
                        END) 's6',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR7' THEN TELEMETRY.value
                        END) 's7',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR8' THEN TELEMETRY.value
                        END) 's8',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR9' THEN TELEMETRY.value
                        END) 's9',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR10' THEN TELEMETRY.value
                        END) 's10',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR11' THEN TELEMETRY.value
                        END) 's11',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR12' THEN TELEMETRY.value
                        END) 's12',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR13' THEN TELEMETRY.value
                        END) 's13',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR14' THEN TELEMETRY.value
                        END) 's14',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR15' THEN TELEMETRY.value
                        END) 's15',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR16' THEN TELEMETRY.value
                        END) 's16',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR17' THEN TELEMETRY.value
                        END) 's17',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR18' THEN TELEMETRY.value
                        END) 's18',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR19' THEN TELEMETRY.value
                        END) 's19',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR20' THEN TELEMETRY.value
                        END) 's20',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR21' THEN TELEMETRY.value
                        END) 's21',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR22' THEN TELEMETRY.value
                        END) 's22',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR23' THEN TELEMETRY.value
                        END) 's23',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR24' THEN TELEMETRY.value
                        END) 's24',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR25' THEN TELEMETRY.value
                        END) 's25',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR26' THEN TELEMETRY.value
                        END) 's26',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR27' THEN TELEMETRY.value
                        END) 's27',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR28' THEN TELEMETRY.value
                        END) 's28',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR29' THEN TELEMETRY.value
                        END) 's29',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR30' THEN TELEMETRY.value
                        END) 's30',
                    MIN(CASE
                            WHEN TELEMETRY_TYPE.value = 'CHR31' THEN TELEMETRY.value
                        END) 's31'
                FROM TELEMETRY
                INNER JOIN TELEMETRY_LOG
                ON TELEMETRY_LOG.id = TELEMETRY.telemetryLogId
                INNER JOIN TELEMETRY_TYPE ON TELEMETRY.telemetryTypeId = TELEMETRY_TYPE.id
                GROUP BY TELEMETRY_LOG.id
                ORDER BY TELEMETRY_LOG.id {order}
                LIMIT {limit};
        """
        return session.execute(text(query)).fetchall()
