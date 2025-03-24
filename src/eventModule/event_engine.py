import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Protocol, TypeVar

import utils
from dotenv import load_dotenv
from envs import env
from ..miDatabase.database import Database as MiDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Constants
TOBACCO_NICOTINE_THRESHOLD = 0.7
TOBACCO_NH3_LOW_THRESHOLD = 15
TOBACCO_NH3_MEDIUM_THRESHOLD = 40

class EventError(Exception):
    """
    Base exception for event-related errors.
    
    This exception serves as the base class for all event-related exceptions
    in the event engine module.
    """
    pass

class ConfigurationError(EventError):
    """
    Exception raised for configuration-related errors.
    
    This exception is raised when there are issues with the configuration
    data, such as invalid values or missing required fields.
    """
    pass

class EventType(Enum):
    """
    Types of events that can be detected by the event engine.
    
    This enumeration defines all possible types of events that the event engine
    can detect and process. Each event type corresponds to a specific category
    of environmental or chemical measurement.
    
    Attributes
    ----------
    ANALYTE : EventType
        Events related to chemical analyte concentrations
    TOBACCO : EventType
        Events related to tobacco smoke detection
    AQI : EventType
        Events related to Air Quality Index
    MOULD : EventType
        Events related to mould detection
    VIRUS : EventType
        Events related to virus detection
    """
    ANALYTE = auto()
    TOBACCO = auto()
    AQI = auto()
    MOULD = auto()
    VIRUS = auto()

class EventState(Enum):
    """
    Enumeration of possible event states.
    
    This enumeration defines the possible states that an event can be in,
    representing different levels of severity or concern.
    
    Attributes
    ----------
    NORMAL : str
        Indicates normal conditions
    WARNING : str
        Indicates slightly elevated levels requiring attention
    ALERT : str
        Indicates significantly elevated levels requiring immediate attention
    CRITICAL : str
        Indicates dangerously elevated levels requiring urgent action
    """
    NORMAL = "normal"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"

@dataclass
class EventData:
    """
    Data structure for event information.
    
    This class holds all the information related to a detected event,
    including its type, state, value, and associated metadata.
    
    Attributes
    ----------
    name : str
        The name of the event
    type : EventType
        The type of event (e.g., ANALYTE, TOBACCO)
    state : EventState
        The current state of the event
    value : float
        The measured value associated with the event
    timestamp : datetime
        When the event was detected
    metadata : Dict[str, float]
        Additional environmental data (temperature, humidity)
    priority : int
        Priority level of the event (default: 0)
    description : str
        Human-readable description of the event (default: "")
    """
    name: str
    type: EventType
    state: EventState
    value: float
    timestamp: datetime
    metadata: Dict[str, float]
    priority: int = field(default=0)
    description: str = field(default="")

@dataclass
class EventConfig:
    """
    Configuration for event detection.
    
    This class holds all configuration parameters needed for event detection,
    including supported states, timing parameters, and thresholds.
    
    Attributes
    ----------
    supported_states : List[str]
        List of possible event states
    event_delay : int
        Minimum delay between event detections in seconds
    thresholds : Dict[str, List[float]]
        Threshold values for different event types
    default_state : str
        Default state for new events (default: "green")
    """
    supported_states: List[str]
    event_delay: int
    thresholds: Dict[str, List[float]]
    default_state: str = field(default="green")
    
    def __post_init__(self):
        """
        Validate configuration after initialization.
        
        Raises
        ------
        ConfigurationError
            If any configuration parameters are invalid
        """
        if not self.supported_states:
            raise ConfigurationError("supported_states cannot be empty")
        if self.event_delay < 0:
            raise ConfigurationError("event_delay must be positive")
        if not self.thresholds:
            raise ConfigurationError("thresholds cannot be empty")
        if "green" not in self.supported_states:
            raise ConfigurationError("'green' must be in supported_states")
        if self.default_state not in self.supported_states:
            raise ConfigurationError(f"default_state {self.default_state} not in supported_states")

@dataclass
class AnalyteConfig:
    """
    Configuration for analyte detection.
    
    This class holds configuration parameters specific to analyte detection,
    including thresholds, units, and priority levels.
    
    Attributes
    ----------
    thresholds : List[float]
        Threshold values for different concentration levels
    name : str
        Name of the analyte
    unit : str
        Unit of measurement
    priority : int
        Priority level for this analyte (default: 0)
    """
    thresholds: List[float]
    name: str
    unit: str
    priority: int = field(default=0)
    
    def __post_init__(self):
        """
        Validate configuration after initialization.
        
        Raises
        ------
        ConfigurationError
            If any configuration parameters are invalid
        """
        if not self.thresholds:
            raise ConfigurationError(f"thresholds cannot be empty for analyte {self.name}")
        if not self.name:
            raise ConfigurationError("name cannot be empty")
        if not self.unit:
            raise ConfigurationError("unit cannot be empty")
        if self.priority < 0:
            raise ConfigurationError("priority must be non-negative")

class EventObserver(Protocol):
    """
    Protocol defining the interface for event observers.
    
    This protocol defines the interface that all event observers must implement
    to receive notifications about detected events.
    """
    def on_event_detected(self, event: EventData) -> None:
        """
        Handle event detection notification.
        
        Parameters
        ----------
        event : EventData
            The event data containing information about the detected event
        """
        ...

T = TypeVar('T', bound=EventObserver)

class EventEngine:
    """
    Event detection engine for monitoring changes in analyte predictions.
    
    This class implements the Observer pattern to detect and notify about significant
    changes in analyte concentrations and derived indices. It manages the detection,
    processing, and notification of various types of environmental events.
    
    The engine supports multiple types of events:
    - Analyte concentration changes
    - Tobacco smoke detection
    - Air Quality Index monitoring
    - Mould detection
    - Virus detection
    
    Attributes
    ----------
    _observers : List[EventObserver]
        List of observers to notify about events
    _supported_analytes : List[str]
        List of supported analyte names
    _event_config : EventConfig
        Configuration for event detection
    _analyte_config : Dict[str, AnalyteConfig]
        Configuration for each analyte
    _database : MiDatabase
        Database instance for storing and retrieving data
    _metadata : Dict[str, float]
        Current environmental metadata (temperature, humidity)
    _event_history : List[EventData]
        History of detected events
    """
    
    def __init__(self, database: MiDatabase, metadata: Dict[str, float]):
        """
        Initialize the EventEngine.
        
        Parameters
        ----------
        database : MiDatabase
            Database instance for storing and retrieving data
        metadata : Dict[str, float]
            Current environmental metadata (temperature, humidity)
            
        Raises
        ------
        ConfigurationError
            If initialization fails due to configuration issues
        """
        self._observers: List[EventObserver] = []
        self._event_history: List[EventData] = []
        self._metadata = metadata
        
        try:
            config = utils.load_config()
            self._supported_analytes = config['supported_analytes']
            self._event_config = EventConfig(**config['event_config'])
            self._analyte_config = {
                name: AnalyteConfig(**cfg) 
                for name, cfg in config['analyte_config'].items()
            }
            self._database = database
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize EventEngine: {str(e)}")

    def add_observer(self, observer: T) -> None:
        """
        Add an observer to be notified of events.
        
        Parameters
        ----------
        observer : EventObserver
            The observer to add
            
        Raises
        ------
        ValueError
            If observer is None
        """
        if observer is None:
            raise ValueError("Observer cannot be None")
        self._observers.append(observer)

    def remove_observer(self, observer: T) -> None:
        """
        Remove an observer from notifications.
        
        Parameters
        ----------
        observer : EventObserver
            The observer to remove
        """
        try:
            self._observers.remove(observer)
        except ValueError:
            logger.warning(f"Observer {observer} not found in observers list")

    def _notify_observers(self, event: EventData) -> None:
        """
        Notify all observers about an event.
        
        Parameters
        ----------
        event : EventData
            The event to notify observers about
        """
        for observer in self._observers:
            try:
                observer.on_event_detected(event)
            except Exception as e:
                logger.error(f"Error notifying observer: {str(e)}")

    def _get_state_name(self, state_id: int) -> str:
        """
        Get the state name for a given state ID.
        
        Parameters
        ----------
        state_id : int
            The ID of the state
            
        Returns
        -------
        str
            The name of the state
            
        Raises
        ------
        IndexError
            If state_id is out of range
        """
        states = self._event_config.supported_states
        if state_id < 0:
            return states[0]
        if state_id >= len(states):
            return states[-1]
        return states[state_id]

    def _get_state_id(self, state_name: str) -> int:
        """
        Get the state ID for a given state name.
        
        Parameters
        ----------
        state_name : str
            The name of the state
            
        Returns
        -------
        int
            The ID of the state
            
        Raises
        ------
        ValueError
            If state_name is not found
        """
        return self._event_config.supported_states.index(state_name)

    def _create_event(self, name: str, event_type: EventType, state: EventState,
                     value: float, timestamp: datetime) -> EventData:
        """
        Create an event data structure.
        
        Parameters
        ----------
        name : str
            Name of the event
        event_type : EventType
            Type of the event
        state : EventState
            State of the event
        value : float
            Value associated with the event
        timestamp : datetime
            Time when the event occurred
            
        Returns
        -------
        EventData
            The created event data structure
        """
        return EventData(
            name=name,
            type=event_type,
            state=state,
            value=value,
            timestamp=timestamp,
            metadata=self._metadata.copy(),
            priority=self._analyte_config.get(name, AnalyteConfig([], "", "")).priority
        )

    def _detect_analyte_event(self, detection_time: datetime) -> None:
        """
        Detect events based on analyte concentration changes.
        
        This method processes each supported analyte and detects if its concentration
        has changed significantly enough to trigger an event.
        
        Parameters
        ----------
        detection_time : datetime
            The time of detection
        """
        for event_name in self._database.get_event_names():
            if not self._database.is_analyte_event(event_name):
                continue

            try:
                analyte = self._database.get_associated_analyte(event_name)
                result = self._database.get_prediction_value(analyte_name=analyte)
                
                if result is None:
                    continue

                last_state_name = self._database.get_event_state(event_name=event_name)
                new_state_id = self._get_state_id(self._event_config.default_state)
                
                analyte_config = self._analyte_config[analyte]
                for threshold in analyte_config.thresholds:
                    if result >= threshold:
                        new_state_id += 1

                new_state_name = self._get_state_name(new_state_id)
                logger.info(f"Analyte {analyte}: {result} -> State: {new_state_name}")
                
                self._database.update_event(
                    event_name,
                    state=new_state_name,
                    value=result,
                    date=detection_time,
                    temp=self._metadata["temp"],
                    humidity=self._metadata["humidity"]
                )
                
                event = self._create_event(
                    event_name,
                    EventType.ANALYTE,
                    EventState(new_state_name),
                    result,
                    detection_time
                )
                self._event_history.append(event)
                self._notify_observers(event)
                
            except Exception as e:
                logger.error(f"Error detecting analyte event for {event_name}: {str(e)}")

    def _detect_tobacco_event(self, detection_time: datetime) -> None:
        """
        Detect tobacco-related events based on nicotine and NH3 levels.
        
        This method analyzes nicotine and NH3 concentrations to determine if
        tobacco smoke is present and at what level.
        
        Parameters
        ----------
        detection_time : datetime
            The time of detection
        """
        try:
            nicotine_result = self._database.get_prediction_value(analyte_name="nicotine")
            nh3_result = self._database.get_prediction_value(analyte_name="nh3")
            
            if nicotine_result is None or nh3_result is None:
                return

            tobacco_result = 0
            if nicotine_result >= TOBACCO_NICOTINE_THRESHOLD:
                if nh3_result <= TOBACCO_NH3_LOW_THRESHOLD:
                    tobacco_result = 1
                elif nh3_result < TOBACCO_NH3_MEDIUM_THRESHOLD:
                    tobacco_result = 2
                else:
                    tobacco_result = 3

            tobacco_state = self._get_state_name(tobacco_result)
            logger.info(f"Tobacco event: {tobacco_result} -> State: {tobacco_state}")
            
            self._database.update_event(
                "tobacco",
                state=tobacco_state,
                value=tobacco_result,
                date=detection_time,
                temp=self._metadata["temp"],
                humidity=self._metadata["humidity"]
            )
            
            event = self._create_event(
                "tobacco",
                EventType.TOBACCO,
                EventState(tobacco_state),
                tobacco_result,
                detection_time
            )
            self._event_history.append(event)
            self._notify_observers(event)
            
        except Exception as e:
            logger.error(f"Error detecting tobacco event: {str(e)}")

    def event_detection_required(self) -> bool:
        """
        Check if event detection should be performed.
        
        This method determines if enough time has passed since the last event
        detection to warrant a new detection cycle.
        
        Returns
        -------
        bool
            True if event detection is required, False otherwise
        """
        latest_event = self._database.get_latest_event()
        if latest_event is None:
            return True
            
        time_diff = (datetime.now() - latest_event[1]).seconds
        return time_diff > self._event_config.event_delay

    def get_event_history(self, event_type: Optional[EventType] = None,
                         limit: int = 100) -> List[EventData]:
        """
        Get the history of events, optionally filtered by type.
        
        Parameters
        ----------
        event_type : Optional[EventType]
            Type of events to filter by
        limit : int
            Maximum number of events to return
            
        Returns
        -------
        List[EventData]
            List of events, filtered by type if specified, sorted by timestamp
        """
        events = self._event_history
        if event_type is not None:
            events = [e for e in events if e.type == event_type]
        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]

    def run_event_engine(self) -> None:
        """
        Run the event detection engine.
        
        This method orchestrates the detection of various types of events:
        - Analyte concentration changes
        - Tobacco-related events
        - AQI events
        - Mould events
        - Virus events
        
        Raises
        ------
        EventError
            If event detection fails
        """
        if not self.event_detection_required():
            return

        try:
            detection_time = datetime.now()
            self._detect_analyte_event(detection_time)
            self._detect_tobacco_event(detection_time)
            self._detect_aqi_event()
            self._detect_mould_event()
            self._detect_virus_event()
        except Exception as e:
            logger.error(f"Error running event engine: {str(e)}")
            raise EventError(f"Failed to run event engine: {str(e)}")

    def _detect_aqi_event(self) -> None:
        """
        Detect Air Quality Index events.
        
        This method is a placeholder for AQI event detection.
        Implementation is pending.
        """
        # TODO: Implement AQI event detection
        pass

    def _detect_mould_event(self) -> None:
        """
        Detect mould-related events.
        
        This method is a placeholder for mould event detection.
        Implementation is pending.
        """
        # TODO: Implement mould event detection
        pass

    def _detect_virus_event(self) -> None:
        """
        Detect virus-related events.
        
        This method is a placeholder for virus event detection.
        Implementation is pending.
        """
        # TODO: Implement virus event detection
        pass
