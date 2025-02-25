"""
Caching Utilities

This module provides caching utilities for the Scout application to optimize
performance by storing and retrieving previously computed results, particularly
for expensive operations like image detection and processing.
"""

import os
import time
import pickle
import hashlib
import logging
from typing import Any, Dict, List, Tuple, Optional, Callable, Union
import functools
import cv2
import numpy as np
from datetime import datetime, timedelta
from collections import OrderedDict
import threading

# Set up logging
logger = logging.getLogger(__name__)

class LRUCache:
    """
    Least Recently Used (LRU) cache implementation.
    
    This cache evicts the least recently used items when it reaches its capacity.
    Thread-safe implementation using locks.
    """
    
    def __init__(self, capacity: int = 100):
        """
        Initialize LRU cache with specified capacity.
        
        Args:
            capacity: Maximum number of items to store in the cache
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        
    def get(self, key: str) -> Any:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            The cached value or None if not found
        """
        with self.lock:
            if key in self.cache:
                # Move to end (mark as recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None
            
    def put(self, key: str, value: Any) -> None:
        """
        Add an item to the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            if key in self.cache:
                # Remove existing entry
                self.cache.pop(key)
                
            # Add to end (mark as recently used)
            self.cache[key] = value
            
            # Check if we exceeded capacity
            if len(self.cache) > self.capacity:
                # Remove least recently used item (first item)
                self.cache.popitem(last=False)
                
    def clear(self) -> None:
        """Clear all items from the cache."""
        with self.lock:
            self.cache.clear()
            
    def remove(self, key: str) -> bool:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if the key was found and removed, False otherwise
        """
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
                return True
            return False
            
    def __len__(self) -> int:
        """Return the number of items in the cache."""
        with self.lock:
            return len(self.cache)
            
    def __contains__(self, key: str) -> bool:
        """Check if key exists in the cache."""
        with self.lock:
            return key in self.cache
            
    def keys(self) -> List[str]:
        """Return a list of all keys in the cache."""
        with self.lock:
            return list(self.cache.keys())


class ImageHashCache:
    """
    Cache for image detection results using perceptual hashing.
    
    This cache stores detection results keyed by a perceptual hash of the input image,
    allowing for retrieval of results even when the images are slightly different.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, threshold: float = 0.9, 
                capacity: int = 100, hash_size: int = 8):
        """
        Initialize the image hash cache.
        
        Args:
            cache_dir: Directory to store persistent cache files (optional)
            threshold: Similarity threshold for hash matching (0.0-1.0)
            capacity: Maximum number of items in the in-memory cache
            hash_size: Size of the perceptual hash (larger = more detailed)
        """
        self.threshold = threshold
        self.hash_size = hash_size
        self.memory_cache = LRUCache(capacity)
        self.cache_dir = cache_dir
        
        # Create cache directory if specified and doesn't exist
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Created cache directory: {self.cache_dir}")
            
    def _compute_image_hash(self, image: np.ndarray) -> str:
        """
        Compute a perceptual hash for an image.
        
        Args:
            image: Image as numpy array
            
        Returns:
            Hash string
        """
        # Convert to grayscale if color image
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Resize to small square
        resized = cv2.resize(gray, (self.hash_size + 1, self.hash_size + 1))
        
        # Compute difference hash (dHash)
        diff = resized[:, 1:] > resized[:, :-1]
        
        # Convert to hex string
        return ''.join(str(int(x)) for x in diff.flatten())
        
    def _hash_similarity(self, hash1: str, hash2: str) -> float:
        """
        Compute similarity between two hashes.
        
        Args:
            hash1: First hash string
            hash2: Second hash string
            
        Returns:
            Similarity as a value between 0.0 and 1.0
        """
        if len(hash1) != len(hash2):
            return 0.0
            
        # Count matching bits
        matches = sum(h1 == h2 for h1, h2 in zip(hash1, hash2))
        return matches / len(hash1)
        
    def _get_persistent_cache_path(self, image_hash: str) -> str:
        """
        Get the file path for a persistent cache entry.
        
        Args:
            image_hash: Hash string for the image
            
        Returns:
            File path for the cache entry
        """
        if not self.cache_dir:
            return None
            
        # Use first few characters as subdirectory to avoid too many files in one dir
        prefix = image_hash[:4]
        subdir = os.path.join(self.cache_dir, prefix)
        os.makedirs(subdir, exist_ok=True)
        
        return os.path.join(subdir, f"{image_hash}.cache")
        
    def get(self, image: np.ndarray) -> Optional[Dict]:
        """
        Get cached detection results for an image.
        
        Args:
            image: Input image
            
        Returns:
            Cached detection results or None if not found
        """
        # Compute hash for the image
        image_hash = self._compute_image_hash(image)
        
        # First check memory cache for exact match
        result = self.memory_cache.get(image_hash)
        if result:
            logger.debug(f"Cache hit (memory): {image_hash}")
            return result
            
        # Check for similar hash in memory cache
        for cached_hash in self.memory_cache.keys():
            similarity = self._hash_similarity(image_hash, cached_hash)
            if similarity >= self.threshold:
                result = self.memory_cache.get(cached_hash)
                logger.debug(f"Cache hit (similar, memory): {cached_hash} ({similarity:.2f})")
                return result
                
        # If not in memory, check persistent cache if available
        if self.cache_dir:
            try:
                # Check for exact match in persistent cache
                cache_path = self._get_persistent_cache_path(image_hash)
                if os.path.exists(cache_path):
                    with open(cache_path, 'rb') as f:
                        result = pickle.load(f)
                    
                    # Add to memory cache
                    self.memory_cache.put(image_hash, result)
                    logger.debug(f"Cache hit (persistent): {image_hash}")
                    return result
                    
                # Check for similar hash in persistent cache
                prefix_dir = os.path.join(self.cache_dir, image_hash[:4])
                if os.path.exists(prefix_dir):
                    for filename in os.listdir(prefix_dir):
                        if filename.endswith('.cache'):
                            cached_hash = filename[:-6]  # Remove .cache extension
                            similarity = self._hash_similarity(image_hash, cached_hash)
                            if similarity >= self.threshold:
                                cache_path = os.path.join(prefix_dir, filename)
                                with open(cache_path, 'rb') as f:
                                    result = pickle.load(f)
                                
                                # Add to memory cache
                                self.memory_cache.put(image_hash, result)
                                logger.debug(f"Cache hit (similar, persistent): {cached_hash} ({similarity:.2f})")
                                return result
            except Exception as e:
                logger.warning(f"Error reading from persistent cache: {str(e)}")
                
        # Cache miss
        logger.debug(f"Cache miss: {image_hash}")
        return None
        
    def put(self, image: np.ndarray, result: Dict) -> None:
        """
        Store detection results for an image.
        
        Args:
            image: Input image
            result: Detection results to cache
        """
        # Compute hash for the image
        image_hash = self._compute_image_hash(image)
        
        # Store in memory cache
        self.memory_cache.put(image_hash, result)
        
        # Store in persistent cache if available
        if self.cache_dir:
            try:
                cache_path = self._get_persistent_cache_path(image_hash)
                with open(cache_path, 'wb') as f:
                    pickle.dump(result, f)
                logger.debug(f"Cached to persistent storage: {image_hash}")
            except Exception as e:
                logger.warning(f"Error writing to persistent cache: {str(e)}")
                
    def clear(self) -> None:
        """Clear all items from the cache."""
        self.memory_cache.clear()
        
        # Clear persistent cache if available
        if self.cache_dir and os.path.exists(self.cache_dir):
            try:
                for root, dirs, files in os.walk(self.cache_dir, topdown=False):
                    for name in files:
                        if name.endswith('.cache'):
                            os.remove(os.path.join(root, name))
                    for name in dirs:
                        dir_path = os.path.join(root, name)
                        if not os.listdir(dir_path):  # Only remove if empty
                            os.rmdir(dir_path)
                logger.info("Cleared persistent cache")
            except Exception as e:
                logger.warning(f"Error clearing persistent cache: {str(e)}")


class DetectionCache:
    """
    Specialized cache for detection results, optimized for different detection strategies.
    
    This cache stores detection results by strategy type, parameters, and input image,
    allowing for efficient retrieval of previous detection results.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, 
                memory_capacity: int = 50, 
                expiration: Optional[timedelta] = timedelta(hours=24)):
        """
        Initialize the detection cache.
        
        Args:
            cache_dir: Directory to store persistent cache files (optional)
            memory_capacity: Maximum number of items in the in-memory cache
            expiration: Time after which cached results expire (None for no expiration)
        """
        self.cache_dir = cache_dir
        self.expiration = expiration
        
        # Create cache for each strategy type
        self.image_caches = {
            'template': ImageHashCache(
                cache_dir=os.path.join(cache_dir, 'template') if cache_dir else None,
                capacity=memory_capacity
            ),
            'ocr': ImageHashCache(
                cache_dir=os.path.join(cache_dir, 'ocr') if cache_dir else None,
                capacity=memory_capacity
            ),
            'yolo': ImageHashCache(
                cache_dir=os.path.join(cache_dir, 'yolo') if cache_dir else None,
                capacity=memory_capacity
            )
        }
        
        # Create cache directory if specified and doesn't exist
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Created detection cache directory: {self.cache_dir}")
            
    def _get_cache_key(self, strategy_type: str, params: Dict) -> str:
        """
        Generate a cache key from strategy type and parameters.
        
        Args:
            strategy_type: Type of detection strategy
            params: Detection parameters
            
        Returns:
            Cache key string
        """
        # Sort params to ensure consistent key
        param_str = str(sorted((k, str(v)) for k, v in params.items()))
        return f"{strategy_type}_{hashlib.md5(param_str.encode()).hexdigest()}"
        
    def get(self, strategy_type: str, image: np.ndarray, params: Dict) -> Optional[Dict]:
        """
        Get cached detection results.
        
        Args:
            strategy_type: Type of detection strategy (template, ocr, yolo)
            image: Input image
            params: Detection parameters
            
        Returns:
            Cached detection results or None if not found
        """
        if strategy_type not in self.image_caches:
            logger.warning(f"Unsupported strategy type for caching: {strategy_type}")
            return None
            
        # Get image cache for this strategy
        image_cache = self.image_caches[strategy_type]
        
        # Check for cached result
        cached_result = image_cache.get(image)
        if cached_result:
            # Extract results for the specific parameters
            cache_key = self._get_cache_key(strategy_type, params)
            if cache_key in cached_result:
                result_entry = cached_result[cache_key]
                
                # Check if expired
                if self.expiration:
                    timestamp = result_entry.get('timestamp', 0)
                    if time.time() - timestamp > self.expiration.total_seconds():
                        logger.debug(f"Cached result expired: {cache_key}")
                        return None
                        
                logger.debug(f"Cache hit for {strategy_type} detection with params: {params}")
                return result_entry.get('result')
                
        return None
        
    def put(self, strategy_type: str, image: np.ndarray, params: Dict, result: Any) -> None:
        """
        Store detection results in cache.
        
        Args:
            strategy_type: Type of detection strategy (template, ocr, yolo)
            image: Input image
            params: Detection parameters
            result: Detection results to cache
        """
        if strategy_type not in self.image_caches:
            logger.warning(f"Unsupported strategy type for caching: {strategy_type}")
            return
            
        # Get image cache for this strategy
        image_cache = self.image_caches[strategy_type]
        
        # Get existing cached results for this image or create new entry
        cached_result = image_cache.get(image) or {}
        
        # Store results for the specific parameters
        cache_key = self._get_cache_key(strategy_type, params)
        cached_result[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Update cache
        image_cache.put(image, cached_result)
        logger.debug(f"Cached {strategy_type} detection result with params: {params}")
        
    def clear(self, strategy_type: Optional[str] = None) -> None:
        """
        Clear cache items.
        
        Args:
            strategy_type: Type of detection strategy to clear (None for all)
        """
        if strategy_type:
            if strategy_type in self.image_caches:
                self.image_caches[strategy_type].clear()
                logger.info(f"Cleared {strategy_type} detection cache")
            else:
                logger.warning(f"Unsupported strategy type for cache clearing: {strategy_type}")
        else:
            # Clear all caches
            for cache_type, cache in self.image_caches.items():
                cache.clear()
            logger.info("Cleared all detection caches")


def cached(cache_instance, key_func=None, expiration=None):
    """
    Decorator for caching function results.
    
    Args:
        cache_instance: Instance of a cache (LRUCache or similar)
        key_func: Function to generate cache key from function arguments
                 (None to use default key generation)
        expiration: Optional expiration time in seconds
                  
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend([str(arg) for arg in args])
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                key = '_'.join(key_parts)
                
            # Try to get from cache
            cached_result = cache_instance.get(key)
            if cached_result is not None:
                # Check expiration if specified
                if expiration:
                    timestamp = cached_result.get('timestamp', 0)
                    if time.time() - timestamp > expiration:
                        logger.debug(f"Cached result expired: {key}")
                    else:
                        logger.debug(f"Cache hit: {key}")
                        return cached_result.get('result')
                else:
                    logger.debug(f"Cache hit: {key}")
                    return cached_result.get('result')
                    
            # Cache miss - compute result
            logger.debug(f"Cache miss: {key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_instance.put(key, {
                'result': result,
                'timestamp': time.time()
            })
            
            return result
        return wrapper
    return decorator


class CacheManager:
    """
    Manager for different cache instances in the application.
    
    This provides a central access point for all caching functionality.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, enable_persistent: bool = True):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Base directory for persistent caches
            enable_persistent: Whether to use persistent caching
        """
        self.cache_dir = cache_dir if enable_persistent else None
        
        # Create base cache directory if needed
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Created base cache directory: {self.cache_dir}")
            
        # Initialize caches
        self.detection_cache = DetectionCache(
            cache_dir=os.path.join(self.cache_dir, 'detection') if self.cache_dir else None
        )
        
        self.result_cache = LRUCache(200)  # General-purpose cache
        
    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.detection_cache.clear()
        self.result_cache.clear()
        logger.info("Cleared all caches")
        
    def get_cache_size(self) -> Dict[str, int]:
        """
        Get the current size of all caches.
        
        Returns:
            Dictionary with cache sizes
        """
        result = {'result_cache': len(self.result_cache)}
        
        # Calculate size of persistent cache if available
        if self.cache_dir and os.path.exists(self.cache_dir):
            total_size = 0
            cache_file_count = 0
            
            for root, _, files in os.walk(self.cache_dir):
                for file in files:
                    if file.endswith('.cache'):
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                        cache_file_count += 1
                        
            result['persistent_size_bytes'] = total_size
            result['persistent_file_count'] = cache_file_count
            
        return result


# Create global cache manager instance
cache_manager = CacheManager(
    cache_dir=os.path.join(os.path.expanduser('~'), '.scout', 'cache'),
    enable_persistent=True
) 