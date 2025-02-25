#!/usr/bin/env python3
"""
Integration Test Runner

This script runs integration tests to verify that all Scout components
work together correctly as a complete system.
"""

import os
import sys
import unittest
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

# Add parent directory to path to allow running from script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegrationTestCategories:
    """Enumeration of integration test categories."""
    WINDOW_DETECTION = "window_detection"
    DETECTION_GAME = "detection_game"
    GAME_AUTOMATION = "game_automation"
    UI_INTEGRATION = "ui_integration"
    ERROR_HANDLING = "error_handling"
    END_TO_END = "end_to_end"
    ALL = "all"


def get_test_modules() -> Dict[str, List[str]]:
    """
    Get a mapping of test categories to test module names.
    
    Returns:
        Dictionary mapping category names to lists of test module names
    """
    return {
        IntegrationTestCategories.WINDOW_DETECTION: [
            "test_window_detection_integration"
        ],
        IntegrationTestCategories.DETECTION_GAME: [
            "test_detection_game_integration"
        ],
        IntegrationTestCategories.GAME_AUTOMATION: [
            "test_game_automation_integration"
        ],
        IntegrationTestCategories.UI_INTEGRATION: [
            "test_ui_integration"
        ],
        IntegrationTestCategories.ERROR_HANDLING: [
            "test_error_handling"
        ],
        IntegrationTestCategories.END_TO_END: [
            "test_end_to_end_integration"
        ]
    }


def run_tests(categories: Set[str], verbosity: int = 2) -> unittest.TestResult:
    """
    Run integration tests for the specified categories.
    
    Args:
        categories: Set of category names to test
        verbosity: Verbosity level (0-2)
        
    Returns:
        Test result object
    """
    # Get test modules for the specified categories
    test_modules = []
    test_module_mapping = get_test_modules()
    
    # Handle 'all' category
    if IntegrationTestCategories.ALL in categories:
        for module_list in test_module_mapping.values():
            test_modules.extend(module_list)
    else:
        # Get modules for specified categories
        for category in categories:
            if category in test_module_mapping:
                test_modules.extend(test_module_mapping[category])
    
    # Remove duplicates
    test_modules = list(set(test_modules))
    
    if not test_modules:
        logger.warning(f"No test modules found for categories: {categories}")
        return unittest.TestResult()
    
    logger.info(f"Running integration tests for modules: {test_modules}")
    
    # Build test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            # Import module from integration test package
            module = __import__(f"scout.tests.integration.{module_name}", fromlist=["*"])
            
            # Add tests from module
            module_tests = loader.loadTestsFromModule(module)
            suite.addTests(module_tests)
            
            logger.info(f"Added tests from module: {module_name}")
        except ImportError as e:
            logger.error(f"Error importing module {module_name}: {e}")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
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
    parser = argparse.ArgumentParser(description="Run integration tests")
    
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=[
            IntegrationTestCategories.WINDOW_DETECTION,
            IntegrationTestCategories.DETECTION_GAME,
            IntegrationTestCategories.GAME_AUTOMATION,
            IntegrationTestCategories.UI_INTEGRATION,
            IntegrationTestCategories.ERROR_HANDLING,
            IntegrationTestCategories.END_TO_END,
            IntegrationTestCategories.ALL
        ],
        default=[IntegrationTestCategories.ALL],
        help="Categories of integration tests to run"
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
    
    # Convert categories to set
    categories = set(args.categories)
    
    # Run tests
    logger.info(f"Starting integration tests for categories: {categories}")
    result = run_tests(categories, args.verbosity)
    
    # Generate report
    if args.report:
        generate_report(result, args.report)
    
    # Print summary
    logger.info(f"Integration tests completed. "
               f"Ran {result.testsRun} tests: "
               f"{result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)} passed, "
               f"{len(result.failures)} failed, "
               f"{len(result.errors)} errors, "
               f"{len(result.skipped)} skipped.")
    
    # Return success if all tests passed
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main()) 