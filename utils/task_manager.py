"""
Task Management Utilities for Alya Bot.

This module provides enterprise-grade thread and task management
for performance-critical operations.
"""

import logging
import asyncio
import threading
import concurrent.futures
from typing import Dict, Any, Callable, Coroutine, TypeVar, Generic, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

# Type variables for generics
T = TypeVar('T')
R = TypeVar('R')

@dataclass
class TaskMetrics:
    """
    Metrics for task execution monitoring.
    
    This class stores performance metrics about task execution
    to enable monitoring and optimization.
    """
    task_id: str
    task_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    context: Dict[str, Any] = None

class TaskManager:
    """
    Enterprise-grade task manager for optimized concurrent operations.
    
    This class helps offload CPU-bound tasks to a thread pool while
    keeping track of metrics for monitoring and diagnostics.
    """
    
    def __init__(self, max_workers: int = 4, task_timeout: int = 30):
        """
        Initialize task manager.
        
        Args:
            max_workers: Maximum number of thread workers
            task_timeout: Default task timeout in seconds
        """
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix="alya_task_"
        )
        self.task_timeout = task_timeout
        self.metrics: List[TaskMetrics] = []
        self.metrics_lock = threading.Lock()
        self._task_id_counter = 0
        self._id_lock = threading.Lock()
        logger.debug(f"TaskManager initialized with {max_workers} workers and {task_timeout}s timeout")
    
    def _generate_task_id(self) -> str:
        """
        Generate unique task ID.
        
        Returns:
            Unique task ID string
        """
        with self._id_lock:
            task_id = f"task_{self._task_id_counter}"
            self._task_id_counter += 1
            return task_id
    
    async def run_in_thread(self, 
                           func: Callable[..., T], 
                           *args,
                           task_type: Optional[str] = None, 
                           timeout: Optional[int] = None,
                           context: Optional[Dict[str, Any]] = None, 
                           **kwargs) -> T:
        """
        Run a blocking function in a thread pool.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            task_type: Type of task for metrics (defaults to function name)
            timeout: Optional custom timeout in seconds
            context: Optional context for metrics
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            TimeoutError: If task exceeds timeout
            Exception: Any exception raised by the function
        """
        task_id = self._generate_task_id()
        task_type = task_type or func.__name__
        timeout = timeout or self.task_timeout
        
        metrics = TaskMetrics(
            task_id=task_id,
            task_type=task_type,
            start_time=datetime.now(),
            context=context or {}
        )
        
        try:
            # Execute task in thread pool with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(self.executor, func, *args, **kwargs),
                timeout=timeout
            )
            
            # Update metrics on success
            metrics.end_time = datetime.now()
            metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
            metrics.success = True
            
            # Log slow operations
            if metrics.duration_ms > 1000:  # More than 1 second
                logger.warning(f"Slow operation: {task_type} took {metrics.duration_ms:.2f}ms")
            
            return result
            
        except asyncio.TimeoutError:
            # Handle timeout
            metrics.end_time = datetime.now()
            metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
            metrics.success = False
            metrics.error = "Task timed out"
            logger.error(f"Task {task_id} ({task_type}) timed out after {timeout} seconds")
            raise TimeoutError(f"Task {task_id} ({task_type}) timed out after {timeout} seconds")
            
        except Exception as e:
            # Handle other errors
            metrics.end_time = datetime.now()
            metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
            metrics.success = False
            metrics.error = str(e)
            logger.error(f"Task {task_id} ({task_type}) failed: {e}")
            raise
            
        finally:
            # Store metrics
            with self.metrics_lock:
                self.metrics.append(metrics)
                # Keep only last 100 metrics
                if len(self.metrics) > 100:
                    self.metrics = self.metrics[-100:]
    
    def get_task_stats(self) -> Dict[str, Any]:
        """
        Get task execution statistics.
        
        Returns:
            Dictionary with task statistics
        """
        with self.metrics_lock:
            if not self.metrics:
                return {
                    "count": 0, 
                    "avg_duration_ms": 0, 
                    "success_rate": 0,
                    "task_distribution": {}
                }
            
            total_tasks = len(self.metrics)
            successful_tasks = sum(1 for m in self.metrics if m.success)
            
            # Calculate average duration for completed tasks
            durations = [m.duration_ms for m in self.metrics if m.duration_ms is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Get task type distribution
            task_types = {}
            for m in self.metrics:
                task_types[m.task_type] = task_types.get(m.task_type, 0) + 1
                
            # Calculate success rate by task type
            success_by_type = {}
            for m in self.metrics:
                if m.task_type not in success_by_type:
                    success_by_type[m.task_type] = {"success": 0, "total": 0}
                success_by_type[m.task_type]["total"] += 1
                if m.success:
                    success_by_type[m.task_type]["success"] += 1
            
            # Convert to percentage
            type_success_rates = {
                t: data["success"] / data["total"] if data["total"] > 0 else 0
                for t, data in success_by_type.items()
            }
            
            return {
                "count": total_tasks,
                "success_count": successful_tasks,
                "failure_count": total_tasks - successful_tasks,
                "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
                "avg_duration_ms": avg_duration,
                "task_distribution": task_types,
                "type_success_rates": type_success_rates,
                "recent_errors": [
                    {"task_id": m.task_id, "task_type": m.task_type, "error": m.error}
                    for m in self.metrics[-10:] if not m.success and m.error
                ]
            }
    
    def shutdown(self) -> None:
        """
        Shutdown the task manager gracefully.
        
        This ensures all threads are properly terminated.
        """
        self.executor.shutdown(wait=True)
        logger.info("TaskManager shutdown complete")

# Create singleton instance
task_manager = TaskManager()

# Decorator for performance monitoring
def monitor_performance(task_name: str = None):
    """
    Decorator to monitor performance of async functions.
    
    Args:
        task_name: Name of the task (defaults to function name)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            function_name = task_name or func.__name__
            start_time = datetime.now()
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                # Log slow operations
                if duration_ms > 1000:  # More than 1 second
                    logger.warning(f"Slow operation: {function_name} took {duration_ms:.2f}ms")
                
                return result
                
            except Exception as e:
                # Log error with performance context
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(f"Error in {function_name} after {duration_ms:.2f}ms: {str(e)}")
                raise
                
        return wrapper
    
    return decorator

# Run CPU-bound function in thread pool (convenience function)
async def run_cpu_bound(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a CPU-bound function in thread pool (convenience function).
    
    Args:
        func: Function to execute
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Function result
    """
    return await task_manager.run_in_thread(func, *args, **kwargs)
