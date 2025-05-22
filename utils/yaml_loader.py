"""
YAML Loading Utilities for Alya Bot.

This module provides YAML file loading capabilities with caching
and nested value access for configuration management.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List, Union, Set
from pathlib import Path

logger = logging.getLogger(__name__)

class YAMLLoader:
    """
    YAML file loader with caching and nested value access.
    
    This class handles loading YAML files efficiently with caching
    to avoid redundant disk I/O operations.
    """
    
    def __init__(self, base_dir: Union[str, Path]):
        """
        Initialize the YAML loader.
        
        Args:
            base_dir: Base directory for YAML files
        """
        self.base_dir = Path(base_dir) if isinstance(base_dir, str) else base_dir
        self.data_cache: Dict[str, Dict[str, Any]] = {}
        self.file_mtimes: Dict[str, float] = {}  # Track file modification times
        self.cache_ttl = 300  # Cache TTL in seconds
        self.last_check: Dict[str, float] = {}  # Last check time for each file
    
    def load_file(self, filepath: Union[str, Path], refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Load a YAML file.
        
        Args:
            filepath: Path to YAML file
            refresh: Whether to refresh cache
        
        Returns:
            Parsed YAML data or None if error
        """
        try:
            # Convert to Path object
            path = Path(filepath) if isinstance(filepath, str) else filepath
            filepath_str = str(path)
            
            # Ensure path exists
            if not path.exists():
                logger.error(f"YAML file does not exist: {filepath_str}")
                return None
                
            # Check if file is in cache and not forcing refresh
            if not refresh and filepath_str in self.data_cache:
                # Check if we need to verify file mtime
                current_time = os.path.getmtime(path)
                last_mtime = self.file_mtimes.get(filepath_str, 0)
                
                # Use cached data if file hasn't been modified
                if current_time <= last_mtime:
                    return self.data_cache[filepath_str]
            
            # Load file
            with open(path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                
                # Update cache
                if data is not None:  # Only cache valid YAML
                    self.data_cache[filepath_str] = data
                    self.file_mtimes[filepath_str] = os.path.getmtime(path)
                    
                return data
                
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading YAML file {filepath}: {e}")
            return None
    
    def load_directory(self, dirpath: Union[str, Path], refresh: bool = False) -> Dict[str, Any]:
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
            # Handle path type conversion
            if isinstance(dirpath, str):
                if os.path.isabs(dirpath):
                    full_path = Path(dirpath)
                else:
                    full_path = self.base_dir / dirpath
            else:
                if dirpath.is_absolute():
                    full_path = dirpath
                else:
                    full_path = self.base_dir / dirpath
            
            # Check if directory exists
            if not full_path.exists():
                logger.warning(f"Directory does not exist: {full_path}")
                return results
                
            # Load all YAML files
            for file_path in full_path.glob("*.*"):
                if file_path.suffix.lower() in ('.yaml', '.yml'):
                    name = file_path.stem
                    data = self.load_file(file_path, refresh)
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
            path: Path to value using dot notation (e.g., 'parent.child.key')
            default: Default value to return if path not found
            
        Returns:
            Value at the specified path or default if not found
        """
        if not data or not isinstance(data, dict):
            return default
            
        if not path:
            return data
            
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current
    
    def save_file(self, filepath: Union[str, Path], data: Dict[str, Any]) -> bool:
        """
        Save data to a YAML file.
        
        Args:
            filepath: Path to YAML file
            data: Data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to Path object
            path = Path(filepath) if isinstance(filepath, str) else filepath
            filepath_str = str(path)
            
            # Ensure directory exists
            dir_path = path.parent
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                
            # Save file
            with open(path, 'w', encoding='utf-8') as file:
                yaml.safe_dump(data, file, default_flow_style=False, sort_keys=False)
                
            # Update cache
            self.data_cache[filepath_str] = data
            self.file_mtimes[filepath_str] = os.path.getmtime(path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving YAML file {filepath}: {e}")
            return False
    
    def update_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
        """
        Update a nested value in a dictionary using dot notation.
        
        Args:
            data: Dictionary to update
            path: Path to value using dot notation (e.g., 'parent.child.key')
            value: New value to set
            
        Returns:
            Updated dictionary
        """
        if not data:
            data = {}
            
        if not path:
            return data
            
        parts = path.split('.')
        current = data
        
        # Navigate to the parent of the final key
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
            
        # Set the value at the final key
        current[parts[-1]] = value
        
        return data
    
    def get_file_paths(self, extension: str = '.yaml') -> List[Path]:
        """
        Get all YAML file paths under the base directory.
        
        Args:
            extension: File extension to look for
            
        Returns:
            List of file paths
        """
        extension = extension.lower()
        paths = []
        
        try:
            # Search all subdirectories recursively
            for path in self.base_dir.rglob(f"*{extension}"):
                if path.is_file():
                    paths.append(path)
                    
        except Exception as e:
            logger.error(f"Error getting YAML file paths: {e}")
            
        return paths
    
    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        Clear the file cache, optionally by pattern.
        
        Args:
            pattern: Optional file path pattern to match
            
        Returns:
            Number of items removed from cache
        """
        if not pattern:
            # Clear entire cache
            count = len(self.data_cache)
            self.data_cache.clear()
            self.file_mtimes.clear()
            return count
            
        # Clear by pattern
        remove_keys = [
            k for k in self.data_cache 
            if pattern in k
        ]
        
        for key in remove_keys:
            del self.data_cache[key]
            if key in self.file_mtimes:
                del self.file_mtimes[key]
                
        return len(remove_keys)
    
    def merge_yaml_files(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """
        Merge multiple YAML files into a single dictionary.
        
        Args:
            file_paths: List of file paths to merge
            
        Returns:
            Merged dictionary
        """
        merged_data = {}
        
        for path in file_paths:
            data = self.load_file(path)
            if data and isinstance(data, dict):
                # Merge dictionaries (shallow merge)
                merged_data.update(data)
                
        return merged_data

# Create singleton instance (base directory is project root)
yaml_loader = YAMLLoader(Path(__file__).parent.parent)

def load_yaml_file(filepath: Union[str, Path], refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Load a YAML file (convenience function).
    
    Args:
        filepath: Path to YAML file
        refresh: Whether to refresh cache
        
    Returns:
        Parsed YAML data or None if error
    """
    return yaml_loader.load_file(filepath, refresh)

def load_yaml_directory(dirpath: Union[str, Path], refresh: bool = False) -> Dict[str, Any]:
    """
    Load all YAML files in a directory (convenience function).
    
    Args:
        dirpath: Path to directory
        refresh: Whether to refresh cache
        
    Returns:
        Dictionary mapping filenames (without extension) to parsed data
    """
    return yaml_loader.load_directory(dirpath, refresh)