"""
Machine Intelligence Module for Chemical Sensor Data Analysis

This module provides functionality for preprocessing and transforming chemical sensor data
before model inference. It handles data normalization, channel filtering, and prediction
post-processing.

The module is designed to work with chemical sensor arrays that produce tab-separated
values representing sensor readings. It supports multiple analytes with different
processing requirements and sensor channel configurations.

Data Format
----------
Input data is expected to be a tab-separated string with the following format:
    timestamp    sensor1    sensor2    ...    sensor32    temperature    humidity    metadata

The module processes the sensor readings (sensor1 through sensor32) and ignores
temperature, humidity, and metadata values.

Classes
-------
DataProcessor
    Handles all data transformations and preprocessing for chemical sensor data.
    This class manages the complete data processing pipeline from raw sensor
    readings to model-ready input data.
"""

import json
from typing import List, Dict, Optional, Union
import numpy as np
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ClippingBounds:
    """
    Configuration for prediction value clipping.
    
    This class defines the bounds and noise parameters for clipping model
    predictions to valid ranges.
    
    Attributes
    ----------
    lower_bound : float
        Minimum allowed prediction value
    upper_bound : Optional[float]
        Maximum allowed prediction value, if None no upper bound is applied
    noise_range : Optional[tuple[float, float]]
        Range for random noise to add to clipped values, if None no noise is added
    """
    lower_bound: float
    upper_bound: Optional[float]
    noise_range: Optional[tuple[float, float]]

@dataclass
class AnalyteConfig:
    """
    Configuration for a specific analyte.
    
    This class defines all parameters needed for processing a specific analyte,
    including sensor selection, scaling factors, and processing thresholds.
    
    Attributes
    ----------
    multiplier : float
        Scaling factor for model predictions
    clipping_bounds : ClippingBounds
        Configuration for prediction value clipping
    used_sensors : List[int]
        List of sensor channel indices used for this analyte
    internal_states : int
        Number of internal states in the LSTM model
    thresholds : List[float]
        Threshold values for state classification
    force_reset : bool
        Whether to force reset of model states
    """
    multiplier: float
    clipping_bounds: ClippingBounds
    used_sensors: List[int]
    internal_states: int
    thresholds: List[float]
    force_reset: bool

class DataProcessor:
    """
    Handles data preprocessing and transformation for chemical sensor data.
    
    This class manages all data transformations required for chemical sensor analysis,
    including data normalization, channel filtering, and prediction post-processing.
    
    The processor is configured through a JSON file that specifies supported analytes
    and their processing parameters. It handles the complete pipeline from raw sensor
    data to model-ready input.
    
    Attributes
    ----------
    config : Dict
        Configuration dictionary loaded from config.json
    supported_analytes : List[str]
        List of supported analyte names
    analyte_config : Dict[str, AnalyteConfig]
        Configuration for each supported analyte
    
    Methods
    -------
    process_payload(input_string: str) -> np.ndarray
        Process raw sensor data string into numpy array
    normalize_input(data: np.ndarray, baseline: np.ndarray, bias: float = -1) -> np.ndarray
        Normalize input data using baseline values
    process_prediction(prediction: np.ndarray, analyte: str) -> np.ndarray
        Process model predictions with analyte-specific scaling and clipping
    get_channels(analyte: str) -> List[int]
        Get list of sensor channels used for specific analyte
    filter_channels(data: np.ndarray, analyte: str) -> np.ndarray
        Filter input data to use only relevant sensor channels
    """
    
    def __init__(self, config_path: Union[str, Path] = "config.json") -> None:
        """
        Initialize the DataProcessor.
        
        Parameters
        ----------
        config_path : Union[str, Path], default="config.json"
            Path to the configuration file containing analyte specifications
            and processing parameters
            
        Raises
        ------
        FileNotFoundError
            If config file not found
        json.JSONDecodeError
            If config file is invalid JSON
        """
        self.config = self._load_config(config_path)
        self.supported_analytes = self.config['supported_analytes']
        self.analyte_config = self._parse_analyte_config(self.config['analyte_config'])

    @staticmethod
    def _load_config(config_path: Union[str, Path]) -> Dict:
        """
        Load configuration from JSON file.
        
        Parameters
        ----------
        config_path : Union[str, Path]
            Path to the configuration file
            
        Returns
        -------
        Dict
            Loaded configuration dictionary
            
        Raises
        ------
        FileNotFoundError
            If config file not found
        json.JSONDecodeError
            If config file is invalid JSON
        """
        with open(config_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def _parse_analyte_config(config: Dict) -> Dict[str, AnalyteConfig]:
        """
        Parse analyte configuration into structured format.
        
        Parameters
        ----------
        config : Dict
            Raw configuration dictionary from JSON
            
        Returns
        -------
        Dict[str, AnalyteConfig]
            Dictionary mapping analyte names to their configurations
            
        Raises
        ------
        KeyError
            If required configuration fields are missing
        ValueError
            If configuration values are invalid
        """
        return {
            name: AnalyteConfig(
                multiplier=cfg['analyte_multiplier'],
                clipping_bounds=ClippingBounds(
                    lower_bound=cfg['clipping_bounds']['lower_clip_bound'],
                    upper_bound=cfg['clipping_bounds']['higher_clip_bound'],
                    noise_range=cfg['clipping_bounds']['higher_clip_noise']
                ),
                used_sensors=cfg['used_sensors'],
                internal_states=cfg['internal_states'],
                thresholds=cfg['thresholds'],
                force_reset=cfg['force_reset']
            )
            for name, cfg in config.items()
        }

    @staticmethod
    def process_payload(input_string: str) -> np.ndarray:
        """
        Process raw sensor data string into numpy array.
        
        This method parses a tab-separated string of sensor readings into a numpy array.
        It expects the input string to have the format:
            timestamp    sensor1    sensor2    ...    sensor32    temperature    humidity    metadata
        
        Parameters
        ----------
        input_string : str
            Raw sensor data string with tab-separated values
            
        Returns
        -------
        np.ndarray
            Processed sensor data array with shape (1, 1, 32)
            
        Raises
        ------
        ValueError
            If input string is empty or invalid
        """
        if not input_string or not isinstance(input_string, str):
            raise ValueError("Invalid input string")
            
        # Split string and convert to float array, excluding temperature and humidity
        values = input_string.split('\t')[1:-4]
        return np.array([float(v) for v in values])

    @staticmethod
    def normalize_input(data: np.ndarray, baseline: np.ndarray, bias: float = -1) -> np.ndarray:
        """
        Normalize input data using baseline values.
        
        This method normalizes sensor data by dividing by the mean of baseline readings
        and adding a bias term. The normalization helps account for sensor drift and
        variations in baseline readings.
        
        Parameters
        ----------
        data : np.ndarray
            Input sensor data array with shape (1, 1, 32)
        baseline : np.ndarray
            Baseline values for normalization with shape (1, N, 32)
            where N is the number of baseline readings
        bias : float, default=-1
            Bias value to add after normalization
            
        Returns
        -------
        np.ndarray
            Normalized data array with shape (1, 1, 32)
            
        Raises
        ------
        ValueError
            If input arrays are invalid or have incompatible shapes
        """
        if data is None or baseline is None:
            raise ValueError("Input arrays cannot be None")
            
        if not isinstance(data, np.ndarray) or not isinstance(baseline, np.ndarray):
            raise ValueError("Inputs must be numpy arrays")
            
        baseline_mean = np.mean(baseline, axis=1).reshape(1, 1, data.shape[2])
        return data / baseline_mean + bias

    def process_prediction(self, prediction: np.ndarray, analyte: str) -> np.ndarray:
        """
        Process model predictions with analyte-specific scaling and clipping.
        
        This method applies analyte-specific processing to model predictions:
        1. Scales predictions using analyte-specific multiplier
        2. Clips values to configured bounds
        3. Adds random noise to clipped values if configured
        
        Parameters
        ----------
        prediction : np.ndarray
            Raw model prediction array
        analyte : str
            Name of the analyte
            
        Returns
        -------
        np.ndarray
            Processed prediction array
            
        Raises
        ------
        ValueError
            If analyte is not supported or prediction is invalid
        """
        if analyte not in self.analyte_config:
            raise ValueError(f"Unsupported analyte: {analyte}")
            
        if prediction is None:
            raise ValueError("Prediction cannot be None")
            
        config = self.analyte_config[analyte]
        
        # Apply analyte-specific multiplier
        scaled_pred = np.where(prediction > 0.0, 
                             prediction * config.multiplier,
                             prediction)
        
        # Apply clipping bounds
        bounds = config.clipping_bounds
        if bounds.lower_bound is not None:
            scaled_pred = np.maximum(scaled_pred, bounds.lower_bound)
            
        if bounds.upper_bound is not None:
            mask = scaled_pred >= bounds.upper_bound
            scaled_pred[mask] = bounds.upper_bound
            
            # Add noise to clipped values if configured
            if bounds.noise_range is not None:
                noise = np.random.uniform(*bounds.noise_range, size=scaled_pred.shape)
                scaled_pred[mask] += noise[mask]
                
        return scaled_pred

    def get_channels(self, analyte: str) -> List[int]:
        """
        Get list of sensor channels used for specific analyte.
        
        Parameters
        ----------
        analyte : str
            Name of the analyte
            
        Returns
        -------
        List[int]
            List of sensor channel indices (0-31) used for this analyte
            
        Raises
        ------
        ValueError
            If analyte is not supported
        """
        if analyte not in self.analyte_config:
            raise ValueError(f"Unsupported analyte: {analyte}")
        return self.analyte_config[analyte].used_sensors

    def filter_channels(self, data: np.ndarray, analyte: str) -> np.ndarray:
        """
        Filter input data to use only relevant sensor channels.
        
        This method selects only the sensor channels that are relevant for
        the specified analyte, reducing the input dimensionality for the model.
        
        Parameters
        ----------
        data : np.ndarray
            Input sensor data array with shape (1, 1, 32)
        analyte : str
            Name of the analyte
            
        Returns
        -------
        np.ndarray
            Filtered data array containing only relevant channels
            
        Raises
        ------
        ValueError
            If analyte is not supported or data is invalid
        """
        if analyte not in self.analyte_config:
            raise ValueError(f"Unsupported analyte: {analyte}")
            
        if data is None:
            raise ValueError("Input data cannot be None")
            
        channels = self.get_channels(analyte)
        return data[:, :, channels]
