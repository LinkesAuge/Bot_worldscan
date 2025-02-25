"""
Detection Performance Benchmarks

This module provides benchmarks for testing the performance of
detection-related components in the Scout application.
"""

import os
import sys
import tempfile
import numpy as np
import cv2
from pathlib import Path
from typing import Optional

# Add parent directory to path to allow running from script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from scout.tests.performance.benchmark_runner import BenchmarkSuite


def create_test_image(width: int = 1920, height: int = 1080) -> np.ndarray:
    """
    Create a test image for benchmarking.
    
    Args:
        width: Image width
        height: Image height
        
    Returns:
        Image as numpy array
    """
    # Create a blank image
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add some patterns for testing
    # Gradient background
    for y in range(height):
        for x in range(width):
            img[y, x] = [
                int(255 * x / width),
                int(255 * y / height),
                int(255 * (x + y) / (width + height))
            ]
    
    # Add some shapes
    # Rectangle
    cv2.rectangle(img, (100, 100), (400, 300), (0, 255, 0), 2)
    
    # Circle
    cv2.circle(img, (600, 200), 100, (0, 0, 255), 2)
    
    # Text
    cv2.putText(img, "Scout Benchmark", (800, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return img


def create_test_template(img: np.ndarray, x: int, y: int, width: int, height: int) -> np.ndarray:
    """
    Create a template from part of a test image.
    
    Args:
        img: Source image
        x, y: Top-left corner coordinates
        width, height: Template dimensions
        
    Returns:
        Template image
    """
    return img[y:y+height, x:x+width].copy()


def benchmark_template_matching(image: np.ndarray, template: np.ndarray, method: int = cv2.TM_CCOEFF_NORMED) -> None:
    """
    Benchmark the template matching performance.
    
    Args:
        image: Image to search in
        template: Template to search for
        method: Template matching method
    """
    result = cv2.matchTemplate(image, template, method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)


def benchmark_ocr_preprocessing(image: np.ndarray) -> None:
    """
    Benchmark the OCR preprocessing performance.
    
    Args:
        image: Image to preprocess
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Apply morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(opening, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


def benchmark_template_matching_strategy() -> None:
    """Benchmark the template matching strategy with realistic parameters."""
    try:
        # Import strategy here to avoid circular dependencies
        from scout.core.detection.strategies.template_strategy import TemplateStrategy
        
        # Create test image and template
        image = create_test_image(1920, 1080)
        template = create_test_template(image, 800, 150, 200, 100)
        
        # Create temporary files for the image and template
        with tempfile.NamedTemporaryFile(suffix=".png") as img_file, \
             tempfile.NamedTemporaryFile(suffix=".png") as template_file:
            
            # Save the images
            cv2.imwrite(img_file.name, image)
            cv2.imwrite(template_file.name, template)
            
            # Create strategy
            strategy = TemplateStrategy()
            
            # Run detection
            result = strategy.detect(img_file.name, {
                "templates": [template_file.name],
                "threshold": 0.8,
                "region": None,
                "limit": 10,
                "visualize": False
            })
    except ImportError:
        # Handle missing dependencies
        pass


def benchmark_edge_detection(image: np.ndarray) -> None:
    """
    Benchmark edge detection algorithms.
    
    Args:
        image: Image to process
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Canny edge detection
    edges = cv2.Canny(blurred, 50, 150)


def benchmark_resize_operations(image: np.ndarray) -> None:
    """
    Benchmark image resize operations.
    
    Args:
        image: Image to resize
    """
    # Various resize operations
    cv2.resize(image, (960, 540), interpolation=cv2.INTER_LINEAR)
    cv2.resize(image, (640, 360), interpolation=cv2.INTER_AREA)
    cv2.resize(image, (320, 180), interpolation=cv2.INTER_NEAREST)


def benchmark_contour_analysis(image: np.ndarray) -> None:
    """
    Benchmark contour analysis operations.
    
    Args:
        image: Image to analyze
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Analyze each contour
    for cnt in contours:
        # Calculate contour area
        area = cv2.contourArea(cnt)
        
        # Calculate perimeter
        perimeter = cv2.arcLength(cnt, True)
        
        # Find bounding rectangle
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Find minimum area rectangle
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)


def create_detection_benchmark_suite(iterations: int = 5, profile: bool = False) -> BenchmarkSuite:
    """
    Create a benchmark suite for detection components.
    
    Args:
        iterations: Number of iterations for each benchmark
        profile: Whether to enable profiling
        
    Returns:
        Benchmark suite
    """
    suite = BenchmarkSuite(
        name="Detection Performance",
        description="Benchmarks for detection-related components"
    )
    
    # Create test data
    image = create_test_image(1920, 1080)
    template = create_test_template(image, 800, 150, 200, 100)
    
    # Add benchmarks
    suite.add_benchmark(
        name="Template Matching",
        func=benchmark_template_matching,
        iterations=iterations,
        profile=profile,
        args=[image, template]
    )
    
    suite.add_benchmark(
        name="OCR Preprocessing",
        func=benchmark_ocr_preprocessing,
        iterations=iterations,
        profile=profile,
        args=[image]
    )
    
    suite.add_benchmark(
        name="Edge Detection",
        func=benchmark_edge_detection,
        iterations=iterations,
        profile=profile,
        args=[image]
    )
    
    suite.add_benchmark(
        name="Resize Operations",
        func=benchmark_resize_operations,
        iterations=iterations,
        profile=profile,
        args=[image]
    )
    
    suite.add_benchmark(
        name="Contour Analysis",
        func=benchmark_contour_analysis,
        iterations=iterations,
        profile=profile,
        args=[image]
    )
    
    suite.add_benchmark(
        name="Template Matching Strategy",
        func=benchmark_template_matching_strategy,
        iterations=iterations,
        profile=profile
    )
    
    return suite


if __name__ == "__main__":
    # Run this file directly to execute just the detection benchmarks
    suite = create_detection_benchmark_suite(iterations=3, profile=True)
    results = suite.run()
    
    # Print results
    for result in results:
        print(f"{result.name}: {result.execution_time:.6f}s (avg: {result.avg_execution_time:.6f}s)") 