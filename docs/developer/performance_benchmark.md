# Performance Benchmarking

This document describes the performance benchmarking system for the Scout application, which is used to measure and optimize application performance across different platforms and components.

## Overview

The Scout performance benchmarking system provides tools for:

1. Measuring execution time of critical application components
2. Profiling code to identify bottlenecks
3. Comparing performance across different platforms
4. Tracking performance changes over time
5. Setting performance baselines and thresholds

## Benchmark Structure

The benchmarking system is organized into multiple components:

### Benchmark Runner

Located at `scout/tests/performance/benchmark_runner.py`, this is the main entry point for running benchmarks. It provides:

- Command-line interface for running benchmarks
- Benchmark result collection and reporting
- Platform information gathering
- Profiling integration

### Benchmark Suites

Each benchmark suite focuses on a specific area of the application:

1. **Detection Benchmarks** (`benchmark_detection.py`): Tests template matching, OCR preprocessing, edge detection, and other image processing operations.

2. **Automation Benchmarks** (`benchmark_automation.py`): Tests task scheduling, action execution, and automation sequences.

3. **UI Benchmarks** (`benchmark_ui.py`): Tests UI rendering, event handling, and layout operations.

## Running Benchmarks

### Basic Usage

Run all benchmarks:

```bash
python -m scout.tests.performance.benchmark_runner
```

Run a specific benchmark suite:

```bash
python -m scout.tests.performance.benchmark_runner --benchmark detection
```

### Options

- `--benchmark {all,detection,automation,ui}`: Specify which benchmark suite to run
- `--iterations N`: Set the number of iterations for each benchmark (default: 5)
- `--profile`: Enable profiling for detailed function-level timing
- `--report FILE`: Save benchmark results to a JSON file

### Example

```bash
# Run detection benchmarks with profiling and 10 iterations
python -m scout.tests.performance.benchmark_runner --benchmark detection --iterations 10 --profile --report reports/detection_benchmark.json
```

## Creating Custom Benchmarks

### Adding to Existing Suites

To add a new benchmark to an existing suite:

1. Define a benchmark function in the appropriate suite file:

```python
def benchmark_my_function(param1, param2):
    """Benchmark for my function."""
    # Code to benchmark
    result = my_function(param1, param2)
```

2. Add the benchmark to the suite's `create_*_benchmark_suite` function:

```python
suite.add_benchmark(
    name="My Function",
    func=benchmark_my_function,
    iterations=iterations,
    profile=profile,
    args=[param1_value, param2_value]
)
```

### Creating a New Benchmark Suite

To create an entirely new benchmark suite:

1. Create a new file `benchmark_my_feature.py` in the `scout/tests/performance` directory
2. Define benchmark functions for your feature
3. Create a `create_my_feature_benchmark_suite` function
4. Update `benchmark_runner.py` to include your suite

## Benchmark Results

Benchmark results are reported in JSON format with the following structure:

```json
{
  "timestamp": "2025-02-26T12:34:56.789012",
  "platform": {
    "system": "Windows",
    "release": "10",
    "version": "10.0.19041",
    "machine": "AMD64",
    "processor": "Intel64 Family 6 Model 142 Stepping 12, GenuineIntel",
    "python_version": "3.9.7",
    "platform_type": "WINDOWS",
    "sys_platform": "win32"
  },
  "suites": [
    {
      "name": "Detection Performance",
      "description": "Benchmarks for detection-related components",
      "results": [
        {
          "name": "Template Matching",
          "execution_time_seconds": 0.123456,
          "iteration_count": 5,
          "avg_execution_time_seconds": 0.024691
        },
        {
          "name": "OCR Preprocessing",
          "execution_time_seconds": 0.234567,
          "iteration_count": 5,
          "avg_execution_time_seconds": 0.046913
        }
      ]
    }
  ]
}
```

## Profiling Results

When profiling is enabled, the benchmark results will include additional profile information:

```json
{
  "profile_stats": "         5 function calls in 0.123 seconds\n\n   Ordered by: cumulative time\n\n   ncalls  tottime  percall  cumtime  percall filename:lineno(function)\n        1    0.100    0.100    0.123    0.123 template_strategy.py:45(match_template)\n        1    0.020    0.020    0.020    0.020 {built-in method cv2.matchTemplate}\n        1    0.003    0.003    0.003    0.003 {built-in method cv2.minMaxLoc}\n"
}
```

## Best Practices

### When to Benchmark

1. **Baseline Measurements**: Establish performance baselines for critical operations
2. **Before Optimization**: Measure performance before attempting optimizations
3. **After Optimization**: Verify that changes improved performance
4. **During CI/CD**: Run benchmarks as part of continuous integration
5. **Before Releases**: Validate performance meets targets before releasing

### Benchmark Design

1. **Isolation**: Benchmark functions should isolate specific operations
2. **Realism**: Use realistic data and parameters
3. **Consistency**: Maintain consistent test conditions
4. **Specificity**: Focus on measurable, specific operations
5. **Documentation**: Document what is being measured and why

### Interpretation

When interpreting benchmark results:

1. **Context Matters**: Consider the hardware, OS, and Python version
2. **Variation is Normal**: Expect some variation between runs
3. **Look for Patterns**: Focus on significant trends rather than minor differences
4. **Profile First**: Use profiling to identify where time is spent before optimizing
5. **Set Thresholds**: Define acceptable performance thresholds for critical operations

## Performance Optimization Workflow

1. **Measure**: Establish baseline performance with benchmarks
2. **Profile**: Identify bottlenecks using profiling
3. **Optimize**: Make targeted improvements to the code
4. **Verify**: Run benchmarks to verify improvements
5. **Document**: Record optimizations and their impact

## Resources

For more detailed information on specific benchmarks and optimization techniques:

- [Detection Performance Guide](detection_performance.md)
- [UI Performance Guide](ui_performance.md)
- [Cross-Platform Testing](cross_platform_testing.md) 