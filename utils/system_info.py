"""
System Information Utilities for Alya Telegram Bot.

This module provides functions to gather and format system information
for status reporting and monitoring.
"""

import os
import platform
import psutil
import time
from datetime import datetime, timedelta

# =========================
# System Information
# =========================

def get_system_info() -> dict:
    """
    Get comprehensive system information.
    
    Returns:
        Dictionary with system information categories
    """
    return {
        'system': get_platform_info(),
        'cpu': get_cpu_info(),
        'memory': get_memory_info(),
        'disk': get_disk_info(),
        'network': get_network_info(),
        'process': get_process_info()
    }

def get_platform_info() -> dict:
    """Get basic platform and OS information."""
    return {
        'platform': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'architecture': platform.machine(),
        'hostname': platform.node(),
        'uptime': get_uptime()
    }

def get_cpu_info() -> dict:
    """Get CPU information and usage."""
    cpu_info = {
        'cores_physical': psutil.cpu_count(logical=False),
        'cores_logical': psutil.cpu_count(),
        'percent': psutil.cpu_percent(interval=1),
        'frequency': {}
    }
    
    # Get CPU frequency if available
    try:
        freq = psutil.cpu_freq()
        if freq:
            cpu_info['frequency'] = {
                'current': f"{freq.current:.2f} MHz",
                'min': f"{freq.min:.2f} MHz" if freq.min else "N/A",
                'max': f"{freq.max:.2f} MHz" if freq.max else "N/A"
            }
    except Exception:
        pass
        
    return cpu_info

def get_memory_info() -> dict:
    """Get RAM usage information."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return {
        'total': format_bytes(memory.total),
        'available': format_bytes(memory.available),
        'used': format_bytes(memory.used),
        'percent': memory.percent,
        'swap_total': format_bytes(swap.total),
        'swap_used': format_bytes(swap.used),
        'swap_percent': swap.percent
    }

def get_disk_info() -> dict:
    """Get disk usage information for root partition."""
    disk = psutil.disk_usage('/')
    
    return {
        'total': format_bytes(disk.total),
        'used': format_bytes(disk.used),
        'free': format_bytes(disk.free),
        'percent': disk.percent
    }

def get_network_info() -> dict:
    """Get basic network information."""
    net_io = psutil.net_io_counters()
    
    return {
        'bytes_sent': format_bytes(net_io.bytes_sent),
        'bytes_recv': format_bytes(net_io.bytes_recv),
        'packets_sent': net_io.packets_sent,
        'packets_recv': net_io.packets_recv,
        'connections': len(psutil.net_connections())
    }

def get_process_info() -> dict:
    """Get information about the current process."""
    process = psutil.Process()
    
    return {
        'pid': process.pid,
        'name': process.name(),
        'memory_used': format_bytes(process.memory_info().rss),
        'cpu_percent': process.cpu_percent(interval=0.5),
        'threads': process.num_threads(),
        'created': datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')
    }

# =========================
# Formatting Helpers
# =========================

def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable format with appropriate unit."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f} PB"

def get_uptime() -> str:
    """Get system uptime in a human-readable format."""
    uptime_seconds = time.time() - psutil.boot_time()
    uptime = timedelta(seconds=uptime_seconds)
    
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} days, {hours} hours, {minutes} minutes"
    elif hours > 0:
        return f"{hours} hours, {minutes} minutes"
    else:
        return f"{minutes} minutes, {seconds} seconds"

def bytes_to_gb(bytes_value: int) -> str:
    """Convert bytes to GB with 2 decimal places."""
    return f"{bytes_value / (1024**3):.2f} GB"
