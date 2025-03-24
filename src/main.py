#!/usr/bin/env python3
"""
Main module for the Cyclops Edge Application.

This module implements the core functionality of the Cyclops Edge Application,
managing multiple processes for sensor data collection, inference, telemetry,
"""

import multiprocessing
import time
import traceback
from datetime import datetime
from multiprocessing import Process as BaseProcess, Semaphore
from typing import List, Optional, Tuple, Any, Dict
from time import sleep

import psutil
from dotenv import load_dotenv

from .eventModule.event_engine import EventEngine
from .lcdModule.lcd import LCD
from .miDatabase.database import Database as MiDatabase
from .miModule.inference_engine import InferenceEngine
from .iotGateway.client import get_thingsboard_client
from .telemetryDatabase.database import Database as TelemetryDatabase
from .utils.ip_utility import IPUtility
from .sensorModule.sensor_interface import SensorInterface
import utils

# Load environment variables
load_dotenv()

# Global semaphore for telemetry database access
telemetry_db_semaphore = Semaphore(1)


class Process(BaseProcess):
    """
    Enhanced Process class with improved error handling and communication.
    
    This class extends the base multiprocessing.Process to provide better
    error handling and inter-process communication capabilities.
    
    Attributes:
        _parent_conn: Parent end of the inter-process communication pipe
        _child_conn: Child end of the inter-process communication pipe
        _exception: Stores any exception that occurs during process execution
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Process with communication pipes."""
        super().__init__(*args, **kwargs)
        self._parent_conn, self._child_conn = multiprocessing.Pipe()
        self._exception: Optional[Tuple[Exception, str]] = None

    def run(self) -> None:
        """
        Override the run method to handle exceptions and communicate them.
        
        Any exceptions during execution are captured and sent through the pipe
        to the parent process.
        """
        try:
            super().run()
            self._child_conn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._child_conn.send((e, tb))

    @property
    def exception(self) -> Optional[Tuple[Exception, str]]:
        """
        Get any exception that occurred during process execution.
        
        Returns:
            Optional[Tuple[Exception, str]]: Exception and traceback if an error occurred,
            None otherwise.
        """
        if self._parent_conn.poll():
            self._exception = self._parent_conn.recv()
        return self._exception


class ProcessManager:
    """
    Manages the lifecycle of all Cyclops processes.
    
    This class handles the creation, monitoring, and cleanup of all processes
    in the Cyclops application.
    
    Attributes:
        telemetry_database: Database instance for telemetry data
        mi_database: Database instance for machine intelligence data
        logger: Logger instance for application logging
        running_processes: List of currently running processes
    """
    
    def __init__(
        self,
        telemetry_database: TelemetryDatabase,
        mi_database: MiDatabase,
        logger: Any
    ) -> None:
        """Initialize the ProcessManager with required dependencies."""
        self.telemetry_database = telemetry_database
        self.mi_database = mi_database
        self.logger = logger
        self.running_processes: List[Process] = []
        self.config = utils.load_config('app_config')
        self.process_fail_count = 0

    def start_processes(self) -> None:
        """Start all required processes for the application."""
        process_functions = [
            self._run_sensor_process,
            self._run_ui_process,
            self._run_mi_detection_process,
            self._run_iot_process,
            self._run_db_cleanup_process
        ]
        
        for process_func in process_functions:
            process = Process(
                target=process_func,
                name=process_func.__name__,
                args=(self.telemetry_database, self.mi_database, self.logger)
            )
            self.running_processes.append(process)
            process.start()
        
        sleep(5)  # Allow processes to initialize
        self.logger.info(f"Current running processes: {self.running_processes}")

    def _run_sensor_process(
        self,
        telemetry_database: TelemetryDatabase,
        mi_database: MiDatabase,
        logger: Any
    ) -> None:
        """
        Process for collecting and storing sensor data.
        
        Continuously reads sensor data and stores it in the telemetry database.
        """
        logger.info('Initiating sensor process')
        sensor_interface = SensorInterface()
        
        while True:
            sleep(0.5)  # Prevent CPU overuse
            nb_of_samples = sensor_interface.getNbOfSamplesCollected()
            if nb_of_samples == 0:
                continue
                
            for _ in range(nb_of_samples):
                if telemetry_db_semaphore.acquire(block=False):
                    try:
                        telemetry_database.write(sensor_interface.getSample())
                    finally:
                        telemetry_db_semaphore.release()
                else:
                    break

    def _run_iot_process(
        self,
        telemetry_database: TelemetryDatabase,
        mi_database: MiDatabase,
        logger: Any
    ) -> None:
        """
        Process for handling IoT communication.
        
        Manages the sending of telemetry and prediction data to the IoT broker.
        """
        logger.info('Initiating IoT process')
        tb_mqtt = get_thingsboard_client()
        
        while True:
            sleep(0.5)  # Prevent CPU overuse
            if not tb_mqtt.connect():
                continue

            # Handle telemetry data
            mqtt_list = telemetry_database.get_unsent_mqtt_logs()
            for log_id in mqtt_list:
                payload = telemetry_database.get_unsent_mqtt_log(log_id)
                if tb_mqtt.sendTelemetryPayload(payload) is None:
                    break
                    
                if telemetry_db_semaphore.acquire(block=True):
                    try:
                        if tb_mqtt.connect():
                            telemetry_database.update_log_sent_mqtt(log_id, True)
                    finally:
                        telemetry_db_semaphore.release()

            # Handle prediction data
            predictions = mi_database.get_unsent_mqtt_predictions()
            if tb_mqtt.sendPredictionPayload(predictions["logs"]) is not None:
                for prediction_id in predictions["ids"]:
                    mi_database.update_sent_mqtt_predictions(prediction_id, True)

    def _run_mi_detection_process(
        self,
        telemetry_database: TelemetryDatabase,
        mi_database: MiDatabase,
        logger: Any
    ) -> None:
        """
        Process for running machine intelligence detection.
        
        Handles baseline establishment and continuous inference on sensor data.
        """
        logger.info('Initiating MI detection process')
        config = utils.load_config()
        mi_detection_count = 0

        # Wait for baseline establishment
        while True:
            baseline = telemetry_database.get_baseline(config['data_config']['baseline_count'])
            if baseline is not None:
                break
            logger.info('Establishing Baseline')

        while True:
            sleep(config['pred_config']['prediction_delay'])

            with telemetry_db_semaphore:
                last_log_id, last_sensor_value = telemetry_database.get_last_log_and_sensor_Values()
                meta_data = telemetry_database.get_latest_meta_data()

            if last_sensor_value is None:
                logger.info('Sensor telemetry Not logged')
                continue

            # Run inference
            inference_engine = InferenceEngine()
            results = inference_engine.run_inference(
                data=last_sensor_value,
                baseline=baseline
            )
            
            mi_database.save_prediction(last_log_id, results, datetime.now())
            mi_detection_count += 1

            # Run event engine if delay threshold reached
            if mi_detection_count >= config['event_config']['event_delay']:
                logger.info('Initiating event detection')
                event_engine = EventEngine(
                    data_base_instance=mi_database,
                    meta_data=meta_data
                )
                event_engine.run_event_engine()
                mi_detection_count = 0

    def _run_ui_process(
        self,
        telemetry_database: TelemetryDatabase,
        mi_database: MiDatabase,
        logger: Any
    ) -> None:
        """
        Process for handling user interface updates.
        
        Manages the LCD display and updates it with current system status.
        """
        logger.info('Initiating UI process')
        config = utils.load_config("ui_config")
        baseline_config = utils.load_config()
        lcd = LCD()
        
        # Initial display
        lcd.screen_message("CYCLOPS", f"IP:{IPUtility.get_ip()}")
        time.sleep(3)

        # Wait for baseline if needed
        if telemetry_database.get_baseline(baseline_config['data_config']['baseline_count']) is None:
            lcd.screen_message("  Establishing  ", "    Baseline    ")
            while True:
                if telemetry_database.get_baseline(baseline_config['data_config']['baseline_count']) is not None:
                    break
                time.sleep(1)

        # Main UI loop
        while True:
            event_details = mi_database.get_event_details()
            for event_detail in event_details:
                cpu = psutil.cpu_percent()
                lcd.update(
                    event_detail['event_name'],
                    event_detail['event_state'],
                    event_detail['value'],
                    event_detail['temp'],
                    event_detail['humidity'],
                    cpu
                )
                sleep(config["ui_delay"])

    def _run_db_cleanup_process(
        self,
        telemetry_database: TelemetryDatabase,
        mi_database: MiDatabase,
        logger: Any
    ) -> None:
        """
        Process for database maintenance.
        
        Handles periodic cleanup of databases to maintain size limits.
        """
        logger.info('Initiating DB cleanup process')
        config = utils.load_config('db_config')
        
        while True:
            sleep(config['db_cleanup_delay'])
            
            # Clean MI database if needed
            if mi_database.get_db_size() > config['db_size']:
                logger.info(f'Cleaning up MI database size: {mi_database.get_db_size()}')
                mi_database.clean_mi_db()
                logger.info(f'Reduced MI database size: {mi_database.get_db_size()}')

            # Clean telemetry database if needed
            if telemetry_database.get_db_size() > config['db_size']:
                if telemetry_db_semaphore.acquire(timeout=1):
                    try:
                        logger.info(f'Cleaning up telemetry database size: {telemetry_database.get_db_size()}')
                        telemetry_database.clean_telemetry_db()
                        logger.info(f"Reduced telemetry database size: {telemetry_database.get_db_size()}")
                    finally:
                        telemetry_db_semaphore.release()

    def monitor_processes(self) -> None:
        """
        Monitor running processes and handle failures.
        
        Continuously checks process health and restarts failed processes if needed.
        """
        while True:
            for process in self.running_processes:
                if process.exception:
                    error, traceback_info = process.exception
                    self.logger.error(f"Process failed: {process}")
                    self.logger.error(f"Traceback: {traceback_info}")

                    process.terminate()
                    self.process_fail_count += 1
                    
                    if self.process_fail_count > self.config["process_restart_count"]:
                        self.process_fail_count = 0
                        raise ChildProcessError("Application cannot restart automatically")
                        
                    self.logger.info(f"Restarting {process}")
                    self.cleanup_processes()
                    self.start_processes()
                    break

    def cleanup_processes(self) -> None:
        """Clean up all running processes."""
        telemetry_db_semaphore.release()
        for process in self.running_processes:
            process.kill()
        self.running_processes = []


def main() -> None:
    """
    Main entry point for the Cyclops Edge Application.
    
    Initializes the application, starts all processes, and handles shutdown.
    """
    try:
        config = utils.load_config('app_config')
        logger = utils.get_logger()
        telemetry_database = TelemetryDatabase.get_instance()
        mi_database = MiDatabase.get_instance()

        process_manager = ProcessManager(
            telemetry_database=telemetry_database,
            mi_database=mi_database,
            logger=logger
        )
        
        process_manager.start_processes()
        process_manager.monitor_processes()

    except KeyboardInterrupt:
        logger.info("Shutting down application...")
        logger.error(f"Traceback: {traceback.format_exc()}")
        process_manager.cleanup_processes()
    except ChildProcessError:
        logger.info("Application failed to recover...")
        logger.error(f"Traceback: {traceback.format_exc()}")
        process_manager.cleanup_processes()


if __name__ == "__main__":
    main()
