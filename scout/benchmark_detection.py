#!/usr/bin/env python
"""
Detection System Benchmark Script

This script benchmarks the performance of the Scout detection system
with and without optimization features enabled.
"""

import os
import sys
import argparse
import logging
import time
import cv2
import numpy as np
from pathlib import Path

# Add parent directory to path to import scout modules
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from scout.core.events.event_bus import EventBus
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy
from scout.core.detection.strategies.ocr_strategy import OCRStrategy
from scout.core.utils.benchmark import benchmark_manager
from scout.core.utils.caching import cache_manager
from scout.core.utils.memory import memory_optimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("benchmark")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Benchmark detection system performance")
    parser.add_argument(
        "-i", "--image", 
        type=str, 
        help="Path to test image (will use a generated image if not provided)"
    )
    parser.add_argument(
        "-t", "--templates_dir", 
        type=str,
        default="data/templates",
        help="Path to templates directory"
    )
    parser.add_argument(
        "-o", "--output_dir", 
        type=str,
        default="benchmark_results",
        help="Directory to save benchmark results"
    )
    parser.add_argument(
        "-n", "--iterations", 
        type=int,
        default=10,
        help="Number of benchmark iterations"
    )
    parser.add_argument(
        "-w", "--warmup", 
        type=int,
        default=3,
        help="Number of warmup iterations"
    )
    parser.add_argument(
        "--strategies", 
        type=str,
        default="template,ocr,yolo",
        help="Comma-separated list of strategies to benchmark"
    )
    parser.add_argument(
        "--plot", 
        action="store_true",
        help="Generate and save plots"
    )
    
    return parser.parse_args()

def create_test_image(width=1024, height=768):
    """
    Create a test image with various patterns and shapes for benchmarking.
    
    Args:
        width: Image width
        height: Image height
        
    Returns:
        Test image as NumPy array
    """
    # Create base image
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add background texture
    for i in range(0, width, 20):
        for j in range(0, height, 20):
            color_variation = ((i + j) % 20) - 10
            color = [150 + color_variation, 150 + color_variation, 150 + color_variation]
            cv2.rectangle(image, (i, j), (i + 20, j + 20), color, -1)
    
    # Add some shapes
    # Circle
    cv2.circle(image, (width // 4, height // 4), 50, (255, 0, 0), -1)
    
    # Rectangle
    cv2.rectangle(image, (width // 2, height // 4), 
                 (width // 2 + 100, height // 4 + 80), (0, 255, 0), -1)
    
    # Triangle
    points = np.array([[3 * width // 4, height // 4], 
                      [3 * width // 4 - 50, height // 4 + 100], 
                      [3 * width // 4 + 50, height // 4 + 100]])
    cv2.fillPoly(image, [points], (0, 0, 255))
    
    # Add text
    cv2.putText(image, "Performance Test", (width // 4, height // 2),
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    cv2.putText(image, "Scout Detection", (width // 4, height // 2 + 50),
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    cv2.putText(image, "Benchmark: Template", (100, height - 100),
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 200, 0), 2)
    cv2.putText(image, "Benchmark: OCR", (width // 2, height - 100),
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)
    
    # Add repeating patterns for template matching
    pattern = np.zeros((30, 30, 3), dtype=np.uint8)
    pattern[:, :] = [200, 100, 50]  # Orange-brown
    cv2.rectangle(pattern, (5, 5), (25, 25), (240, 240, 240), -1)
    
    for i in range(5):
        x = np.random.randint(0, width - 30)
        y = np.random.randint(0, height - 30)
        image[y:y+30, x:x+30] = pattern.copy()
    
    return image

def create_test_templates(image, output_dir):
    """
    Create test templates from the test image.
    
    Args:
        image: Test image
        output_dir: Directory to save templates
    """
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create templates
    templates = [
        # Circle
        {"name": "circle", "x": image.shape[1] // 4 - 50, "y": image.shape[0] // 4 - 50, 
         "width": 100, "height": 100},
        # Rectangle
        {"name": "rectangle", "x": image.shape[1] // 2, "y": image.shape[0] // 4, 
         "width": 100, "height": 80},
        # Text
        {"name": "text_performance", "x": image.shape[1] // 4, "y": image.shape[0] // 2 - 30, 
         "width": 300, "height": 60},
        # Pattern
        {"name": "pattern", "x": 0, "y": 0, "width": 30, "height": 30}
    ]
    
    # Extract and save templates
    for template in templates:
        x, y = template["x"], template["y"]
        w, h = template["width"], template["height"]
        
        # Adjust if out of bounds
        if x < 0 or y < 0 or x + w > image.shape[1] or y + h > image.shape[0]:
            continue
            
        # Extract template
        template_img = image[y:y+h, x:x+w].copy()
        
        # Save template
        cv2.imwrite(os.path.join(output_dir, f"{template['name']}.png"), template_img)
        logger.info(f"Created template: {template['name']}.png")
    
    return templates

def run_benchmarks(args):
    """
    Run detection system benchmarks.
    
    Args:
        args: Command-line arguments
    """
    # Load or create test image
    if args.image and os.path.exists(args.image):
        logger.info(f"Loading test image from {args.image}")
        test_image = cv2.imread(args.image)
    else:
        logger.info("Creating test image")
        test_image = create_test_image()
        
        # Save the test image
        os.makedirs(args.output_dir, exist_ok=True)
        test_image_path = os.path.join(args.output_dir, "test_image.png")
        cv2.imwrite(test_image_path, test_image)
        logger.info(f"Saved test image to {test_image_path}")
    
    # Create templates directory if it doesn't exist
    os.makedirs(args.templates_dir, exist_ok=True)
    
    # Check if templates exist, create them if not
    if not any(Path(args.templates_dir).glob("*.png")):
        logger.info(f"No templates found in {args.templates_dir}, creating test templates")
        templates = create_test_templates(test_image, args.templates_dir)
    else:
        logger.info(f"Using existing templates in {args.templates_dir}")
        templates = [
            {"name": p.stem} 
            for p in Path(args.templates_dir).glob("*.png")
        ]
    
    # Initialize services
    event_bus = EventBus()
    window_service = WindowService(event_bus)
    detection_service = DetectionService(event_bus, window_service)
    
    # Register detection strategies
    template_strategy = TemplateMatchingStrategy(templates_dir=args.templates_dir)
    detection_service.register_strategy("template", template_strategy)
    
    try:
        ocr_strategy = OCRStrategy()
        detection_service.register_strategy("ocr", ocr_strategy)
        has_ocr = True
    except Exception as e:
        logger.warning(f"OCR strategy not available: {e}")
        has_ocr = False
    
    try:
        from scout.core.detection.strategies.yolo_strategy import YOLOStrategy
        yolo_strategy = YOLOStrategy(model_path=None)  # Uses a default model
        detection_service.register_strategy("yolo", yolo_strategy)
        has_yolo = True
    except Exception as e:
        logger.warning(f"YOLO strategy not available: {e}")
        has_yolo = False
    
    # Set up output directory
    benchmark_output_dir = os.path.join(args.output_dir, f"benchmark_{int(time.time())}")
    os.makedirs(benchmark_output_dir, exist_ok=True)
    
    # Configure benchmark manager to use the output directory
    benchmark_manager.results_dir = benchmark_output_dir
    
    # Set up context for detection
    detection_service.set_context({"window_title": "Benchmark"})
    
    # Define strategies to benchmark
    strategies_to_benchmark = args.strategies.split(",")
    
    # Prepare parameters for each strategy
    strategies = []
    params_list = []
    
    if "template" in strategies_to_benchmark:
        strategies.append("template")
        template_names = [t["name"] for t in templates]
        params_list.append({
            "template_name": template_names[0] if template_names else None,
            "confidence_threshold": 0.7,
            "max_results": 10
        })
    
    if "ocr" in strategies_to_benchmark and has_ocr:
        strategies.append("ocr")
        params_list.append({
            "pattern": None,
            "confidence_threshold": 0.6,
            "preprocess": None
        })
    
    if "yolo" in strategies_to_benchmark and has_yolo:
        strategies.append("yolo")
        params_list.append({
            "class_names": None,
            "confidence_threshold": 0.5,
            "nms_threshold": 0.5
        })
    
    # Mock window service to return our test image
    window_service.capture_screenshot = lambda: test_image
    window_service.find_window = lambda title: True
    
    # Run comparison benchmarks
    logger.info("Starting benchmark")
    results = benchmark_manager.compare_optimizations(
        detection_service=detection_service,
        image=test_image,
        strategies=strategies,
        params_list=params_list,
        iterations=args.iterations,
        warmup=args.warmup
    )
    
    # Print benchmark summaries
    for result in results:
        logger.info("\n" + result.summary())
    
    # Generate plots if requested
    if args.plot:
        logger.info("Generating plots")
        # Plot comparison of optimized vs non-optimized
        benchmark_manager.plot_optimization_comparison(
            results=results,
            metric='execution_time',
            output_file=os.path.join(benchmark_output_dir, "optimization_comparison.png")
        )
        
        # Plot individual metrics for each result
        for result in results:
            for metric in ['execution_time', 'memory_usage_mb', 'result_count']:
                if metric in result.metrics:
                    result.plot(
                        metric_name=metric,
                        output_file=os.path.join(
                            benchmark_output_dir, 
                            f"{result.name}_{metric}.png"
                        ),
                        title=f"{result.name} - {metric}"
                    )
    
    logger.info(f"Benchmark complete. Results saved to {benchmark_output_dir}")
    return results

if __name__ == "__main__":
    args = parse_arguments()
    run_benchmarks(args) 