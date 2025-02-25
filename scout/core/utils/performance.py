"""
Performance Profiling Utilities

This module provides utilities for profiling and optimizing the performance
of the Scout application. It includes tools for measuring execution time,
memory usage, and identifying bottlenecks in the image processing and
detection pipelines.
"""

import time
import cProfile
import pstats
import io
import functools
import gc
import logging
import os
# Try to import real psutil, fall back to our stub implementation
try:
    import psutil
except ImportError:
    from .psutil_stub import Process, virtual_memory, cpu_count, cpu_percent, disk_usage
    import scout.core.utils.psutil_stub as psutil
import tracemalloc
from typing import Callable, Dict, List, Tuple, Any, Optional
import numpy as np
import cv2

# Set up logging
logger = logging.getLogger(__name__)

class ExecutionTimer:
    """
    Utility class for measuring execution time of code blocks or functions.
    
    Can be used as a context manager or as a decorator.
    
    Examples:
        # As a context manager
        with ExecutionTimer("Detection operation"):
            results = detection_service.detect_template(...)
            
        # As a decorator
        @ExecutionTimer("Template matching")
        def match_template(image, template):
            # ...
    """
    
    def __init__(self, operation_name: str, log_level: int = logging.DEBUG):
        """
        Initialize the execution timer.
        
        Args:
            operation_name: Name of the operation being timed
            log_level: Logging level to use (default: DEBUG)
        """
        self.operation_name = operation_name
        self.log_level = log_level
        self.start_time = None
        self.execution_time = None
        
    def __enter__(self):
        """Start timing when entering the context."""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing when exiting the context and log the result."""
        self.execution_time = time.time() - self.start_time
        logger.log(self.log_level, f"{self.operation_name} completed in {self.execution_time:.4f} seconds")
        
    def __call__(self, func):
        """Use as a decorator for functions."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


class PerformanceProfiler:
    """
    Utility for profiling the performance of the application.
    
    Provides methods for:
    - Measuring execution time of functions
    - Tracking memory usage
    - Identifying bottlenecks using cProfile
    - Collecting performance statistics for analysis
    """
    
    def __init__(self):
        """Initialize the performance profiler."""
        self.stats = {}
        self.memory_tracking_active = False
        
    def start_memory_tracking(self):
        """Start tracking memory allocations."""
        tracemalloc.start()
        self.memory_tracking_active = True
        logger.debug("Memory tracking started")
        
    def stop_memory_tracking(self) -> Tuple[int, List[tracemalloc.Snapshot]]:
        """
        Stop tracking memory allocations and return statistics.
        
        Returns:
            Tuple of (current memory usage, snapshot)
        """
        if not self.memory_tracking_active:
            logger.warning("Memory tracking was not active")
            return 0, None
            
        current, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        self.memory_tracking_active = False
        
        logger.debug(f"Memory tracking stopped. Current: {current / 1024:.2f} KB, Peak: {peak / 1024:.2f} KB")
        return current, snapshot
        
    def analyze_memory_snapshot(self, snapshot, top_n: int = 10) -> List[Dict]:
        """
        Analyze memory snapshot to find largest allocations.
        
        Args:
            snapshot: Memory snapshot to analyze
            top_n: Number of top allocations to return
            
        Returns:
            List of dictionaries with allocation statistics
        """
        if snapshot is None:
            return []
            
        stats = []
        top_stats = snapshot.statistics('lineno')
        
        for stat in top_stats[:top_n]:
            frame = stat.traceback[0]
            stats.append({
                'file': os.path.basename(frame.filename),
                'line': frame.lineno,
                'size': stat.size / 1024,  # KB
                'count': stat.count
            })
            
        return stats
        
    def profile_function(self, func, *args, **kwargs) -> Tuple[Any, pstats.Stats]:
        """
        Profile a function using cProfile.
        
        Args:
            func: Function to profile
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Tuple of (function result, profile statistics)
        """
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()
            
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Print top 20 functions by cumulative time
        
        logger.debug(f"Profile for {func.__name__}:\n{s.getvalue()}")
        return result, ps
        
    def measure_function_execution_time(self, func: Callable, iterations: int = 1, 
                                       *args, **kwargs) -> Dict[str, float]:
        """
        Measure the execution time of a function over multiple iterations.
        
        Args:
            func: Function to measure
            iterations: Number of iterations to run
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Dictionary with timing statistics
        """
        times = []
        
        for i in range(iterations):
            start_time = time.time()
            func(*args, **kwargs)
            execution_time = time.time() - start_time
            times.append(execution_time)
            
        return {
            'mean': np.mean(times),
            'median': np.median(times),
            'min': np.min(times),
            'max': np.max(times),
            'std': np.std(times) if iterations > 1 else 0,
            'iterations': iterations
        }
        
    def measure_memory_usage(self, func: Callable, *args, **kwargs) -> Dict[str, float]:
        """
        Measure memory usage of a function.
        
        Args:
            func: Function to measure
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Dictionary with memory usage statistics
        """
        # Force garbage collection to get a clean starting point
        gc.collect()
        
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024  # KB
        
        # Execute the function
        result = func(*args, **kwargs)
        
        # Force garbage collection to clean up temporary objects
        gc.collect()
        
        end_memory = process.memory_info().rss / 1024  # KB
        memory_diff = end_memory - start_memory
        
        return {
            'start_memory_kb': start_memory,
            'end_memory_kb': end_memory,
            'diff_kb': memory_diff,
            'result': result
        }
        
    def benchmark_detection_strategies(self, strategies: Dict[str, Callable], 
                                      images: List[np.ndarray], 
                                      iterations: int = 5) -> Dict[str, Dict]:
        """
        Benchmark multiple detection strategies against a set of test images.
        
        Args:
            strategies: Dictionary mapping strategy name to detection function
            images: List of test images to run detection on
            iterations: Number of iterations for each strategy/image
            
        Returns:
            Dictionary with benchmark results
        """
        results = {}
        
        for strategy_name, detection_func in strategies.items():
            strategy_results = {'execution_time': [], 'memory_usage': []}
            
            for i, image in enumerate(images):
                # Measure execution time
                with ExecutionTimer(f"{strategy_name} - Image {i}") as timer:
                    for _ in range(iterations):
                        detection_func(image)
                        
                strategy_results['execution_time'].append({
                    'image_index': i,
                    'time_seconds': timer.execution_time / iterations
                })
                
                # Measure memory usage (just once per image)
                memory_info = self.measure_memory_usage(detection_func, image)
                strategy_results['memory_usage'].append({
                    'image_index': i,
                    'memory_kb': memory_info['diff_kb']
                })
                
            results[strategy_name] = strategy_results
            
        return results
        
    def analyze_image_processing_performance(self, image: np.ndarray, operations: Dict[str, Callable]) -> Dict[str, float]:
        """
        Analyze performance of different image processing operations.
        
        Args:
            image: Image to process
            operations: Dictionary mapping operation name to function
            
        Returns:
            Dictionary with execution times for each operation
        """
        results = {}
        
        for op_name, op_func in operations.items():
            with ExecutionTimer(f"Image operation: {op_name}") as timer:
                op_func(image)
                
            results[op_name] = timer.execution_time
            
        return results
        
    def compare_image_sizes(self, image: np.ndarray) -> Dict[str, Dict]:
        """
        Compare performance impact of different image sizes.
        
        Args:
            image: Original image to resize
            
        Returns:
            Dictionary with performance metrics for different sizes
        """
        results = {}
        original_size = image.shape[:2]
        
        # Define standard resize operations
        resize_factors = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        
        for factor in resize_factors:
            new_height = int(original_size[0] * factor)
            new_width = int(original_size[1] * factor)
            
            # Skip if too small
            if new_height < 10 or new_width < 10:
                continue
                
            # Resize image
            resized = cv2.resize(image, (new_width, new_height))
            
            # Define test operations
            def test_blur():
                return cv2.GaussianBlur(resized, (5, 5), 0)
                
            def test_canny():
                return cv2.Canny(resized, 100, 200)
                
            def test_template_match():
                # Create a small template from the image itself
                h, w = resized.shape[:2]
                template = resized[h//4:h//2, w//4:w//2]
                return cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
                
            # Measure performance
            operations = {
                'blur': test_blur,
                'canny': test_canny,
                'template_match': test_template_match
            }
            
            size_results = self.analyze_image_processing_performance(resized, operations)
            size_results['image_size'] = {'height': new_height, 'width': new_width}
            
            results[f"factor_{factor:.2f}"] = size_results
            
        return results
        
    def optimize_template_matching(self, image: np.ndarray, template: np.ndarray, 
                                 methods: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Find the optimal template matching method and parameters.
        
        Args:
            image: Image to search in
            template: Template to search for
            methods: List of OpenCV template matching methods to test
            
        Returns:
            Dictionary with performance results for different methods
        """
        if methods is None:
            methods = [
                cv2.TM_CCOEFF_NORMED,
                cv2.TM_CCORR_NORMED,
                cv2.TM_SQDIFF_NORMED
            ]
            
        method_names = {
            cv2.TM_CCOEFF: "TM_CCOEFF",
            cv2.TM_CCOEFF_NORMED: "TM_CCOEFF_NORMED",
            cv2.TM_CCORR: "TM_CCORR",
            cv2.TM_CCORR_NORMED: "TM_CCORR_NORMED",
            cv2.TM_SQDIFF: "TM_SQDIFF",
            cv2.TM_SQDIFF_NORMED: "TM_SQDIFF_NORMED"
        }
        
        results = {}
        
        # Test different template matching methods
        for method in methods:
            method_name = method_names.get(method, f"Method_{method}")
            
            with ExecutionTimer(f"Template matching with {method_name}") as timer:
                result = cv2.matchTemplate(image, template, method)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
            # Determine the matching location based on the method
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                match_loc = min_loc
                match_val = min_val
            else:
                match_loc = max_loc
                match_val = max_val
                
            results[method_name] = {
                'execution_time': timer.execution_time,
                'match_value': match_val,
                'match_location': match_loc
            }
            
        return results
            
    def save_stats(self, name: str, data: Any):
        """
        Save performance statistics for later analysis.
        
        Args:
            name: Name to associate with the statistics
            data: Data to save
        """
        self.stats[name] = data
        logger.debug(f"Saved performance stats: {name}")
        
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get information about the system for performance context.
        
        Returns:
            Dictionary with system information
        """
        return {
            'cpu_count': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total': psutil.virtual_memory().total / (1024 * 1024),  # MB
            'memory_available': psutil.virtual_memory().available / (1024 * 1024),  # MB
            'platform': os.name,
            'python_version': os.sys.version
        }


# Singleton instance for global use
profiler = PerformanceProfiler()


def profile(func=None, *, name=None):
    """
    Decorator for profiling functions.
    
    Args:
        func: Function to profile
        name: Optional name for the profiling results
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            profile_name = name or f.__name__
            logger.debug(f"Profiling {profile_name}")
            
            # Start memory tracking
            profiler.start_memory_tracking()
            
            # Measure execution time
            start_time = time.time()
            result = f(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Stop memory tracking and get results
            memory_usage, snapshot = profiler.stop_memory_tracking()
            memory_stats = profiler.analyze_memory_snapshot(snapshot, top_n=5)
            
            # Save the profiling information
            profiler.save_stats(profile_name, {
                'execution_time': execution_time,
                'memory_usage': memory_usage / 1024,  # KB
                'memory_details': memory_stats,
                'timestamp': time.time()
            })
            
            logger.debug(f"{profile_name} executed in {execution_time:.4f} seconds")
            
            return result
        return wrapper
        
    if func is None:
        return decorator
    return decorator(func)


def time_function(func=None, *, iterations=1, name=None):
    """
    Decorator for timing function execution over multiple iterations.
    
    Args:
        func: Function to time
        iterations: Number of iterations to run
        name: Optional name for the timing results
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            profile_name = name or f.__name__
            
            # Time the function
            timing_stats = profiler.measure_function_execution_time(f, iterations, *args, **kwargs)
            
            # Save the timing information
            profiler.save_stats(f"{profile_name}_timing", timing_stats)
            
            # Run the function one more time to get the result
            return f(*args, **kwargs)
        return wrapper
        
    if func is None:
        return decorator
    return decorator(func)


def analyze_image_pipeline(name, image_provider, pipeline_steps):
    """
    Analyze the performance of an image processing pipeline.
    
    Args:
        name: Name for this analysis
        image_provider: Function that returns the image to process
        pipeline_steps: Dictionary mapping step name to processing function
        
    Returns:
        Dictionary with performance results for each step
    """
    image = image_provider()
    results = {
        'name': name,
        'image_shape': image.shape,
        'steps': {}
    }
    
    current_image = image
    
    for step_name, step_func in pipeline_steps.items():
        with ExecutionTimer(f"Pipeline step: {step_name}") as timer:
            current_image = step_func(current_image)
            
        results['steps'][step_name] = {
            'execution_time': timer.execution_time,
            'output_shape': current_image.shape if hasattr(current_image, 'shape') else None
        }
        
    return results 