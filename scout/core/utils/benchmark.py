"""
Performance Benchmarking Utilities

This module provides utilities for benchmarking the performance of the Scout
application, allowing for measurement and comparison of different components
and optimization strategies.
"""

import time
import logging
import json
import os
import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
import psutil

from scout.core.utils.performance import ExecutionTimer
from scout.core.utils.caching import cache_manager
from scout.core.utils.memory import memory_optimizer

# Set up logging
logger = logging.getLogger(__name__)

class BenchmarkResult:
    """
    Container for benchmark results with statistics and visualization methods.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize benchmark result.
        
        Args:
            name: Name of the benchmark
            description: Description of the benchmark
        """
        self.name = name
        self.description = description
        self.start_time = datetime.datetime.now()
        self.iterations = 0
        self.metrics: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Any] = {}
        self.system_info = self._get_system_info()
        self.annotations: Dict[str, List[Tuple[int, str]]] = {}
        
    def _get_system_info(self) -> Dict[str, Any]:
        """
        Collect system information for context.
        
        Returns:
            Dictionary with system information
        """
        cpu_info = {}
        mem_info = {}
        
        try:
            import cpuinfo
            cpu_info = cpuinfo.get_cpu_info()
        except ImportError:
            # If py-cpuinfo is not available, use psutil
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                cpu_info = {
                    'brand_raw': 'Unknown',
                    'hz_advertised_friendly': f"{cpu_freq.max:.2f}MHz" if cpu_freq.max else "Unknown",
                    'arch': os.uname().machine if hasattr(os, 'uname') else "Unknown",
                    'count': psutil.cpu_count(logical=True)
                }
                
        # Get memory information
        vm = psutil.virtual_memory()
        mem_info = {
            'total_gb': vm.total / (1024**3),
            'available_gb': vm.available / (1024**3)
        }
        
        return {
            'cpu': cpu_info,
            'memory': mem_info,
            'platform': os.name,
            'python_version': os.sys.version
        }
        
    def add_metric(self, name: str, value: float, iteration: Optional[int] = None) -> None:
        """
        Add a metric measurement to the benchmark.
        
        Args:
            name: Metric name
            value: Metric value
            iteration: Iteration number (None for auto-increment)
        """
        if name not in self.metrics:
            self.metrics[name] = []
            
        # Store the value
        self.metrics[name].append(value)
        
        # Update iteration count if this is a primary metric
        if iteration is None and name == 'execution_time':
            self.iterations += 1
            
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the benchmark.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        
    def add_annotation(self, metric_name: str, idx: int, text: str) -> None:
        """
        Add an annotation to a specific point in a metric.
        
        Args:
            metric_name: Name of the metric
            idx: Index in the metric data
            text: Annotation text
        """
        if metric_name not in self.annotations:
            self.annotations[metric_name] = []
            
        self.annotations[metric_name].append((idx, text))
        
    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """
        Calculate statistics for a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Dictionary with statistics (min, max, mean, median, std, etc.)
        """
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}
            
        values = np.array(self.metrics[metric_name])
        
        return {
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'mean': float(np.mean(values)),
            'median': float(np.median(values)),
            'std': float(np.std(values)),
            'count': len(values)
        }
        
    def plot(self, metric_name: str, output_file: Optional[str] = None, 
            show_annotations: bool = True, title: Optional[str] = None) -> None:
        """
        Plot a metric over iterations.
        
        Args:
            metric_name: Name of the metric to plot
            output_file: Path to save the plot (None to display)
            show_annotations: Whether to show annotations
            title: Plot title (None for default)
        """
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            logger.warning(f"No data for metric: {metric_name}")
            return
            
        # Create figure
        plt.figure(figsize=(10, 6))
        
        # Plot metric
        values = self.metrics[metric_name]
        x = range(1, len(values) + 1)
        plt.plot(x, values, marker='o', linestyle='-', alpha=0.7)
        
        # Add annotations if requested
        if show_annotations and metric_name in self.annotations:
            for idx, text in self.annotations[metric_name]:
                if 0 <= idx < len(values):
                    plt.annotate(text, (idx + 1, values[idx]),
                                textcoords="offset points", xytext=(0, 10),
                                ha='center')
                                
        # Add statistics as text
        stats = self.get_statistics(metric_name)
        stat_text = (f"Mean: {stats['mean']:.4f}, Median: {stats['median']:.4f}, "
                    f"Min: {stats['min']:.4f}, Max: {stats['max']:.4f}, "
                    f"Std: {stats['std']:.4f}")
        plt.figtext(0.5, 0.01, stat_text, ha='center', fontsize=10)
        
        # Set labels and title
        plt.xlabel('Iteration')
        plt.ylabel(metric_name)
        plt.title(title or f"{self.name} - {metric_name} over iterations")
        plt.grid(True, alpha=0.3)
        
        # Save or show plot
        if output_file:
            plt.savefig(output_file, dpi=100, bbox_inches='tight')
            logger.info(f"Saved plot to {output_file}")
        else:
            plt.show()
            
        plt.close()
        
    def plot_comparison(self, metric_names: List[str], output_file: Optional[str] = None,
                      normalize: bool = False, title: Optional[str] = None) -> None:
        """
        Plot multiple metrics for comparison.
        
        Args:
            metric_names: List of metrics to compare
            output_file: Path to save the plot (None to display)
            normalize: Whether to normalize values (0-1 scale)
            title: Plot title (None for default)
        """
        # Validate metrics
        valid_metrics = [m for m in metric_names if m in self.metrics and self.metrics[m]]
        if not valid_metrics:
            logger.warning("No valid metrics to compare")
            return
            
        # Create figure
        plt.figure(figsize=(12, 6))
        
        # Process each metric
        for metric_name in valid_metrics:
            values = np.array(self.metrics[metric_name])
            
            # Normalize if requested
            if normalize:
                min_val = np.min(values)
                max_val = np.max(values)
                if max_val > min_val:
                    values = (values - min_val) / (max_val - min_val)
                    
            # Plot metric
            x = range(1, len(values) + 1)
            plt.plot(x, values, marker='o', linestyle='-', label=metric_name, alpha=0.7)
            
        # Set labels and title
        plt.xlabel('Iteration')
        plt.ylabel('Value' if normalize else 'Metric Value')
        plt.title(title or f"{self.name} - Metric Comparison")
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Save or show plot
        if output_file:
            plt.savefig(output_file, dpi=100, bbox_inches='tight')
            logger.info(f"Saved comparison plot to {output_file}")
        else:
            plt.show()
            
        plt.close()
        
    def save(self, file_path: str) -> None:
        """
        Save benchmark results to a JSON file.
        
        Args:
            file_path: Path to save the results
        """
        # Create result dictionary
        result = {
            'name': self.name,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.datetime.now().isoformat(),
            'iterations': self.iterations,
            'metrics': {k: list(map(float, v)) for k, v in self.metrics.items()},
            'statistics': {k: self.get_statistics(k) for k in self.metrics},
            'metadata': self.metadata,
            'system_info': self.system_info,
            'annotations': {k: [(i, t) for i, t in v] for k, v in self.annotations.items()}
        }
        
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"Saved benchmark results to {file_path}")
        
    @classmethod
    def load(cls, file_path: str) -> 'BenchmarkResult':
        """
        Load benchmark results from a JSON file.
        
        Args:
            file_path: Path to load the results from
            
        Returns:
            Loaded benchmark result
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Create result object
        result = cls(data['name'], data['description'])
        result.start_time = datetime.datetime.fromisoformat(data['start_time'])
        result.iterations = data['iterations']
        result.metrics = data['metrics']
        result.metadata = data['metadata']
        result.system_info = data['system_info']
        result.annotations = data['annotations']
        
        return result
        
    def summary(self) -> str:
        """
        Get a text summary of the benchmark results.
        
        Returns:
            Summary text
        """
        lines = [
            f"Benchmark: {self.name}",
            f"Description: {self.description}",
            f"Start time: {self.start_time.isoformat()}",
            f"Iterations: {self.iterations}",
            "",
            "Statistics:"
        ]
        
        for metric_name in sorted(self.metrics.keys()):
            stats = self.get_statistics(metric_name)
            if stats:
                lines.append(f"  {metric_name}:")
                lines.append(f"    Min: {stats['min']:.6f}")
                lines.append(f"    Max: {stats['max']:.6f}")
                lines.append(f"    Mean: {stats['mean']:.6f}")
                lines.append(f"    Median: {stats['median']:.6f}")
                lines.append(f"    Std Dev: {stats['std']:.6f}")
                
        if self.metadata:
            lines.append("")
            lines.append("Metadata:")
            for key, value in sorted(self.metadata.items()):
                lines.append(f"  {key}: {value}")
                
        return "\n".join(lines)


class Benchmark:
    """
    Utility for benchmarking components of the Scout application.
    
    Provides methods for:
    - Running performance benchmarks on specific functions
    - Comparing different implementations or configurations
    - Measuring resource usage during execution
    - Generating benchmark reports
    """
    
    def __init__(self, results_dir: Optional[str] = None):
        """
        Initialize benchmark utility.
        
        Args:
            results_dir: Directory to store benchmark results (None for no saving)
        """
        self.results_dir = results_dir
        
        # Create results directory if specified
        if self.results_dir and not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir, exist_ok=True)
            logger.info(f"Created benchmark results directory: {self.results_dir}")
            
    def measure_function(self, func: Callable, args: tuple = (), kwargs: Dict = None,
                       iterations: int = 10, warmup: int = 2,
                       name: Optional[str] = None,
                       description: Optional[str] = None) -> BenchmarkResult:
        """
        Benchmark a function by measuring execution time and resource usage.
        
        Args:
            func: Function to benchmark
            args: Function arguments
            kwargs: Function keyword arguments
            iterations: Number of iterations to run
            warmup: Number of warmup iterations (not measured)
            name: Benchmark name (None for auto)
            description: Benchmark description
            
        Returns:
            Benchmark results
        """
        kwargs = kwargs or {}
        name = name or f"{func.__name__}_benchmark"
        description = description or f"Benchmark of {func.__name__}"
        
        # Initialize results
        result = BenchmarkResult(name, description)
        result.add_metadata('function', func.__name__)
        result.add_metadata('iterations', iterations)
        result.add_metadata('warmup_iterations', warmup)
        
        # Get process for resource monitoring
        process = psutil.Process(os.getpid())
        
        # Perform warmup iterations
        logger.info(f"Running {warmup} warmup iterations")
        for _ in range(warmup):
            func(*args, **kwargs)
            
        # Run benchmark iterations
        logger.info(f"Running {iterations} benchmark iterations")
        for i in range(iterations):
            # Record memory before execution
            mem_before = process.memory_info().rss / (1024 * 1024)
            
            # Measure execution time
            start_time = time.time()
            func_result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record memory after execution
            mem_after = process.memory_info().rss / (1024 * 1024)
            mem_change = mem_after - mem_before
            
            # Record metrics
            result.add_metric('execution_time', execution_time)
            result.add_metric('memory_usage_mb', mem_after)
            result.add_metric('memory_change_mb', mem_change)
            
            # Check if result size can be measured
            if isinstance(func_result, (list, dict)):
                result.add_metric('result_size', len(func_result))
                
            logger.debug(f"Iteration {i+1}/{iterations}: time={execution_time:.6f}s, "
                        f"memory change={mem_change:.2f}MB")
                        
        # Save results if a directory was specified
        if self.results_dir:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = os.path.join(self.results_dir, f"{name}_{timestamp}.json")
            result.save(result_file)
            
        return result
        
    def compare_functions(self, functions: List[Dict], 
                        common_args: tuple = (), common_kwargs: Dict = None,
                        iterations: int = 10, warmup: int = 2,
                        name: str = "function_comparison") -> List[BenchmarkResult]:
        """
        Compare multiple functions or implementations.
        
        Args:
            functions: List of {func, name, args, kwargs} dictionaries
            common_args: Arguments to pass to all functions
            common_kwargs: Keyword arguments to pass to all functions
            iterations: Number of iterations to run
            warmup: Number of warmup iterations (not measured)
            name: Base name for the benchmark
            
        Returns:
            List of benchmark results, one per function
        """
        common_kwargs = common_kwargs or {}
        results = []
        
        for i, func_dict in enumerate(functions):
            func = func_dict['func']
            func_name = func_dict.get('name', func.__name__)
            func_args = func_dict.get('args', common_args)
            func_kwargs = {**common_kwargs, **func_dict.get('kwargs', {})}
            
            logger.info(f"Benchmarking function {i+1}/{len(functions)}: {func_name}")
            
            # Run benchmark
            result = self.measure_function(
                func=func,
                args=func_args,
                kwargs=func_kwargs,
                iterations=iterations,
                warmup=warmup,
                name=f"{name}_{func_name}",
                description=f"Benchmark of {func_name} ({name})"
            )
            
            results.append(result)
            
        return results
        
    def plot_comparison(self, results: List[BenchmarkResult], metric: str = 'execution_time',
                      output_file: Optional[str] = None, title: Optional[str] = None) -> None:
        """
        Plot comparison of multiple benchmark results.
        
        Args:
            results: List of benchmark results to compare
            metric: Metric to compare
            output_file: Path to save the plot (None to display)
            title: Plot title (None for default)
        """
        if not results:
            logger.warning("No results to compare")
            return
            
        # Extract statistics for the metric
        labels = []
        means = []
        stds = []
        
        for result in results:
            func_name = result.metadata.get('function', 'Unknown')
            labels.append(func_name)
            
            stats = result.get_statistics(metric)
            means.append(stats.get('mean', 0))
            stds.append(stats.get('std', 0))
            
        # Create bar chart
        plt.figure(figsize=(10, 6))
        x = range(len(labels))
        plt.bar(x, means, yerr=stds, alpha=0.7, capsize=10)
        plt.xticks(x, labels, rotation=45, ha='right')
        
        # Add labels and title
        plt.xlabel('Function')
        plt.ylabel(metric)
        plt.title(title or f"Comparison of {metric}")
        plt.tight_layout()
        
        # Save or show plot
        if output_file:
            plt.savefig(output_file, dpi=100, bbox_inches='tight')
            logger.info(f"Saved comparison plot to {output_file}")
        else:
            plt.show()
            
        plt.close()
        
    def benchmark_detection(self, detection_service, image: np.ndarray,
                          strategy: str, params: Dict,
                          iterations: int = 5, warmup: int = 2,
                          with_optimizations: bool = True) -> BenchmarkResult:
        """
        Benchmark the detection service with specific parameters.
        
        Args:
            detection_service: Detection service instance
            image: Input image for detection
            strategy: Detection strategy to use ('template', 'ocr', 'yolo')
            params: Parameters for the detection
            iterations: Number of iterations to run
            warmup: Number of warmup iterations
            with_optimizations: Whether to use optimizations (caching, parallel)
            
        Returns:
            Benchmark results
        """
        # Set up benchmark
        name = f"detection_{strategy}_{'optimized' if with_optimizations else 'baseline'}"
        description = f"Benchmark of {strategy} detection "
        description += "with optimizations" if with_optimizations else "without optimizations"
        
        result = BenchmarkResult(name, description)
        result.add_metadata('strategy', strategy)
        result.add_metadata('with_optimizations', with_optimizations)
        result.add_metadata('params', params)
        result.add_metadata('image_shape', image.shape)
        
        # Define detection function based on strategy
        if strategy == 'template':
            detect_func = lambda: detection_service.detect_template(
                template_name=params.get('template_name', ''),
                confidence_threshold=params.get('confidence_threshold', 0.7),
                max_results=params.get('max_results', 10),
                region=params.get('region'),
                use_cache=with_optimizations
            )
        elif strategy == 'ocr':
            detect_func = lambda: detection_service.detect_text(
                pattern=params.get('pattern'),
                confidence_threshold=params.get('confidence_threshold', 0.6),
                region=params.get('region'),
                use_cache=with_optimizations,
                preprocess=params.get('preprocess')
            )
        elif strategy == 'yolo':
            detect_func = lambda: detection_service.detect_objects(
                class_names=params.get('class_names'),
                confidence_threshold=params.get('confidence_threshold', 0.5),
                region=params.get('region'),
                use_cache=with_optimizations,
                nms_threshold=params.get('nms_threshold', 0.5)
            )
        else:
            raise ValueError(f"Unsupported detection strategy: {strategy}")
            
        # Make sure we start with a clean state
        if with_optimizations:
            # Initialize services
            memory_optimizer.start()
        else:
            # Clear caches to ensure fair comparison
            detection_service.clear_cache()
            cache_manager.clear_all_caches()
            
        # Perform warmup iterations
        logger.info(f"Running {warmup} warmup iterations")
        for _ in range(warmup):
            detect_func()
            
        # Clear cache between warmup and actual benchmark if needed
        if not with_optimizations:
            detection_service.clear_cache()
            
        # Run benchmark iterations
        logger.info(f"Running {iterations} benchmark iterations")
        for i in range(iterations):
            # Take memory snapshot before
            mem_before = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            
            # Measure execution time
            with ExecutionTimer(f"Detection iteration {i+1}") as timer:
                detection_results = detect_func()
                
            # Record memory after execution
            mem_after = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            mem_change = mem_after - mem_before
            
            # Record metrics
            result.add_metric('execution_time', timer.execution_time)
            result.add_metric('memory_usage_mb', mem_after)
            result.add_metric('memory_change_mb', mem_change)
            result.add_metric('result_count', len(detection_results))
            
            logger.debug(f"Iteration {i+1}/{iterations}: time={timer.execution_time:.6f}s, "
                        f"results={len(detection_results)}, memory change={mem_change:.2f}MB")
                        
            # Clear cache between iterations if not using optimizations
            if not with_optimizations:
                detection_service.clear_cache()
                
        # Clean up
        if with_optimizations:
            memory_optimizer.stop()
            
        # Save results if a directory was specified
        if self.results_dir:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = os.path.join(self.results_dir, f"{name}_{timestamp}.json")
            result.save(result_file)
            
        return result
        
    def compare_optimizations(self, detection_service, image: np.ndarray,
                           strategies: List[str], params_list: List[Dict],
                           iterations: int = 5, warmup: int = 2) -> List[BenchmarkResult]:
        """
        Compare detection with and without optimizations.
        
        Args:
            detection_service: Detection service instance
            image: Input image for detection
            strategies: List of detection strategies to benchmark
            params_list: List of parameter dictionaries for each strategy
            iterations: Number of iterations to run
            warmup: Number of warmup iterations
            
        Returns:
            List of benchmark results
        """
        if len(strategies) != len(params_list):
            raise ValueError("strategies and params_list must have the same length")
            
        results = []
        
        for strategy, params in zip(strategies, params_list):
            # Run with optimizations
            logger.info(f"Benchmarking {strategy} detection with optimizations")
            optim_result = self.benchmark_detection(
                detection_service=detection_service,
                image=image,
                strategy=strategy,
                params=params,
                iterations=iterations,
                warmup=warmup,
                with_optimizations=True
            )
            results.append(optim_result)
            
            # Run without optimizations
            logger.info(f"Benchmarking {strategy} detection without optimizations")
            baseline_result = self.benchmark_detection(
                detection_service=detection_service,
                image=image,
                strategy=strategy,
                params=params,
                iterations=iterations,
                warmup=warmup,
                with_optimizations=False
            )
            results.append(baseline_result)
            
        return results
        
    def plot_optimization_comparison(self, results: List[BenchmarkResult], 
                                  metric: str = 'execution_time',
                                  output_file: Optional[str] = None) -> None:
        """
        Plot comparison of optimized vs. non-optimized performance.
        
        Args:
            results: List of benchmark results
            metric: Metric to compare
            output_file: Path to save the plot (None to display)
        """
        # Group results by strategy
        strategies = set()
        strategy_results = {}
        
        for result in results:
            strategy = result.metadata.get('strategy', 'unknown')
            optimized = result.metadata.get('with_optimizations', False)
            
            strategies.add(strategy)
            
            key = (strategy, optimized)
            strategy_results[key] = result
            
        # Check if we have pairs for comparison
        if not all((strategy, True) in strategy_results and 
                   (strategy, False) in strategy_results 
                   for strategy in strategies):
            logger.warning("Incomplete optimization comparison data")
            
        # Create grouped bar chart
        plt.figure(figsize=(12, 6))
        
        # Set up positions
        x = np.arange(len(strategies))
        width = 0.35
        
        # Extract statistics
        baseline_means = []
        baseline_stds = []
        optimized_means = []
        optimized_stds = []
        
        strategy_list = sorted(strategies)
        
        for strategy in strategy_list:
            # Get baseline result
            baseline = strategy_results.get((strategy, False))
            if baseline:
                stats = baseline.get_statistics(metric)
                baseline_means.append(stats.get('mean', 0))
                baseline_stds.append(stats.get('std', 0))
            else:
                baseline_means.append(0)
                baseline_stds.append(0)
                
            # Get optimized result
            optimized = strategy_results.get((strategy, True))
            if optimized:
                stats = optimized.get_statistics(metric)
                optimized_means.append(stats.get('mean', 0))
                optimized_stds.append(stats.get('std', 0))
            else:
                optimized_means.append(0)
                optimized_stds.append(0)
                
        # Plot bars
        plt.bar(x - width/2, baseline_means, width, yerr=baseline_stds, 
               label='Baseline', alpha=0.7, capsize=10)
        plt.bar(x + width/2, optimized_means, width, yerr=optimized_stds,
               label='Optimized', alpha=0.7, capsize=10)
               
        # Calculate speedup
        speedups = []
        for baseline, optimized in zip(baseline_means, optimized_means):
            if baseline > 0 and optimized > 0:
                speedup = baseline / optimized
                speedups.append(f"{speedup:.2f}x")
            else:
                speedups.append("N/A")
                
        # Add speedup annotations
        for i, speedup in enumerate(speedups):
            plt.annotate(
                f"{speedup}",
                (x[i], max(baseline_means[i], optimized_means[i]) + 
                     max(baseline_stds[i], optimized_stds[i]) + 0.05),
                ha='center',
                va='bottom'
            )
            
        # Set labels and title
        plt.xlabel('Detection Strategy')
        plt.ylabel(metric)
        plt.title(f'Performance Comparison: Baseline vs. Optimized ({metric})')
        plt.xticks(x, strategy_list)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Save or show plot
        if output_file:
            plt.savefig(output_file, dpi=100, bbox_inches='tight')
            logger.info(f"Saved optimization comparison plot to {output_file}")
        else:
            plt.show()
            
        plt.close()
        
        # Print textual summary
        logger.info("Optimization comparison summary:")
        for i, strategy in enumerate(strategy_list):
            if baseline_means[i] > 0 and optimized_means[i] > 0:
                improvement = (baseline_means[i] - optimized_means[i]) / baseline_means[i] * 100
                logger.info(f"  {strategy}: {speedups[i]} speedup ({improvement:.1f}% improvement)")


# Create global benchmark manager
benchmark_manager = Benchmark(
    results_dir=os.path.join(os.path.expanduser('~'), '.scout', 'benchmarks')
) 