"""
Configuration Loading Utilities for Alya Bot.

This module provides functionality for loading, validating, and accessing
YAML configuration files with efficient caching.
"""

import os
import yaml
import logging
import time
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache for loaded config files with timestamps
_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}

def get_config_path(config_name: str) -> Path:
    """
    Get full path for a config file.
    
    Args:
        config_name: Name of config file or subdirectory/file
        
    Returns:
        Path object for the config file
    """
    base_dir = Path(__file__).parent.parent
    config_dir = base_dir / "config"
    
    # Handle special cases for nested files (like personas/waifu)
    if '/' in config_name:
        return config_dir / config_name
        
    # Handle direct file access with .yaml extension
    if config_name.endswith(('.yaml', '.yml')):
        return config_dir / config_name
        
    # Default: add .yaml extension
    return config_dir / f"{config_name}.yaml"

def load_config(config_name: str, refresh: bool = False, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Load YAML config with caching.
    
    Args:
        config_name: Name of config (e.g. "alya", "personas/waifu")
        refresh: Force reload from disk
        default: Default values if config not found
        
    Returns:
        Config dictionary
    """
    # Check if we have a recent cache (less than 5 minutes old)
    cache_entry = _CONFIG_CACHE.get(config_name, {})
    
    if not refresh and cache_entry and time.time() - cache_entry.get('timestamp', 0) < 300:
        return cache_entry.get('data', {}) 
    
    config_path = get_config_path(config_name)
    
    try:
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return default or {}
            
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Validate data structure
        if not isinstance(data, dict):
            logger.error(f"Invalid config format in {config_path}: expected dictionary")
            return default or {}
        
        # Cache the result with timestamp
        _CONFIG_CACHE[config_name] = {
            'data': data,
            'timestamp': time.time()
        }
        
        return data
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {config_path}: {e}")
        return default or {}
    except Exception as e:
        logger.error(f"Error loading config {config_name}: {e}")
        return default or {}

def get_config_value(config_name: str, key_path: str, default: Any = None) -> Any:
    """
    Get specific config value using dot notation.
    
    Args:
        config_name: Name of config file
        key_path: Path to value using dot notation (e.g., 'database.host')
        default: Default value if key not found
        
    Returns:
        Config value or default
    """
    config = load_config(config_name)
    
    if not key_path:
        return config
        
    parts = key_path.split('.')
    current = config
    
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
        
    return current

def save_config(config_name: str, data: Dict[str, Any]) -> bool:
    """
    Save data to config file.
    
    Args:
        config_name: Name of config file
        data: Data to save
        
    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_path(config_name)
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write config
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
        # Update cache
        _CONFIG_CACHE[config_name] = {
            'data': data,
            'timestamp': time.time()
        }
        
        return True
    except Exception as e:
        logger.error(f"Error saving config {config_name}: {e}")
        return False

def clear_config_cache() -> int:
    """
    Clear the config cache.
    
    Returns:
        Number of cache entries cleared
    """
    count = len(_CONFIG_CACHE)
    _CONFIG_CACHE.clear()
    return count
