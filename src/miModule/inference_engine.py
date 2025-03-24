"""
Machine Intelligence Module for Chemical Sensor Analysis

This module provides functionality for running inference on chemical sensor data
using TensorFlow Lite models. It handles model loading, data preprocessing, and
prediction generation for multiple analytes.

Classes
-------
InferenceEngine
    Manages model inference and prediction generation for chemical sensor data
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path

import numpy as np
import tensorflow as tf
from .config import load_config, ModelConfig
from dotenv import load_dotenv
from envs import env
from .data_engine import DataProcessor
from .tflite_model import TFLiteModel

load_dotenv()


class InferenceEngine:
    """
    Manages model inference and prediction generation for chemical sensor data.
    
    This class coordinates the process of running inference on chemical sensor data
    using TensorFlow Lite models. It handles model loading, data preprocessing,
    and prediction generation for multiple analytes.
    
    Attributes
    ----------
    models_dir : Path
        Directory containing the TensorFlow Lite model files
    supported_analytes : List[str]
        List of supported analyte names
    analyte_config : Dict
        Configuration for each supported analyte
    data_processor : DataProcessor
        Instance of DataProcessor for data preprocessing
    
    Methods
    -------
    run_inference(data: np.ndarray, baseline: np.ndarray) -> Dict[str, np.ndarray]
        Run inference on input data for all supported analytes
    """
    
    def __init__(self, models_dir: str, config_path: str = "config.json") -> None:
        """
        Initialize the InferenceEngine.
        
        Parameters
        ----------
        models_dir : str
            Path to directory containing TensorFlow Lite model files
        config_path : str, default="config.json"
            Path to configuration file
            
        Raises
        ------
        ValueError
            If models directory is invalid or configuration is missing
        """
        self.models_dir = Path(models_dir)
        if not self.models_dir.exists():
            raise ValueError(f"Models directory not found: {models_dir}")
            
        self.data_processor = DataProcessor(config_path)
        self.supported_analytes = self.data_processor.supported_analytes
        self.analyte_config = self.data_processor.analyte_config
        
        self._validate_models()

    def _validate_models(self) -> None:
        """
        Validate that all required model files exist.
        
        Raises
        ------
        ValueError
            If any required model file is missing
        """
        for analyte in self.supported_analytes:
            model_path = self.models_dir / analyte / "model.tflite"
            if not model_path.exists():
                raise ValueError(f"Model file not found for analyte {analyte}: {model_path}")

    def _get_model_config(self, analyte: str) -> Dict:
        """
        Get configuration for a specific analyte model.
        
        Parameters
        ----------
        analyte : str
            Name of the analyte
            
        Returns
        -------
        Dict
            Model configuration dictionary
            
        Raises
        ------
        ValueError
            If analyte is not supported
        """
        if analyte not in self.analyte_config:
            raise ValueError(f"Unsupported analyte: {analyte}")
        return self.analyte_config[analyte]

    def run_inference(self, data: np.ndarray, baseline: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Run inference on input data for all supported analytes.
        
        This method:
        1. Validates input data and baseline
        2. Normalizes input data using baseline values
        3. For each analyte:
           - Filters relevant sensor channels
           - Loads and runs the appropriate model
           - Processes and scales predictions
        4. Returns predictions for all analytes
        
        Parameters
        ----------
        data : np.ndarray
            Input sensor data array
        baseline : np.ndarray
            Baseline values for normalization
            
        Returns
        -------
        Dict[str, np.ndarray]
            Dictionary mapping analyte names to their predictions
            
        Raises
        ------
        ValueError
            If input data or baseline is invalid
        """
        if data is None or baseline is None:
            raise ValueError("Input data and baseline cannot be None")
            
        # Normalize input data
        normalized_data = self.data_processor.normalize_input(data, baseline)
        
        results = {}
        for analyte in self.supported_analytes:
            # Get model configuration
            config = self._get_model_config(analyte)
            
            # Filter relevant channels
            filtered_data = self.data_processor.filter_channels(normalized_data, analyte)
            
            # Create and run model
            model = TFLiteModel(
                name=analyte,
                model_dir=str(self.models_dir / analyte),
                num_states=config.internal_states,
                force_reset=config.force_reset
            )
            
            # Generate and process prediction
            prediction = model.predict(filtered_data)
            processed_pred = self.data_processor.process_prediction(prediction, analyte)
            
            results[analyte] = processed_pred
            
            # Clean up
            del model
            
        return results
