"""
YAML Loader Utility for Alya Bot.

This module provides utilities for loading and parsing YAML configuration files.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

class YAMLLoader:
    """Utility class for loading and managing YAML configuration files."""
    
    def __init__(self, base_dir: str):
        """
        Initialize the YAML loader.
        
        Args:
            base_dir: Base directory for YAML files
        """
        self.base_dir = base_dir
        self.data_cache = {}
        
    def load_file(self, filepath: str, refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Load a YAML file.
        
        Args:
            filepath: Path to YAML file
            refresh: Whether to refresh cache
        
        Returns:
            Parsed YAML data or None if error
        """
        try:
            # Check if file exists and is in cache
            if not refresh and filepath in self.data_cache:
                return self.data_cache[filepath]
            
            # Load file
            with open(filepath, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                self.data_cache[filepath] = data
                return data
        except Exception as e:
            logger.error(f"Error loading YAML file {filepath}: {e}")
            return None
    
    def load_directory(self, dirpath: str, refresh: bool = False) -> Dict[str, Any]:
        """
        Load all YAML files in a directory.
        
        Args:
            dirpath: Path to directory
            refresh: Whether to refresh cache
        
        Returns:
            Dictionary mapping filenames (without extension) to parsed data
        """
        results = {}
        try:
            full_path = os.path.join(self.base_dir, dirpath)
            if not os.path.exists(full_path):
                logger.warning(f"Directory does not exist: {full_path}")
                return results
                
            for filename in os.listdir(full_path):
                if filename.endswith(('.yaml', '.yml')):
                    name = os.path.splitext(filename)[0]
                    filepath = os.path.join(full_path, filename)
                    data = self.load_file(filepath, refresh)
                    if data:
                        results[name] = data
        except Exception as e:
            logger.error(f"Error loading YAML directory {dirpath}: {e}")
        
        return results
    
    def get_nested_value(self, data: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        Get a nested value from a dictionary using dot notation.
        
        Args:
            data: Dictionary to search in
            path: Path to value using dot notation (e.g., "persona.traits.0")
            default: Default value if path not found
            
        Returns:
            Value at path or default
        """
        if not data or not path:
            return default
            
        parts = path.split('.')
        current = data
        
        for part in parts:
            # Handle array index if it's a number
            if part.isdigit() and isinstance(current, list):
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return default
            elif part in current:
                current = current[part]
            else:
                return default
                
        return current
