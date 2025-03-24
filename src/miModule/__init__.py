"""
Machine Intelligence Module for Chemical Sensor Data Analysis

Processes and analyzes chemical sensor data using TensorFlow Lite models.
Supports multiple analytes including formaldehyde (ch2o), nitrogen dioxide (no2),
and ammonia (nh3).

Features
--------
- Data preprocessing and normalization
- Multi-analyte inference support
- TensorFlow Lite model integration
- Configurable analyte-specific processing
- State management for LSTM models
- Model optimization and conversion

Classes
-------
DataProcessor
    Preprocesses sensor data: normalization, channel filtering, prediction processing

InferenceEngine
    Manages model inference: loading, execution, state persistence

TFLiteModel
    Handles TFLite model operations: loading, state management, predictions

ModelOptimizer
    Converts and optimizes TensorFlow models for TFLite deployment

Example
-------
    >>> from miModule import DataProcessor, InferenceEngine
    >>> 
    >>> # Initialize components
    >>> processor = DataProcessor("config.json")
    >>> engine = InferenceEngine("models_dir", "config.json")
    >>> 
    >>> # Process sensor data and run inference
    >>> raw_data = "10000\t1000000\t374046\t209461\t..."  # Sensor readings
    >>> sensor_data = processor.process_payload(raw_data)
    >>> baseline = np.array(...)  # Baseline sensor readings
    >>> results = engine.run_inference(sensor_data, baseline)
    >>> 
    >>> # Access predictions
    >>> for analyte, prediction in results.items():
    ...     print(f"{analyte}: {prediction}")

Configuration
------------
Requires config.json with:
- Supported analytes
- Analyte-specific configurations
- Sensor channel mappings
- Processing parameters
"""

from .data_engine import DataProcessor
from .inference_engine import InferenceEngine
from .tflite_model import TFLiteModel
from .optimizer import ModelOptimizer

__version__ = '1.0.0'
__all__ = ['DataProcessor', 'InferenceEngine', 'TFLiteModel', 'ModelOptimizer'] 