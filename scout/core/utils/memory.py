"""
Memory Management Utilities

This module provides utilities for monitoring and optimizing memory usage
in the Scout application, helping prevent memory leaks and ensuring efficient
resource utilization.
"""

import gc
import os
import sys
import time
import logging
import threading
import weakref
from typing import Dict, List, Any, Optional, Callable, Set, Tuple, Type
import psutil
import numpy as np

# Set up logging
logger = logging.getLogger(__name__)

class MemoryMonitor:
    """
    Utility for monitoring memory usage of the application.
    
    Provides methods for:
    - Tracking memory usage over time
    - Identifying memory leaks
    - Taking memory snapshots for comparison
    - Triggering garbage collection when memory usage exceeds thresholds
    """
    
    def __init__(self, threshold_mb: float = 500, poll_interval: float = 10):
        """
        Initialize the memory monitor.
        
        Args:
            threshold_mb: Memory threshold in MB to trigger cleanup
            poll_interval: Time between memory checks in seconds
        """
        self.threshold_mb = threshold_mb
        self.poll_interval = poll_interval
        self.process = psutil.Process(os.getpid())
        self.snapshots = []
        self.monitoring = False
        self.monitor_thread = None
        self.memory_data = []
        self.lock = threading.RLock()
        
    def start_monitoring(self) -> None:
        """Start the memory monitoring thread."""
        with self.lock:
            if self.monitoring:
                logger.warning("Memory monitoring already active")
                return
                
            self.monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()
            logger.info(f"Started memory monitoring (threshold: {self.threshold_mb}MB)")
        
    def stop_monitoring(self) -> None:
        """Stop the memory monitoring thread."""
        with self.lock:
            if not self.monitoring:
                logger.warning("Memory monitoring not active")
                return
                
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=2.0)
                self.monitor_thread = None
            logger.info("Stopped memory monitoring")
        
    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in a background thread."""
        while self.monitoring:
            try:
                # Get current memory usage
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                
                # Save memory data point
                with self.lock:
                    self.memory_data.append((time.time(), memory_mb))
                    
                    # Keep only the last 1000 data points
                    if len(self.memory_data) > 1000:
                        self.memory_data = self.memory_data[-1000:]
                
                # Check if cleanup is needed
                if memory_mb > self.threshold_mb:
                    logger.warning(f"Memory usage ({memory_mb:.2f}MB) exceeds threshold ({self.threshold_mb}MB)")
                    self.force_cleanup()
                    
                # Sleep for the poll interval
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
                time.sleep(self.poll_interval)
                
    def force_cleanup(self) -> float:
        """
        Force garbage collection and memory cleanup.
        
        Returns:
            Memory freed in MB
        """
        # Record memory before cleanup
        memory_before = self.process.memory_info().rss / (1024 * 1024)
        
        # Force garbage collection
        collected = gc.collect()
        
        # Record memory after cleanup
        memory_after = self.process.memory_info().rss / (1024 * 1024)
        memory_freed = memory_before - memory_after
        
        logger.info(f"Memory cleanup: collected {collected} objects, freed {memory_freed:.2f}MB")
        return memory_freed
        
    def take_snapshot(self, name: str) -> Dict[str, Any]:
        """
        Take a snapshot of current memory state.
        
        Args:
            name: Name for this snapshot
            
        Returns:
            Dictionary with snapshot information
        """
        # Record memory usage
        memory_info = self.process.memory_info()
        
        # Get garbage collector statistics
        gc_counts = gc.get_count()
        
        # Create snapshot
        snapshot = {
            'name': name,
            'timestamp': time.time(),
            'memory_rss_mb': memory_info.rss / (1024 * 1024),
            'memory_vms_mb': memory_info.vms / (1024 * 1024),
            'gc_counts': gc_counts,
            'gc_objects': len(gc.get_objects())
        }
        
        # Save snapshot
        with self.lock:
            self.snapshots.append(snapshot)
            
        logger.debug(f"Took memory snapshot '{name}': {snapshot['memory_rss_mb']:.2f}MB RSS")
        return snapshot
        
    def compare_snapshots(self, name1: str, name2: str) -> Dict[str, Any]:
        """
        Compare two memory snapshots.
        
        Args:
            name1: Name of first snapshot
            name2: Name of second snapshot
            
        Returns:
            Dictionary with comparison results
        """
        with self.lock:
            # Find snapshots by name
            snapshot1 = next((s for s in self.snapshots if s['name'] == name1), None)
            snapshot2 = next((s for s in self.snapshots if s['name'] == name2), None)
            
            if not snapshot1 or not snapshot2:
                missing = name1 if not snapshot1 else name2
                logger.error(f"Snapshot not found: {missing}")
                return {}
                
            # Calculate differences
            time_diff = snapshot2['timestamp'] - snapshot1['timestamp']
            rss_diff = snapshot2['memory_rss_mb'] - snapshot1['memory_rss_mb']
            vms_diff = snapshot2['memory_vms_mb'] - snapshot1['memory_vms_mb']
            obj_diff = snapshot2['gc_objects'] - snapshot1['gc_objects']
            
            # Create result
            result = {
                'snapshot1': name1,
                'snapshot2': name2,
                'time_diff_sec': time_diff,
                'rss_diff_mb': rss_diff,
                'vms_diff_mb': vms_diff,
                'object_count_diff': obj_diff
            }
            
            logger.info(f"Memory comparison {name1} → {name2}: {rss_diff:.2f}MB RSS change over {time_diff:.2f}s")
            return result
            
    def get_memory_trend(self, minutes: float = 5) -> Dict[str, Any]:
        """
        Analyze memory usage trend over the specified time period.
        
        Args:
            minutes: Time period to analyze in minutes
            
        Returns:
            Dictionary with trend analysis
        """
        with self.lock:
            if not self.memory_data:
                return {'error': 'No memory data available'}
                
            # Calculate cutoff time
            cutoff_time = time.time() - (minutes * 60)
            
            # Filter data points within time period
            recent_data = [(t, m) for t, m in self.memory_data if t >= cutoff_time]
            
            if not recent_data:
                return {'error': f'No memory data available for the last {minutes} minutes'}
                
            # Extract times and memory values
            times, memory_values = zip(*recent_data)
            
            # Convert to relative times in minutes
            relative_times = [(t - times[0]) / 60 for t in times]
            
            # Calculate statistics
            min_memory = min(memory_values)
            max_memory = max(memory_values)
            avg_memory = sum(memory_values) / len(memory_values)
            
            # Calculate trend (linear regression)
            if len(recent_data) >= 2:
                # Calculate slope using least squares
                n = len(relative_times)
                sum_x = sum(relative_times)
                sum_y = sum(memory_values)
                sum_xy = sum(x * y for x, y in zip(relative_times, memory_values))
                sum_xx = sum(x * x for x in relative_times)
                
                # Avoid division by zero
                if n * sum_xx - sum_x * sum_x != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
                else:
                    slope = 0
            else:
                slope = 0
                
            # Create result
            result = {
                'period_minutes': minutes,
                'data_points': len(recent_data),
                'min_memory_mb': min_memory,
                'max_memory_mb': max_memory,
                'avg_memory_mb': avg_memory,
                'memory_slope_mb_per_minute': slope,
                'latest_memory_mb': memory_values[-1] if memory_values else 0
            }
            
            return result
            
    def get_system_memory_info(self) -> Dict[str, Any]:
        """
        Get information about system memory usage.
        
        Returns:
            Dictionary with system memory information
        """
        vm = psutil.virtual_memory()
        
        return {
            'total_mb': vm.total / (1024 * 1024),
            'available_mb': vm.available / (1024 * 1024),
            'used_mb': vm.used / (1024 * 1024),
            'free_mb': vm.free / (1024 * 1024),
            'percent_used': vm.percent
        }


class ResourceTracker:
    """
    Utility for tracking resource usage and detecting leaks.
    
    Can be used to track specific resource types like images or large objects
    and ensure they are properly cleaned up.
    """
    
    def __init__(self):
        """Initialize the resource tracker."""
        self.resources = weakref.WeakValueDictionary()
        self.resource_counts = {}
        self.lock = threading.RLock()
        
    def track(self, resource: Any, resource_type: str = 'generic') -> int:
        """
        Track a resource for potential memory leaks.
        
        Args:
            resource: Resource to track
            resource_type: Type of resource for categorization
            
        Returns:
            Resource ID
        """
        with self.lock:
            # Generate resource ID
            resource_id = id(resource)
            
            # Track resource with a weak reference
            self.resources[resource_id] = resource
            
            # Update count for this resource type
            self.resource_counts[resource_type] = self.resource_counts.get(resource_type, 0) + 1
            
            return resource_id
            
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about tracked resources.
        
        Returns:
            Dictionary mapping resource types to counts
        """
        with self.lock:
            # Copy resource counts
            return dict(self.resource_counts)
            
    def cleanup_resources(self) -> Dict[str, int]:
        """
        Force cleanup of resources that are no longer referenced.
        
        Returns:
            Dictionary mapping resource types to number of resources cleaned
        """
        with self.lock:
            # Get initial resource counts
            initial_counts = dict(self.resource_counts)
            
            # Force garbage collection
            gc.collect()
            
            # Resources with weak references will be automatically removed
            # from self.resources if they're no longer referenced elsewhere
            
            # Recalculate resource counts
            for resource_type in list(self.resource_counts.keys()):
                count = sum(1 for rid, res in self.resources.items())
                if count == 0:
                    del self.resource_counts[resource_type]
                else:
                    self.resource_counts[resource_type] = count
                    
            # Calculate cleaned resources
            cleaned = {}
            for resource_type, initial_count in initial_counts.items():
                current_count = self.resource_counts.get(resource_type, 0)
                cleaned_count = initial_count - current_count
                if cleaned_count > 0:
                    cleaned[resource_type] = cleaned_count
                    
            return cleaned


class ImageBuffer:
    """
    Buffer for efficiently reusing and managing image data.
    
    Provides methods for:
    - Recycling images to reduce allocations
    - Managing image lifecycle
    - Optimizing memory usage for large images
    """
    
    def __init__(self, max_size: int = 20):
        """
        Initialize the image buffer.
        
        Args:
            max_size: Maximum number of images to keep in buffer
        """
        self.max_size = max_size
        self.buffer = {}  # Maps (height, width, channels) to list of images
        self.lock = threading.RLock()
        
    def get(self, height: int, width: int, channels: int = 3) -> np.ndarray:
        """
        Get an image from the buffer or create a new one.
        
        Args:
            height: Image height
            width: Image width
            channels: Number of channels (default: 3 for BGR)
            
        Returns:
            NumPy array for the image
        """
        with self.lock:
            # Create key for this image size
            key = (height, width, channels)
            
            # Check if we have an image of this size in the buffer
            if key in self.buffer and self.buffer[key]:
                # Reuse existing image
                image = self.buffer[key].pop()
                # Make sure image is zeroed out
                image.fill(0)
                return image
            else:
                # Create new image
                return np.zeros((height, width, channels), dtype=np.uint8)
                
    def put(self, image: np.ndarray) -> None:
        """
        Return an image to the buffer for reuse.
        
        Args:
            image: Image data as NumPy array
        """
        with self.lock:
            # Extract image dimensions
            if image.ndim == 2:
                height, width = image.shape
                channels = 1
            else:
                height, width, channels = image.shape
                
            # Create key for this image size
            key = (height, width, channels)
            
            # Add image to buffer if there's space
            if key not in self.buffer:
                self.buffer[key] = []
                
            if len(self.buffer[key]) < self.max_size:
                self.buffer[key].append(image)
                
    def clear(self) -> None:
        """Clear all images from the buffer."""
        with self.lock:
            self.buffer.clear()
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the image buffer.
        
        Returns:
            Dictionary with buffer statistics
        """
        with self.lock:
            stats = {
                'total_images': sum(len(images) for images in self.buffer.values()),
                'unique_sizes': len(self.buffer),
                'memory_mb': 0
            }
            
            # Calculate total memory usage
            for (height, width, channels), images in self.buffer.items():
                image_size_bytes = height * width * channels
                buffer_size_bytes = image_size_bytes * len(images)
                stats['memory_mb'] += buffer_size_bytes / (1024 * 1024)
                
            return stats


class MemoryOptimizer:
    """
    Utility for optimizing memory usage in the application.
    
    Provides methods for:
    - Memory-efficient object allocation
    - Detecting and fixing memory leaks
    - Scheduling memory cleanup
    """
    
    def __init__(self):
        """Initialize the memory optimizer."""
        self.monitor = MemoryMonitor()
        self.resource_tracker = ResourceTracker()
        self.image_buffer = ImageBuffer()
        self.cleanup_scheduled = False
        self.cleanup_thread = None
        self.lock = threading.RLock()
        
    def start(self) -> None:
        """Start memory optimization services."""
        with self.lock:
            self.monitor.start_monitoring()
            
            # Schedule periodic cleanup
            if not self.cleanup_scheduled:
                self.cleanup_scheduled = True
                self.cleanup_thread = threading.Thread(
                    target=self._periodic_cleanup,
                    daemon=True
                )
                self.cleanup_thread.start()
                
            logger.info("Started memory optimization services")
            
    def stop(self) -> None:
        """Stop memory optimization services."""
        with self.lock:
            self.monitor.stop_monitoring()
            self.cleanup_scheduled = False
            
            # Clear image buffer
            self.image_buffer.clear()
            
            logger.info("Stopped memory optimization services")
            
    def _periodic_cleanup(self) -> None:
        """Periodically clean up memory."""
        while self.cleanup_scheduled:
            # Sleep for a while
            time.sleep(60)  # 1 minute
            
            # Skip if cleanup is no longer scheduled
            if not self.cleanup_scheduled:
                break
                
            try:
                # Clean up resources
                cleaned = self.resource_tracker.cleanup_resources()
                
                # Force garbage collection if resources were cleaned
                if cleaned:
                    logger.debug(f"Cleaned resources: {cleaned}")
                    gc.collect()
                    
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
                
    def optimize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Optimize an image for memory usage.
        
        Args:
            image: Input image
            
        Returns:
            Optimized image
        """
        # Check if image needs optimizing
        if image is None:
            return None
            
        # Determine image size in MB
        image_size_mb = image.nbytes / (1024 * 1024)
        
        # Only optimize larger images
        if image_size_mb < 1.0:
            return image
            
        try:
            # Create optimized copy
            height, width = image.shape[:2]
            channels = image.shape[2] if len(image.shape) > 2 else 1
            
            # Get image from buffer
            optimized = self.image_buffer.get(height, width, channels)
            
            # Copy data
            np.copyto(optimized, image)
            
            # Track resource for cleanup
            self.resource_tracker.track(optimized, 'optimized_image')
            
            return optimized
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            return image
            
    def release_image(self, image: np.ndarray) -> None:
        """
        Release an image back to the buffer when done with it.
        
        Args:
            image: Image to release
        """
        if image is None:
            return
            
        try:
            self.image_buffer.put(image)
        except Exception as e:
            logger.error(f"Error releasing image: {e}")
            
    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        Get statistics about memory optimization.
        
        Returns:
            Dictionary with optimization statistics
        """
        stats = {
            'resources': self.resource_tracker.get_stats(),
            'image_buffer': self.image_buffer.get_stats(),
            'memory': {}
        }
        
        # Get current memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        stats['memory']['rss_mb'] = memory_info.rss / (1024 * 1024)
        stats['memory']['vms_mb'] = memory_info.vms / (1024 * 1024)
        
        # Get memory trend
        trend = self.monitor.get_memory_trend(minutes=5)
        stats['memory']['trend'] = trend
        
        return stats


# Create global optimizer instance
memory_optimizer = MemoryOptimizer() 