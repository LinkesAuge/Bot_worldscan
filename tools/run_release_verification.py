#!/usr/bin/env python3
"""
Scout Release Verification Script

This script helps automate the release verification process by running the necessary
checks and collecting the results. It will:

1. Check version consistency
2. Run tests and collect results
3. Build executables for the current platform
4. Generate verification reports

Usage:
    python run_release_verification.py [options]

Options:
    --version VERSION     Version to verify (default: 1.0.0)
    --output-dir DIR      Directory to store verification results
    --skip-build          Skip building executables
    --skip-tests          Skip running tests
    --help                Show this help message
"""

import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import prepare_release helper functions if available
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from prepare_release import (
        Colors, 
        check_requirements, 
        check_version_in_files, 
        run_tests, 
        run_linting,
        build_platform,
        check_documentation,
        create_release_artifacts,
        log_info,
        log_success,
        log_warning,
        log_error,
        log_step,
        run_command,
    )
except ImportError:
    # Define our own versions if prepare_release can't be imported
    class Colors:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    def log_info(message: str) -> None:
        print(f"[INFO] {message}")

    def log_success(message: str) -> None:
        print(f"[SUCCESS] {message}")

    def log_warning(message: str) -> None:
        print(f"[WARNING] {message}")

    def log_error(message: str) -> None:
        print(f"[ERROR] {message}")

    def log_step(step: str) -> None:
        print(f"\n=== {step} ===")

    def run_command(command: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                command,
                cwd=cwd or Path.cwd(),
                capture_output=True,
                text=True,
                check=True,
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"Command failed with exit code {e.returncode}\n{e.stderr}"


# Constants
REPO_ROOT = Path(__file__).parent.parent.absolute()
DEFAULT_VERSION = "1.0.0"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "verification_results"
VERIFICATION_DOC = REPO_ROOT / "docs" / "developer" / "release_verification.md"
QA_CHECKLIST = REPO_ROOT / "docs" / "developer" / "final_qa_checklist.md"
TEST_PLAN = REPO_ROOT / "docs" / "developer" / "test_plan.md"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Files to check for version consistency
VERSION_FILES = [
    "setup.py",
    "scout/__init__.py",
    "file_version_info.txt",
    "installer/scout_installer.nsi",
    "README.md",
    "docs/RELEASE_NOTES.md",
]


class VerificationResult:
    """Class to store verification results."""
    
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.status = "Not Run"
        self.details = ""
        self.start_time = None
        self.end_time = None
        self.duration = None
    
    def start(self) -> None:
        """Mark test as started."""
        self.start_time = time.time()
        self.status = "Running"
    
    def succeed(self, details: str = "") -> None:
        """Mark test as successful."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time if self.start_time else None
        self.status = "Success"
        self.details = details
    
    def fail(self, details: str = "") -> None:
        """Mark test as failed."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time if self.start_time else None
        self.status = "Failed"
        self.details = details
    
    def skip(self, details: str = "") -> None:
        """Mark test as skipped."""
        self.status = "Skipped"
        self.details = details
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting."""
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "details": self.details,
            "duration": self.duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class VerificationReport:
    """Class to generate and manage verification reports."""
    
    def __init__(self, version: str, output_dir: Path):
        self.version = version
        self.output_dir = output_dir
        self.results = []
        self.timestamp = TIMESTAMP
        self.platform = platform.system()
        self.system_info = self._collect_system_info()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _collect_system_info(self) -> Dict:
        """Collect information about the current system."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        }
    
    def add_result(self, result: VerificationResult) -> None:
        """Add a verification result to the report."""
        self.results.append(result)
    
    def get_result(self, name: str, category: str) -> Optional[VerificationResult]:
        """Get a specific verification result."""
        for result in self.results:
            if result.name == name and result.category == category:
                return result
        return None
    
    def get_summary(self) -> Dict:
        """Get a summary of all results."""
        total = len(self.results)
        succeeded = sum(1 for r in self.results if r.status == "Success")
        failed = sum(1 for r in self.results if r.status == "Failed")
        skipped = sum(1 for r in self.results if r.status == "Skipped")
        not_run = sum(1 for r in self.results if r.status == "Not Run")
        
        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "not_run": not_run,
            "success_rate": round(succeeded / total * 100, 2) if total > 0 else 0,
        }
    
    def write_json_report(self) -> Path:
        """Write a JSON report with all results."""
        report_file = self.output_dir / f"verification_report_{self.timestamp}.json"
        
        report_data = {
            "version": self.version,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "system_info": self.system_info,
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results],
        }
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        
        log_info(f"Wrote JSON report to {report_file}")
        return report_file
    
    def write_markdown_report(self) -> Path:
        """Write a Markdown report with all results."""
        report_file = self.output_dir / f"verification_report_{self.timestamp}.md"
        
        summary = self.get_summary()
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# Scout {self.version} Verification Report\n\n")
            f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## System Information\n\n")
            for key, value in self.system_info.items():
                f.write(f"- **{key}**: {value}\n")
            
            f.write("\n## Summary\n\n")
            f.write(f"- **Total Tests**: {summary['total']}\n")
            f.write(f"- **Succeeded**: {summary['succeeded']} ({summary['success_rate']}%)\n")
            f.write(f"- **Failed**: {summary['failed']}\n")
            f.write(f"- **Skipped**: {summary['skipped']}\n")
            f.write(f"- **Not Run**: {summary['not_run']}\n\n")
            
            # Group results by category
            results_by_category = {}
            for result in self.results:
                if result.category not in results_by_category:
                    results_by_category[result.category] = []
                results_by_category[result.category].append(result)
            
            f.write("## Detailed Results\n\n")
            
            for category, results in results_by_category.items():
                f.write(f"### {category}\n\n")
                
                f.write("| Test | Status | Duration | Details |\n")
                f.write("|------|--------|----------|--------|\n")
                
                for result in results:
                    duration_str = (
                        f"{result.duration:.2f}s" 
                        if result.duration is not None 
                        else "N/A"
                    )
                    status_str = (
                        f"✅ {result.status}" if result.status == "Success" 
                        else f"❌ {result.status}" if result.status == "Failed" 
                        else f"⏭️ {result.status}" if result.status == "Skipped" 
                        else f"⏳ {result.status}"
                    )
                    details = result.details[:50] + "..." if len(result.details) > 50 else result.details
                    f.write(f"| {result.name} | {status_str} | {duration_str} | {details} |\n")
                
                f.write("\n")
            
            # Add footer with links to verification documents
            f.write("\n---\n\n")
            f.write("**Related Documents**:\n")
            f.write("- [Release Verification](../docs/developer/release_verification.md)\n")
            f.write("- [Final QA Checklist](../docs/developer/final_qa_checklist.md)\n")
            f.write("- [Test Plan](../docs/developer/test_plan.md)\n")
        
        log_info(f"Wrote Markdown report to {report_file}")
        return report_file
    
    def write_html_report(self) -> Path:
        """Write an HTML report with all results."""
        report_file = self.output_dir / f"verification_report_{self.timestamp}.html"
        
        summary = self.get_summary()
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html>\n")
            f.write("<html lang='en'>\n")
            f.write("<head>\n")
            f.write("  <meta charset='UTF-8'>\n")
            f.write("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n")
            f.write(f"  <title>Scout {self.version} Verification Report</title>\n")
            f.write("  <style>\n")
            f.write("    body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }\n")
            f.write("    h1 { color: #2c3e50; }\n")
            f.write("    h2 { color: #3498db; margin-top: 30px; }\n")
            f.write("    h3 { color: #2980b9; }\n")
            f.write("    .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }\n")
            f.write("    .success { color: #27ae60; }\n")
            f.write("    .failure { color: #e74c3c; }\n")
            f.write("    .skipped { color: #f39c12; }\n")
            f.write("    .not-run { color: #95a5a6; }\n")
            f.write("    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }\n")
            f.write("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n")
            f.write("    th { background-color: #f2f2f2; }\n")
            f.write("    tr:nth-child(even) { background-color: #f9f9f9; }\n")
            f.write("    .footer { margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }\n")
            f.write("  </style>\n")
            f.write("</head>\n")
            f.write("<body>\n")
            
            f.write(f"  <h1>Scout {self.version} Verification Report</h1>\n")
            f.write(f"  <p>Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
            
            f.write("  <h2>System Information</h2>\n")
            f.write("  <ul>\n")
            for key, value in self.system_info.items():
                f.write(f"    <li><strong>{key}</strong>: {value}</li>\n")
            f.write("  </ul>\n")
            
            f.write("  <h2>Summary</h2>\n")
            f.write("  <div class='summary'>\n")
            f.write(f"    <p><strong>Total Tests:</strong> {summary['total']}</p>\n")
            f.write(f"    <p class='success'><strong>Succeeded:</strong> {summary['succeeded']} ({summary['success_rate']}%)</p>\n")
            f.write(f"    <p class='failure'><strong>Failed:</strong> {summary['failed']}</p>\n")
            f.write(f"    <p class='skipped'><strong>Skipped:</strong> {summary['skipped']}</p>\n")
            f.write(f"    <p class='not-run'><strong>Not Run:</strong> {summary['not_run']}</p>\n")
            f.write("  </div>\n")
            
            # Group results by category
            results_by_category = {}
            for result in self.results:
                if result.category not in results_by_category:
                    results_by_category[result.category] = []
                results_by_category[result.category].append(result)
            
            f.write("  <h2>Detailed Results</h2>\n")
            
            for category, results in results_by_category.items():
                f.write(f"  <h3>{category}</h3>\n")
                
                f.write("  <table>\n")
                f.write("    <tr><th>Test</th><th>Status</th><th>Duration</th><th>Details</th></tr>\n")
                
                for result in results:
                    duration_str = (
                        f"{result.duration:.2f}s" 
                        if result.duration is not None 
                        else "N/A"
                    )
                    
                    status_class = (
                        "success" if result.status == "Success" 
                        else "failure" if result.status == "Failed" 
                        else "skipped" if result.status == "Skipped" 
                        else "not-run"
                    )
                    
                    details = result.details[:100] + "..." if len(result.details) > 100 else result.details
                    
                    f.write("    <tr>\n")
                    f.write(f"      <td>{result.name}</td>\n")
                    f.write(f"      <td class='{status_class}'>{result.status}</td>\n")
                    f.write(f"      <td>{duration_str}</td>\n")
                    f.write(f"      <td>{details}</td>\n")
                    f.write("    </tr>\n")
                
                f.write("  </table>\n")
            
            # Add footer with links to verification documents
            f.write("  <div class='footer'>\n")
            f.write("    <p><strong>Related Documents</strong>:</p>\n")
            f.write("    <ul>\n")
            f.write("      <li><a href='../docs/developer/release_verification.md'>Release Verification</a></li>\n")
            f.write("      <li><a href='../docs/developer/final_qa_checklist.md'>Final QA Checklist</a></li>\n")
            f.write("      <li><a href='../docs/developer/test_plan.md'>Test Plan</a></li>\n")
            f.write("    </ul>\n")
            f.write("  </div>\n")
            
            f.write("</body>\n")
            f.write("</html>\n")
        
        log_info(f"Wrote HTML report to {report_file}")
        return report_file


def run_verification_tests(args: argparse.Namespace) -> VerificationReport:
    """Run the verification tests and return results."""
    version = args.version
    output_dir = Path(args.output_dir)
    
    # Initialize report
    report = VerificationReport(version, output_dir)
    
    # Check requirements
    req_result = VerificationResult("Requirements Check", "Environment")
    req_result.start()
    if check_requirements():
        req_result.succeed("All required tools are installed")
    else:
        req_result.fail("Missing required tools")
    report.add_result(req_result)
    
    # Check version consistency
    version_result = VerificationResult("Version Consistency", "Code and Version")
    version_result.start()
    if not args.skip_check:
        if check_version_in_files(version):
            version_result.succeed("Version numbers are consistent across all files")
        else:
            version_result.fail("Version numbers are inconsistent across files")
    else:
        version_result.skip("Version check skipped")
    report.add_result(version_result)
    
    # Check documentation
    docs_result = VerificationResult("Documentation", "Documentation")
    docs_result.start()
    if not args.skip_docs:
        if check_documentation(version):
            docs_result.succeed("Documentation is up to date")
        else:
            docs_result.fail("Documentation needs updating")
    else:
        docs_result.skip("Documentation check skipped")
    report.add_result(docs_result)
    
    # Run linting
    lint_result = VerificationResult("Linting", "Tests")
    lint_result.start()
    if not args.skip_tests:
        if run_linting():
            lint_result.succeed("Linting checks passed")
        else:
            lint_result.fail("Linting checks failed")
    else:
        lint_result.skip("Linting skipped")
    report.add_result(lint_result)
    
    # Run unit tests
    unit_result = VerificationResult("Unit Tests", "Tests")
    unit_result.start()
    if not args.skip_tests:
        if run_tests("unit"):
            unit_result.succeed("Unit tests passed")
        else:
            unit_result.fail("Unit tests failed")
    else:
        unit_result.skip("Unit tests skipped")
    report.add_result(unit_result)
    
    # Run integration tests
    integration_result = VerificationResult("Integration Tests", "Tests")
    integration_result.start()
    if not args.skip_tests:
        if run_tests("integration"):
            integration_result.succeed("Integration tests passed")
        else:
            integration_result.fail("Integration tests failed")
    else:
        integration_result.skip("Integration tests skipped")
    report.add_result(integration_result)
    
    # Build for current platform
    current_platform = platform.system().lower()
    if current_platform == "darwin":
        current_platform = "macos"
    
    build_result = VerificationResult(f"{current_platform.capitalize()} Build", "Build")
    build_result.start()
    if not args.skip_build:
        if build_platform(current_platform, version):
            build_result.succeed(f"Successfully built for {current_platform}")
        else:
            build_result.fail(f"Failed to build for {current_platform}")
    else:
        build_result.skip("Build skipped")
    report.add_result(build_result)
    
    # Generate artifacts
    artifacts_result = VerificationResult("Release Artifacts", "Build")
    artifacts_result.start()
    if not args.skip_build and build_result.status == "Success":
        if create_release_artifacts(version):
            artifacts_result.succeed("Release artifacts created successfully")
        else:
            artifacts_result.fail("Failed to create release artifacts")
    else:
        artifacts_result.skip("Artifact generation skipped")
    report.add_result(artifacts_result)
    
    return report


def copy_verification_docs(output_dir: Path) -> None:
    """Copy verification documents to the output directory."""
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # List of docs to copy
    docs_to_copy = [
        (VERIFICATION_DOC, "release_verification.md"),
        (QA_CHECKLIST, "final_qa_checklist.md"),
        (TEST_PLAN, "test_plan.md"),
    ]
    
    for src, dst in docs_to_copy:
        if src.exists():
            shutil.copy2(src, docs_dir / dst)
            log_info(f"Copied {src} to {docs_dir / dst}")
        else:
            log_warning(f"Could not find {src}")


def generate_verification_checklist(output_dir: Path, version: str) -> None:
    """Generate a verification checklist based on the release verification doc."""
    if not VERIFICATION_DOC.exists():
        log_warning(f"Could not find {VERIFICATION_DOC}")
        return
    
    checklist_file = output_dir / f"Scout_{version}_Verification_Checklist.md"
    
    with open(VERIFICATION_DOC, "r", encoding="utf-8") as src:
        content = src.read()
    
    # Add header and instructions
    checklist_content = f"""# Scout {version} Verification Checklist

**Generated on:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This checklist is generated from the [Release Verification](../docs/developer/release_verification.md) document.
Use this document to track your progress through the verification process.

Instructions:
1. Check off items as you complete them
2. Add notes for any issues or observations
3. For any failures, record them in the Issue Summary section
4. Once all sections are complete, add your signature to the sign-off section

"""
    # Add the original content (without the title)
    lines = content.split('\n')
    checklist_content += '\n'.join(lines[1:])
    
    with open(checklist_file, "w", encoding="utf-8") as dst:
        dst.write(checklist_content)
    
    log_info(f"Generated verification checklist at {checklist_file}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Scout Release Verification Tool")
    parser.add_argument("--version", default=DEFAULT_VERSION, help=f"Version to verify (default: {DEFAULT_VERSION})")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to store verification results")
    parser.add_argument("--skip-build", action="store_true", help="Skip building executables")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-docs", action="store_true", help="Skip documentation checks")
    parser.add_argument("--skip-check", action="store_true", help="Skip version checks")
    
    args = parser.parse_args()
    
    # Convert output_dir to Path
    args.output_dir = Path(args.output_dir) / f"verification_{args.version}_{TIMESTAMP}"
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Print header
    print(f"\n{'='*80}")
    print(f"Scout {args.version} Release Verification")
    print(f"{'='*80}\n")
    
    # Run verification tests
    report = run_verification_tests(args)
    
    # Write reports
    report.write_json_report()
    report.write_markdown_report()
    report.write_html_report()
    
    # Copy verification documents
    copy_verification_docs(args.output_dir)
    
    # Generate verification checklist
    generate_verification_checklist(args.output_dir, args.version)
    
    # Print summary
    summary = report.get_summary()
    
    print(f"\n{'='*80}")
    print(f"Verification Summary")
    print(f"{'='*80}")
    print(f"Total Tests:  {summary['total']}")
    print(f"Succeeded:    {summary['succeeded']} ({summary['success_rate']}%)")
    print(f"Failed:       {summary['failed']}")
    print(f"Skipped:      {summary['skipped']}")
    print(f"Not Run:      {summary['not_run']}")
    print(f"{'='*80}")
    print(f"Results saved to: {args.output_dir}")
    print(f"{'='*80}\n")
    
    # Return exit code based on success rate
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main()) 