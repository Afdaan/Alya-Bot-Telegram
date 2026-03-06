"""
Resource monitoring utilities for voice processing.
"""
import logging
import psutil
import torch

logger = logging.getLogger(__name__)


def get_optimal_rvc_config() -> dict:
    """Get optimal RVC config based on system resources."""
    try:
        if torch.cuda.is_available():
            return {'device': 'cuda', 'cpu_threads': 1}
        
        cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True)
        return {'device': 'cpu', 'cpu_threads': max(1, cpu_count - 1)}
    except Exception as e:
        logger.warning(f"⚠️ Error detecting resources: {e}, using defaults")
        return {'device': 'cpu', 'cpu_threads': 2}


def get_system_memory() -> dict | None:
    """Get current system memory usage."""
    try:
        m = psutil.virtual_memory()
        return {'total': m.total, 'available': m.available, 'used': m.used, 'percent': m.percent}
    except Exception as e:
        logger.error(f"❌ Error getting memory info: {e}")
        return None


def get_system_cpu_usage() -> float:
    """Get current CPU usage percentage."""
    try:
        return psutil.cpu_percent(interval=1)
    except Exception as e:
        logger.error(f"❌ Error getting CPU usage: {e}")
        return 0.0
