"""
Parallel Processing Utilities

This module provides utilities for parallel processing in the Scout application,
enabling efficient distribution of computational tasks across multiple cores.
It includes tools for parallel execution of image processing tasks, detection
operations, and general parallel workloads.
"""

import os
import time
import logging
import threading
import queue
import concurrent.futures
from typing import Any, Dict, List, Tuple, Callable, TypeVar, Generic, Optional, Iterator
import multiprocessing
import numpy as np
import cv2

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')
R = TypeVar('R')

class ParallelExecutor:
    """
    Utility for executing tasks in parallel using thread or process pools.
    
    Provides methods for:
    - Running multiple tasks in parallel
    - Distributing work across multiple cores
    - Managing thread/process pools
    - Collecting and aggregating results
    """
    
    def __init__(self, max_workers: Optional[int] = None, use_processes: bool = False):
        """
        Initialize the parallel executor.
        
        Args:
            max_workers: Maximum number of worker threads/processes (None for auto)
            use_processes: Whether to use processes instead of threads
        """
        # Auto-detect number of workers if not specified
        if max_workers is None:
            max_workers = multiprocessing.cpu_count()
            # Reserve one core for UI and other operations
            if max_workers > 2:
                max_workers -= 1
                
        self.max_workers = max_workers
        self.use_processes = use_processes
        logger.debug(f"Initialized ParallelExecutor with {max_workers} workers "
                    f"using {'processes' if use_processes else 'threads'}")
        
    def map(self, func: Callable[[T], R], items: List[T], 
           timeout: Optional[float] = None) -> List[R]:
        """
        Apply a function to each item in parallel.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            timeout: Maximum time to wait for completion (None for no timeout)
            
        Returns:
            List of results in the same order as input items
        """
        executor_class = (concurrent.futures.ProcessPoolExecutor if self.use_processes
                        else concurrent.futures.ThreadPoolExecutor)
        
        if not items:
            return []
            
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(func, item): i for i, item in enumerate(items)
            }
            
            # Collect results in order
            results = [None] * len(items)
            
            for future in concurrent.futures.as_completed(future_to_index, timeout=timeout):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as exc:
                    logger.error(f"Task {index} generated an exception: {exc}")
                    results[index] = None
                    
        return results
        
    def execute_with_progress(self, func: Callable[[T], R], items: List[T],
                             progress_callback: Optional[Callable[[int, int], None]] = None,
                             timeout: Optional[float] = None) -> List[R]:
        """
        Execute tasks in parallel with progress reporting.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            progress_callback: Function to call with progress updates (completed, total)
            timeout: Maximum time to wait for completion (None for no timeout)
            
        Returns:
            List of results in the same order as input items
        """
        executor_class = (concurrent.futures.ProcessPoolExecutor if self.use_processes
                        else concurrent.futures.ThreadPoolExecutor)
        
        if not items:
            return []
            
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(func, item): i for i, item in enumerate(items)
            }
            
            # Collect results in order
            results = [None] * len(items)
            completed = 0
            total = len(items)
            
            # Report initial progress
            if progress_callback:
                progress_callback(completed, total)
                
            for future in concurrent.futures.as_completed(future_to_index, timeout=timeout):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as exc:
                    logger.error(f"Task {index} generated an exception: {exc}")
                    results[index] = None
                    
                # Update progress
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                    
        return results
        
    def parallel_for(self, func: Callable[[int], R], start: int, end: int, 
                    chunk_size: Optional[int] = None) -> List[R]:
        """
        Execute a for-loop in parallel.
        
        Args:
            func: Function to apply to each index
            start: Start index (inclusive)
            end: End index (exclusive)
            chunk_size: Size of chunks to process at once (None for auto)
            
        Returns:
            List of results in the same order as the loop iterations
        """
        # Calculate range size
        size = end - start
        
        # Auto-determine chunk size if not specified
        if chunk_size is None:
            chunk_size = max(1, size // (self.max_workers * 4))
            
        # Create chunks
        chunks = []
        for i in range(start, end, chunk_size):
            chunk_end = min(i + chunk_size, end)
            chunks.append((i, chunk_end))
            
        # Process chunks in parallel
        def process_chunk(chunk_range: Tuple[int, int]) -> List[R]:
            chunk_start, chunk_end = chunk_range
            return [func(i) for i in range(chunk_start, chunk_end)]
            
        # Flatten results
        chunk_results = self.map(process_chunk, chunks)
        results = []
        for chunk in chunk_results:
            results.extend(chunk)
            
        return results


class ImageProcessor:
    """
    Utility for parallel image processing operations.
    
    Provides methods for:
    - Dividing images into tiles for parallel processing
    - Applying functions to image regions in parallel
    - Recombining processed tiles into a complete image
    """
    
    def __init__(self, executor: Optional[ParallelExecutor] = None):
        """
        Initialize the image processor.
        
        Args:
            executor: ParallelExecutor instance (None to create new one)
        """
        self.executor = executor or ParallelExecutor()
        
    def _split_image_into_tiles(self, image: np.ndarray, tile_size: int, 
                               overlap: int = 0) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Split an image into overlapping tiles.
        
        Args:
            image: Input image
            tile_size: Size of tiles (height=width)
            overlap: Overlap between adjacent tiles
            
        Returns:
            List of (tile_image, (x, y, width, height)) tuples
        """
        height, width = image.shape[:2]
        tiles = []
        
        # Calculate effective step size
        step = tile_size - overlap
        
        for y in range(0, height, step):
            for x in range(0, width, step):
                # Calculate tile bounds with overlap
                x1 = x
                y1 = y
                x2 = min(x + tile_size, width)
                y2 = min(y + tile_size, height)
                
                # Handle edge tiles
                if x2 - x1 < tile_size and x > 0:
                    x1 = max(0, x2 - tile_size)
                if y2 - y1 < tile_size and y > 0:
                    y1 = max(0, y2 - tile_size)
                    
                # Extract tile
                tile = image[y1:y2, x1:x2].copy()
                tile_info = (x1, y1, x2 - x1, y2 - y1)
                tiles.append((tile, tile_info))
                
        return tiles
        
    def _recombine_tiles(self, tiles: List[Tuple[np.ndarray, Tuple[int, int, int, int]]], 
                        original_shape: Tuple[int, int, int]) -> np.ndarray:
        """
        Recombine processed tiles into a single image.
        
        Args:
            tiles: List of (processed_tile, (x, y, width, height)) tuples
            original_shape: Shape of the original image (height, width, channels)
            
        Returns:
            Recombined image
        """
        # Create empty result image
        result = np.zeros(original_shape, dtype=np.uint8)
        
        # Place each tile in the result
        for tile, (x, y, w, h) in tiles:
            # Ensure tile matches target region size
            if tile.shape[:2] != (h, w):
                tile = cv2.resize(tile, (w, h))
                
            result[y:y+h, x:x+w] = tile
            
        return result
        
    def process_image_in_tiles(self, image: np.ndarray, 
                              process_func: Callable[[np.ndarray], np.ndarray],
                              tile_size: int = 256, 
                              overlap: int = 0) -> np.ndarray:
        """
        Process an image in parallel by dividing it into tiles.
        
        Args:
            image: Input image
            process_func: Function to apply to each tile
            tile_size: Size of tiles
            overlap: Overlap between adjacent tiles
            
        Returns:
            Processed image
        """
        # Split image into tiles
        tiles = self._split_image_into_tiles(image, tile_size, overlap)
        
        # Define function to process a tile
        def process_tile(item: Tuple[np.ndarray, Tuple[int, int, int, int]]) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
            tile, tile_info = item
            processed_tile = process_func(tile)
            return processed_tile, tile_info
            
        # Process tiles in parallel
        processed_tiles = self.executor.map(process_tile, tiles)
        
        # Recombine processed tiles
        return self._recombine_tiles(processed_tiles, image.shape)
        
    def apply_detection_in_tiles(self, image: np.ndarray,
                               detect_func: Callable[[np.ndarray], List[Dict]],
                               tile_size: int = 400,
                               overlap: int = 50,
                               min_distance: int = 20) -> List[Dict]:
        """
        Apply detection in parallel by dividing image into tiles.
        
        Args:
            image: Input image
            detect_func: Detection function that returns list of detections
            tile_size: Size of tiles
            overlap: Overlap between adjacent tiles
            min_distance: Minimum distance for duplicate removal
            
        Returns:
            Combined list of detections with duplicates removed
        """
        # Split image into tiles
        tiles = self._split_image_into_tiles(image, tile_size, overlap)
        
        # Define function to process a tile
        def process_tile(item: Tuple[np.ndarray, Tuple[int, int, int, int]]) -> List[Dict]:
            tile, (x, y, w, h) = item
            
            # Run detection on tile
            detections = detect_func(tile)
            
            # Adjust coordinates to global image space
            for detection in detections:
                if 'x' in detection and 'y' in detection:
                    detection['x'] += x
                    detection['y'] += y
                elif 'bbox' in detection:
                    # Adjust bounding box [x, y, width, height]
                    detection['bbox'][0] += x
                    detection['bbox'][1] += y
                    
            return detections
            
        # Process tiles in parallel
        tile_results = self.executor.map(process_tile, tiles)
        
        # Flatten results
        all_detections = []
        for detections in tile_results:
            all_detections.extend(detections)
            
        # Remove duplicates
        return self._remove_duplicate_detections(all_detections, min_distance)
        
    def _remove_duplicate_detections(self, detections: List[Dict], 
                                   min_distance: int) -> List[Dict]:
        """
        Remove duplicate detections based on distance.
        
        Args:
            detections: List of detection results
            min_distance: Minimum distance to consider detections as duplicates
            
        Returns:
            List of detections with duplicates removed
        """
        if not detections:
            return []
            
        # Sort by confidence (higher first) if available
        if 'confidence' in detections[0]:
            detections = sorted(detections, key=lambda d: d.get('confidence', 0), reverse=True)
            
        # Initialize result with the first detection
        result = [detections[0]]
        
        # Check each detection against the result
        for detection in detections[1:]:
            # Get center point of detection
            if 'x' in detection and 'y' in detection:
                x1, y1 = detection['x'], detection['y']
                
                # Check if this is a duplicate of any detection in result
                is_duplicate = False
                for kept in result:
                    if 'x' in kept and 'y' in kept:
                        x2, y2 = kept['x'], kept['y']
                        
                        # Calculate distance
                        distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                        
                        if distance < min_distance:
                            is_duplicate = True
                            break
                            
                if not is_duplicate:
                    result.append(detection)
            else:
                # Can't determine duplicates without coordinates, just add it
                result.append(detection)
                
        return result


class WorkQueue(Generic[T]):
    """
    Thread-safe work queue for distributing tasks to worker threads.
    
    Provides methods for:
    - Adding tasks to the queue
    - Processing tasks in worker threads
    - Collecting results
    """
    
    def __init__(self, num_workers: int = 4):
        """
        Initialize the work queue.
        
        Args:
            num_workers: Number of worker threads
        """
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.num_workers = num_workers
        self.stop_event = threading.Event()
        
    def start(self, worker_func: Callable[[T], Any]):
        """
        Start worker threads.
        
        Args:
            worker_func: Function to process each task
        """
        # Create and start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(worker_func, i),
                daemon=True
            )
            self.workers.append(worker)
            worker.start()
            
        logger.debug(f"Started {self.num_workers} worker threads")
        
    def _worker_loop(self, worker_func: Callable[[T], Any], worker_id: int):
        """
        Main worker thread loop.
        
        Args:
            worker_func: Function to process each task
            worker_id: ID of this worker thread
        """
        while not self.stop_event.is_set():
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=0.5)
                
                # Process task
                try:
                    task_id, item = task
                    result = worker_func(item)
                    self.result_queue.put((task_id, result, None))
                except Exception as e:
                    # Log and pass on the exception
                    logger.error(f"Worker {worker_id} error: {str(e)}")
                    self.result_queue.put((task_id, None, e))
                finally:
                    self.task_queue.task_done()
                    
            except queue.Empty:
                # Queue is empty, just continue
                continue
                
    def add_task(self, task_id: int, item: T):
        """
        Add a task to the queue.
        
        Args:
            task_id: Unique task ID
            item: Task data
        """
        self.task_queue.put((task_id, item))
        
    def get_result(self, block: bool = True, timeout: Optional[float] = None) -> Tuple[int, Any, Optional[Exception]]:
        """
        Get a result from the result queue.
        
        Args:
            block: Whether to block if queue is empty
            timeout: Maximum time to wait
            
        Returns:
            Tuple of (task_id, result, exception)
        """
        return self.result_queue.get(block=block, timeout=timeout)
        
    def stop(self):
        """Stop all worker threads."""
        # Signal threads to stop
        self.stop_event.set()
        
        # Wait for all threads to complete
        for worker in self.workers:
            worker.join()
            
        logger.debug("All worker threads stopped")
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def parallel_map(func: Callable[[T], R], items: List[T], 
               max_workers: Optional[int] = None, 
               use_processes: bool = False) -> List[R]:
    """
    Convenience function for parallel mapping.
    
    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of workers (None for auto)
        use_processes: Whether to use processes instead of threads
        
    Returns:
        List of results
    """
    executor = ParallelExecutor(max_workers=max_workers, use_processes=use_processes)
    return executor.map(func, items)


def split_workload(total_items: int, num_parts: int) -> List[Tuple[int, int]]:
    """
    Split a workload into approximately equal parts.
    
    Args:
        total_items: Total number of items
        num_parts: Number of parts to split into
        
    Returns:
        List of (start, end) index pairs
    """
    if total_items <= 0:
        return []
        
    # Ensure num_parts is not larger than total_items
    num_parts = min(num_parts, total_items)
    
    # Calculate base items per part
    base_per_part = total_items // num_parts
    
    # Calculate remainder
    remainder = total_items % num_parts
    
    # Distribute remainder across parts
    parts = []
    start = 0
    
    for i in range(num_parts):
        # Add one to this part's size if there's remainder left
        extra = 1 if i < remainder else 0
        items_in_part = base_per_part + extra
        
        end = start + items_in_part
        parts.append((start, end))
        start = end
        
    return parts


# Create global executor instance
default_executor = ParallelExecutor()

# Create global image processor instance
image_processor = ImageProcessor(default_executor) 