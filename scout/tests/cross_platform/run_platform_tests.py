#!/usr/bin/env python3
"""
Platform Test Runner

This script runs the platform-specific tests and generates a report
on the results across different platforms.
"""

import os
import sys
import unittest
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow running from script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from scout.tests.cross_platform import get_current_platform, PlatformType
from scout.tests.cross_platform.platform_utils import get_platform_info


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_tests(test_pattern: str = "test_*.py", verbosity: int = 2) -> unittest.TestResult:
    """
    Run all the platform-specific tests matching the pattern.
    
    Args:
        test_pattern: Pattern for test files to run
        verbosity: Verbosity level (0-2)
        
    Returns:
        Test result object
    """
    logger.info(f"Running platform tests with pattern: {test_pattern}")
    
    # Get test loader
    loader = unittest.TestLoader()
    
    # Find tests in the current directory matching the pattern
    test_suite = loader.discover(script_dir, pattern=test_pattern)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(test_suite)
    
    return result


def generate_report(result: unittest.TestResult, output_file: Optional[str] = None) -> str:
    """
    Generate a report from the test results.
    
    Args:
        result: Test result object
        output_file: File to write the report to, or None for no file output
        
    Returns:
        Report as a string
    """
    # Collect platform information
    platform_info = get_platform_info()
    
    # Format test results
    total_tests = result.testsRun
    passed_tests = total_tests - len(result.failures) - len(result.errors) - len(result.skipped)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    # Format errors and failures
    errors = [
        {
            "test": test_case.__str__(),
            "error": error
        }
        for test_case, error in result.errors
    ]
    
    failures = [
        {
            "test": test_case.__str__(),
            "failure": failure
        }
        for test_case, failure in result.failures
    ]
    
    skipped = [
        {
            "test": test_case.__str__(),
            "reason": reason
        }
        for test_case, reason in result.skipped
    ]
    
    # Create report data
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform_info,
        "results": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success_rate": f"{success_rate:.2f}%"
        },
        "details": {
            "errors": errors,
            "failures": failures,
            "skipped": skipped
        }
    }
    
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
    parser = argparse.ArgumentParser(description="Run platform-specific tests")
    
    parser.add_argument(
        "--pattern",
        default="test_*.py",
        help="Pattern for test files to run"
    )
    
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=2,
        help="Verbosity level (0-2)"
    )
    
    parser.add_argument(
        "--report",
        help="File to write the report to"
    )
    
    args = parser.parse_args()
    
    # Log platform information
    platform_type = get_current_platform()
    logger.info(f"Running tests on platform: {platform_type.name}")
    
    # Run tests
    result = run_tests(args.pattern, args.verbosity)
    
    # Generate report
    if args.report:
        generate_report(result, args.report)
    
    # Return success if all tests passed
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main()) 