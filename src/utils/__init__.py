"""Utility module for common operations.

This module provides utility functions for configuration loading and logging setup.
"""

import json
import logging
import multiprocessing
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from envs import env

# Load environment variables
load_dotenv()


def load_config(key: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from the config file.
    
    Args:
        key (Optional[str]): Specific configuration key to load. If None,
            returns the entire configuration.
            
    Returns:
        Dict[str, Any]: The configuration dictionary or the value for the
            specified key.
    """
    config_file = env('CONFIG_FILE', var_type='string')
    with open(config_file, 'r') as reader:
        config = json.load(reader)
        if key:
            config = config[key]
    return config


def get_logger() -> logging.Logger:
    """Get a configured logger instance.
    
    This function sets up a logger with the following features:
    - Log level from configuration
    - File handler for logging to file
    - Formatted output with timestamp, level, and process name
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    config = load_config("app_config")
    logger = multiprocessing.get_logger()
    logger.setLevel(config["log_level"])
    
    formatter = logging.Formatter(
        '[%(asctime)s| %(levelname)s| %(processName)s] %(message)s'
    )
    
    handler = logging.FileHandler(env('LOG_OUTPUT_PATH', var_type='string'))
    handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(handler)
    return logger
