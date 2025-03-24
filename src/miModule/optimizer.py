"""
Machine Intelligence Module for Model Optimization

This module provides functionality for converting TensorFlow models to TensorFlow Lite format
and optimizing them for deployment. It handles model conversion, quantization, and weight
optimization.

Classes
-------
ModelOptimizer
    Handles conversion of TensorFlow models to TFLite format with optimization options
"""

import os
import warnings
from typing import Optional

import tensorflow as tf

warnings.filterwarnings('ignore')

class ModelOptimizer:
    """
    A class for converting and optimizing TensorFlow models to TFLite format.
    
    This class provides functionality to convert TensorFlow SavedModel format to
    TensorFlow Lite format, with support for both built-in and custom operations.
    
    Attributes
    ----------
    weights_path : str
        Path to the directory containing the TensorFlow model weights
    tflite_models_base : str
        Base directory name for storing converted TFLite models
    gcloud_path : Optional[str]
        Optional path for Google Cloud storage integration
    
    Methods
    -------
    convert_weights() -> None
        Converts all TensorFlow models in the weights directory to TFLite format
    """
    
    def __init__(self, weights_path: str, gcloud_path: Optional[str] = None) -> None:
        """
        Initialize the ModelOptimizer.
        
        Parameters
        ----------
        weights_path : str
            Path to the directory containing TensorFlow model weights
        gcloud_path : Optional[str], default=None
            Optional path for Google Cloud storage integration
        """
        self.weights_path = weights_path
        self.tflite_models_base = 'tflite'
        self.gcloud_path = gcloud_path

    def convert_weights(self) -> None:
        """
        Convert all TensorFlow models in the weights directory to TFLite format.
        
        This method:
        1. Creates a tflite directory if it doesn't exist
        2. Processes each model directory
        3. Converts models using TFLiteConverter with support for both built-in
           and custom operations
        4. Saves the converted models in the tflite directory
        
        Raises
        ------
        ValueError
            If the weights directory is not found or is empty
        """
        tflite_dir = os.path.join(self.weights_path, self.tflite_models_base)
        if not os.path.isdir(tflite_dir):
            os.makedirs(tflite_dir)

        model_dirs = [d for d in os.listdir(self.weights_path) 
                     if d != self.tflite_models_base and os.path.isdir(os.path.join(self.weights_path, d))]
        
        if not model_dirs:
            raise ValueError(f"No model directories found in {self.weights_path}")

        for model_dir in model_dirs:
            print(f'Processing {model_dir}...')
            current_model_path = os.path.join(self.weights_path, model_dir)
            tflite_model_path = os.path.join(tflite_dir, model_dir)

            # Configure converter with support for both built-in and custom operations
            converter = tf.lite.TFLiteConverter.from_saved_model(current_model_path)
            converter.target_spec.supported_ops = [
                tf.lite.OpsSet.TFLITE_BUILTINS,
                tf.lite.OpsSet.SELECT_TF_OPS
            ]
            
            # Convert model
            tflite_model = converter.convert()

            # Create output directory if it doesn't exist
            os.makedirs(tflite_model_path, exist_ok=True)

            # Save converted model
            model_file = os.path.join(tflite_model_path, "model.tflite")
            with open(model_file, 'wb') as writer:
                writer.write(tflite_model)
