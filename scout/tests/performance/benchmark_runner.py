#!/usr/bin/env python3
"""
Performance Benchmark Runner

This module provides tools for running performance benchmarks
on various components of the Scout application and generating
reports on the results.
"""

import os
import sys
import time
import json
import logging
import argparse
import cProfile
import pstats
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple

# Add parent directory to path to allow running from script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from scout.tests.cross_platform.platform_utils import get_platform_info


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BenchmarkResult:
    """Class to store benchmark results."""
    
    def __init__(self, name: str, execution_time: float, iteration_count: int = 1, profiler_stats: Optional[pstats.Stats] = None):
        """
        Initialize benchmark result.
        
        Args:
            name: Benchmark name
            execution_time: Execution time in seconds
            iteration_count: Number of iterations (for averaging)
            profiler_stats: Optional profiler statistics
        """
        self.name = name
        self.execution_time = execution_time
        self.iteration_count = iteration_count
        self.profiler_stats = profiler_stats
        self.avg_execution_time = execution_time / iteration_count if iteration_count > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for reporting.
        
        Returns:
            Dictionary representation
        """
        result = {
            "name": self.name,
            "execution_time_seconds": self.execution_time,
            "iteration_count": self.iteration_count,
            "avg_execution_time_seconds": self.avg_execution_time,
        }
        
        # Add profiler stats if available
        if self.profiler_stats is not None:
            # Get top functions by cumulative time
            stats_dict = {}
            
            # Create a temporary file for stats
            with tempfile.NamedTemporaryFile(mode='w') as tmp:
                # Redirect stats to temporary file
                self.profiler_stats.sort_stats('cumulative').print_stats(20, file=tmp.file)
                tmp.flush()
                
                # Read stats back
                with open(tmp.name, 'r') as f:
                    stats_text = f.read()
            
            # Add stats to result
            result["profile_stats"] = stats_text
        
        return result


class BenchmarkSuite:
    """Suite of benchmarks to run."""
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize benchmark suite.
        
        Args:
            name: Suite name
            description: Suite description
        """
        self.name = name
        self.description = description
        self.benchmarks: List[Dict[str, Any]] = []
    
    def add_benchmark(self, name: str, func: Callable, iterations: int = 1, profile: bool = False, args: List[Any] = None, kwargs: Dict[str, Any] = None):
        """
        Add a benchmark to the suite.
        
        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations (for averaging)
            profile: Whether to profile the execution
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
        """
        self.benchmarks.append({
            "name": name,
            "func": func,
            "iterations": iterations,
            "profile": profile,
            "args": args or [],
            "kwargs": kwargs or {}
        })
    
    def run(self) -> List[BenchmarkResult]:
        """
        Run all benchmarks in the suite.
        
        Returns:
            List of benchmark results
        """
        results = []
        
        logger.info(f"Running benchmark suite: {self.name}")
        
        for benchmark in self.benchmarks:
            name = benchmark["name"]
            func = benchmark["func"]
            iterations = benchmark["iterations"]
            profile = benchmark["profile"]
            args = benchmark["args"]
            kwargs = benchmark["kwargs"]
            
            logger.info(f"Running benchmark: {name} (iterations: {iterations})")
            
            # Run benchmark
            if profile:
                # Profile execution
                profiler = cProfile.Profile()
                profiler.enable()
                
                start_time = time.time()
                for _ in range(iterations):
                    func(*args, **kwargs)
                end_time = time.time()
                
                profiler.disable()
                
                # Create stats object
                stats = pstats.Stats(profiler)
                
                # Create result
                result = BenchmarkResult(name, end_time - start_time, iterations, stats)
            else:
                # Simple timing
                start_time = time.time()
                for _ in range(iterations):
                    func(*args, **kwargs)
                end_time = time.time()
                
                # Create result
                result = BenchmarkResult(name, end_time - start_time, iterations)
            
            results.append(result)
            
            # Log result
            logger.info(f"Benchmark {name} completed in {result.execution_time:.6f}s "
                       f"(avg: {result.avg_execution_time:.6f}s)")
        
        return results


def generate_report(suites: List[Tuple[BenchmarkSuite, List[BenchmarkResult]]], output_file: Optional[str] = None) -> str:
    """
    Generate a report from benchmark results.
    
    Args:
        suites: List of (suite, results) tuples
        output_file: File to write the report to, or None for no file output
        
    Returns:
        Report as a string
    """
    # Collect platform information
    platform_info = get_platform_info()
    
    # Create report data
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform_info,
        "suites": []
    }
    
    # Add suite results
    for suite, results in suites:
        suite_data = {
            "name": suite.name,
            "description": suite.description,
            "results": [result.to_dict() for result in results]
        }
        report_data["suites"].append(suite_data)
    
    # Format as JSON with indentation
    report_json = json.dumps(report_data, indent=2)
    
    # Write to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(report_json)
        
        logger.info(f"Report written to: {output_path}")
    
    return report_json


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    
    parser.add_argument(
        "--benchmark",
        choices=["all", "detection", "automation", "ui"],
        default="all",
        help="Benchmark to run"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations for each benchmark"
    )
    
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable profiling"
    )
    
    parser.add_argument(
        "--report",
        help="File to write the report to"
    )
    
    args = parser.parse_args()
    
    # Create suites based on args
    suites_to_run = []
    suite_results = []
    
    # Detection benchmarks
    if args.benchmark in ["all", "detection"]:
        from scout.tests.performance.benchmark_detection import create_detection_benchmark_suite
        detection_suite = create_detection_benchmark_suite(args.iterations, args.profile)
        suites_to_run.append(detection_suite)
    
    # Automation benchmarks
    if args.benchmark in ["all", "automation"]:
        from scout.tests.performance.benchmark_automation import create_automation_benchmark_suite
        automation_suite = create_automation_benchmark_suite(args.iterations, args.profile)
        suites_to_run.append(automation_suite)
    
    # UI benchmarks
    if args.benchmark in ["all", "ui"]:
        from scout.tests.performance.benchmark_ui import create_ui_benchmark_suite
        ui_suite = create_ui_benchmark_suite(args.iterations, args.profile)
        suites_to_run.append(ui_suite)
    
    # Run all suites
    for suite in suites_to_run:
        results = suite.run()
        suite_results.append((suite, results))
    
    # Generate report
    if args.report or len(suite_results) > 0:
        generate_report(suite_results, args.report)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 