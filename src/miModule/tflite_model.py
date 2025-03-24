"""
Machine Intelligence Module for TensorFlow Lite Model Operations

This module provides functionality for loading and running inference with TensorFlow Lite models.
It handles model loading, state management, and prediction generation.

Classes
-------
TFLiteModel
    Wrapper for TensorFlow Lite model operations and state management
"""

import os
from dataclasses import dataclass
from typing import Tuple, Optional
from pathlib import Path

import numpy as np
import tensorflow as tf

@dataclass
class ModelState:
    """Represents the internal state of an LSTM layer."""
    hidden: np.ndarray
    cell: np.ndarray

class TFLiteModel:
    """
    Wrapper for TensorFlow Lite model operations and state management.
    
    This class provides a high-level interface for working with TensorFlow Lite models,
    handling model loading, state management, and prediction generation.
    
    Attributes
    ----------
    name : str
        Name of the analyte this model predicts
    model_dir : Path
        Directory containing the model files
    num_states : int
        Number of internal states in the LSTM layers
    weight_type : np.dtype
        Data type for model weights
    force_reset : bool
        Whether to force reset of model states
    interpreter : tf.lite.Interpreter
        TensorFlow Lite interpreter instance
    states : Tuple[ModelState, ModelState]
        Internal states of the LSTM layers
    
    Methods
    -------
    predict(data: np.ndarray) -> np.ndarray
        Generate predictions for input data
    analyze_model() -> None
        Analyze model structure and operations
    """
    
    def __init__(
        self,
        name: str,
        model_dir: str,
        num_states: int,
        weight_type: np.dtype = np.float32,
        force_reset: bool = False
    ) -> None:
        """
        Initialize the TFLiteModel.
        
        Parameters
        ----------
        name : str
            Name of the analyte this model predicts
        model_dir : str
            Directory containing the model files
        num_states : int
            Number of internal states in the LSTM layers
        weight_type : np.dtype, default=np.float32
            Data type for model weights
        force_reset : bool, default=False
            Whether to force reset of model states
            
        Raises
        ------
        ValueError
            If name or model_dir is None, or model file not found
        """
        if not name:
            raise ValueError("Model name cannot be None")
        if not model_dir:
            raise ValueError("Model directory cannot be None")
            
        self.name = name
        self.model_dir = Path(model_dir)
        self.num_states = num_states
        self.weight_type = weight_type
        self.force_reset = force_reset
        
        # Initialize model and states
        self.interpreter = self._load_model()
        self.states = self._initialize_states()
        
    def _load_model(self) -> tf.lite.Interpreter:
        """
        Load the TensorFlow Lite model.
        
        Returns
        -------
        tf.lite.Interpreter
            Loaded model interpreter
            
        Raises
        ------
        ValueError
            If model file not found
        """
        model_path = self.model_dir / "model.tflite"
        if not model_path.exists():
            raise ValueError(f"Model file not found: {model_path}")
        return tf.lite.Interpreter(str(model_path))
        
    def _initialize_states(self) -> Tuple[ModelState, ModelState]:
        """
        Initialize or load model states.
        
        Returns
        -------
        Tuple[ModelState, ModelState]
            Initialized model states
            
        Raises
        ------
        ValueError
            If state files are corrupted
        """
        if self.force_reset or not self._state_files_exist():
            return self._create_states()
            
        try:
            return self._load_states()
        except Exception as e:
            raise ValueError(f"Failed to load model states: {e}")
            
    def _create_states(self) -> Tuple[ModelState, ModelState]:
        """Create new model states."""
        shape = (1, self.num_states)
        dtype = self.weight_type
        
        state1 = ModelState(
            hidden=np.zeros(shape, dtype=dtype),
            cell=np.zeros(shape, dtype=dtype)
        )
        state2 = ModelState(
            hidden=np.zeros(shape, dtype=dtype),
            cell=np.zeros(shape, dtype=dtype)
        )
        
        self._save_states(state1, state2)
        return state1, state2
        
    def _load_states(self) -> Tuple[ModelState, ModelState]:
        """Load model states from files."""
        state1 = ModelState(
            hidden=np.load(self.model_dir / "h1.npy"),
            cell=np.load(self.model_dir / "c1.npy")
        )
        state2 = ModelState(
            hidden=np.load(self.model_dir / "h2.npy"),
            cell=np.load(self.model_dir / "c2.npy")
        )
        return state1, state2
        
    def _save_states(self, state1: ModelState, state2: ModelState) -> None:
        """Save model states to files."""
        np.save(self.model_dir / "h1.npy", state1.hidden)
        np.save(self.model_dir / "c1.npy", state1.cell)
        np.save(self.model_dir / "h2.npy", state2.hidden)
        np.save(self.model_dir / "c2.npy", state2.cell)
        
    def _state_files_exist(self) -> bool:
        """Check if state files exist."""
        files = ["h1.npy", "c1.npy", "h2.npy", "c2.npy"]
        return all((self.model_dir / f).exists() for f in files)
        
    def analyze_model(self) -> None:
        """
        Analyze model structure and operations.
        
        This method provides a detailed analysis of the model's structure,
        including input/output details and supported operations.
        """
        tf.lite.experimental.Analyzer.analyze(
            model_path=str(self.model_dir / "model.tflite")
        )
        
    def predict(self, data: np.ndarray) -> np.ndarray:
        """
        Generate predictions for input data.
        
        Parameters
        ----------
        data : np.ndarray
            Input data array
            
        Returns
        -------
        np.ndarray
            Model predictions
            
        Raises
        ------
        ValueError
            If input data dimensions are incorrect
        """
        # Prepare input data
        data = data.astype(self.weight_type)
        
        # Get model details
        input_details = self.interpreter.get_input_details()
        output_details = sorted(
            self.interpreter.get_output_details(),
            key=lambda x: x['index']
        )
        
        # Validate input dimensions
        self._validate_input_dimensions(data, input_details)
        
        # Allocate tensors and set inputs
        self.interpreter.allocate_tensors()
        self._set_input_tensors(data, input_details)
        
        # Run inference
        self.interpreter.invoke()
        
        # Get outputs and update states
        prediction = self.interpreter.get_tensor(output_details[4]['index'])
        self._update_states(output_details)
        
        # Save updated states
        self._save_states(*self.states)
        
        return prediction
        
    def _validate_input_dimensions(self, data: np.ndarray, input_details: list) -> None:
        """Validate input data dimensions."""
        expected_shapes = [
            data.shape,
            self.states[0].hidden.shape,
            self.states[0].cell.shape,
            self.states[1].hidden.shape,
            self.states[1].cell.shape
        ]
        
        actual_shapes = [tuple(detail['shape']) for detail in input_details]
        
        if not all(exp == act for exp, act in zip(expected_shapes, actual_shapes)):
            raise ValueError("Input data dimensions mismatch")
            
    def _set_input_tensors(self, data: np.ndarray, input_details: list) -> None:
        """Set input tensors for model inference."""
        self.interpreter.set_tensor(input_details[0]['index'], data)
        self.interpreter.set_tensor(input_details[1]['index'], self.states[0].hidden)
        self.interpreter.set_tensor(input_details[2]['index'], self.states[0].cell)
        self.interpreter.set_tensor(input_details[3]['index'], self.states[1].hidden)
        self.interpreter.set_tensor(input_details[4]['index'], self.states[1].cell)
        
    def _update_states(self, output_details: list) -> None:
        """Update model states from inference outputs."""
        self.states[0].hidden = self.interpreter.get_tensor(output_details[0]['index'])
        self.states[0].cell = self.interpreter.get_tensor(output_details[1]['index'])
        self.states[1].hidden = self.interpreter.get_tensor(output_details[2]['index'])
        self.states[1].cell = self.interpreter.get_tensor(output_details[3]['index'])

    def __str__(self) -> str:
        """
        Returns the name of the analyte the class makes the prediction
        """
        return f'{self.name} tflite model'
