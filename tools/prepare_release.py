#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scout Release Preparation Script

This script automates the final steps in preparing a release of the Scout application,
including version verification, build checks, and packaging.

Usage:
    python prepare_release.py [options]

Options:
    --version VERSION     Version to prepare (e.g., 1.0.0)
    --platforms PLATFORMS List of platforms to build for (windows,macos,linux), comma-separated
    --skip-tests          Skip running tests before building
    --skip-check          Skip checking version numbers in files
    --skip-docs           Skip documentation verification
    --build-only          Only build executables, skip other checks
    --help                Show this help message
"""

import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Constants
REPO_ROOT = Path(__file__).parent.parent.absolute()
BUILD_DIR = REPO_ROOT / "dist"
VERSION_PATTERN = r"\d+\.\d+\.\d+"
RELEASE_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# Files that should contain version numbers
VERSION_FILES = [
    "setup.py",
    "scout/__init__.py",
    "file_version_info.txt",
    "installer/scout_installer.nsi",
    "README.md",
    "docs/RELEASE_NOTES.md",
]

# Command configurations
COMMANDS = {
    "tests": {
        "all": ["pytest", "tests"],
        "unit": ["pytest", "tests/core", "tests/ui"],
        "integration": ["python", "-m", "tests.integration.run_integration_tests"],
    },
    "build": {
        "windows": ["pyinstaller", "scout.spec"],
        "macos": ["python", "tools/build_macos.py"],
        "linux": ["python", "tools/build_linux.py"],
    },
    "linting": {
        "ruff": ["ruff", "check", "scout"],
        "mypy": ["mypy", "scout"],
    },
}

# Color definitions for terminal output
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
    """Print an informational message."""
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {message}")


def log_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} {message}")


def log_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}[WARNING]{Colors.ENDC} {message}")


def log_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}[ERROR]{Colors.ENDC} {message}")


def log_step(step: str) -> None:
    """Print a step header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {step} ==={Colors.ENDC}")


def check_requirements() -> bool:
    """Check that all required tools are installed."""
    log_step("Checking requirements")
    
    required_tools = {
        "python": "Python interpreter",
        "pip": "Python package manager",
        "pytest": "Python testing framework",
        "pyinstaller": "Python executable packager",
        "git": "Version control system",
    }
    
    missing_tools = []
    
    for tool, description in required_tools.items():
        try:
            # Use 'where' on Windows, 'which' on Unix
            which_cmd = "where" if platform.system() == "Windows" else "which"
            subprocess.check_call(
                [which_cmd, tool], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            log_info(f"Found {tool} ({description})")
        except (subprocess.CalledProcessError, FileNotFoundError):
            log_error(f"Missing {tool} ({description})")
            missing_tools.append(tool)
    
    if missing_tools:
        log_error("Missing required tools. Please install them before continuing.")
        return False
    
    log_success("All required tools are installed")
    return True


def run_command(command: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Command failed with exit code {e.returncode}\n{e.stderr}"


def check_version_in_files(version: str) -> bool:
    """Check that the version number is consistent across all files."""
    log_step(f"Checking version {version} in files")
    
    all_correct = True
    
    for file_path in VERSION_FILES:
        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            log_warning(f"File {file_path} not found, skipping version check")
            continue
        
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if version in content:
            log_info(f"Version {version} found in {file_path}")
        else:
            log_error(f"Version {version} NOT found in {file_path}")
            all_correct = False
    
    if all_correct:
        log_success("Version numbers are consistent across all files")
    else:
        log_error("Version numbers are inconsistent. Please update all files to version " + version)
    
    return all_correct


def run_tests(test_type: str = "all") -> bool:
    """Run the specified tests."""
    log_step(f"Running {test_type} tests")
    
    if test_type not in COMMANDS["tests"]:
        log_error(f"Unknown test type: {test_type}")
        return False
    
    command = COMMANDS["tests"][test_type]
    log_info(f"Running command: {' '.join(command)}")
    
    success, output = run_command(command)
    
    if success:
        log_success(f"{test_type.capitalize()} tests passed")
        return True
    else:
        log_error(f"{test_type.capitalize()} tests failed:\n{output}")
        return False


def run_linting() -> bool:
    """Run linting checks."""
    log_step("Running linting checks")
    
    all_passed = True
    
    for linter, command in COMMANDS["linting"].items():
        log_info(f"Running {linter}...")
        success, output = run_command(command)
        
        if success:
            log_success(f"{linter.capitalize()} checks passed")
        else:
            log_error(f"{linter.capitalize()} checks failed:\n{output}")
            all_passed = False
    
    return all_passed


def build_platform(platform_name: str, version: str) -> bool:
    """Build the application for the specified platform."""
    log_step(f"Building for {platform_name}")
    
    if platform_name not in COMMANDS["build"]:
        log_error(f"Unknown platform: {platform_name}")
        return False
    
    # Check if we can build for this platform
    current_platform = platform.system().lower()
    cross_platform_build = platform_name != current_platform
    
    if cross_platform_build:
        log_warning(f"Building for {platform_name} from {current_platform} (cross-platform build)")
        
        # Special handling for cross-platform builds
        if platform_name == "macos" and current_platform == "windows":
            log_error("Cannot build macOS package from Windows")
            return False
        elif platform_name == "linux" and current_platform == "windows":
            # We can build Linux from Windows using WSL, but we need to check if it's available
            log_warning("Building Linux package from Windows requires Windows Subsystem for Linux (WSL)")
            wsl_check, wsl_output = run_command(["wsl", "--status"])
            if not wsl_check:
                log_error("WSL is not available. Cannot build Linux package from Windows")
                return False
    
    # Build package
    command = COMMANDS["build"][platform_name]
    log_info(f"Running command: {' '.join(command)}")
    
    success, output = run_command(command)
    
    if success:
        log_success(f"Successfully built for {platform_name}")
        
        # Verify build artifacts
        if platform_name == "windows":
            exe_path = BUILD_DIR / "Scout" / "Scout.exe"
            if exe_path.exists():
                log_success(f"Found Windows executable at {exe_path}")
            else:
                log_error(f"Windows executable not found at {exe_path}")
                success = False
        
        elif platform_name == "macos":
            app_path = BUILD_DIR / "Scout.app"
            if app_path.exists():
                log_success(f"Found macOS application bundle at {app_path}")
            else:
                log_error(f"macOS application bundle not found at {app_path}")
                success = False
        
        elif platform_name == "linux":
            appimage_path = BUILD_DIR / f"Scout-{version}-x86_64.AppImage"
            deb_path = BUILD_DIR / f"scout_{version}_amd64.deb"
            
            if appimage_path.exists():
                log_success(f"Found Linux AppImage at {appimage_path}")
            else:
                log_warning(f"Linux AppImage not found at {appimage_path}")
            
            if deb_path.exists():
                log_success(f"Found Linux Debian package at {deb_path}")
            else:
                log_warning(f"Linux Debian package not found at {deb_path}")
            
            if not appimage_path.exists() and not deb_path.exists():
                log_error("No Linux build artifacts found")
                success = False
    
    else:
        log_error(f"Build for {platform_name} failed:\n{output}")
    
    return success


def check_documentation(version: str) -> bool:
    """Check that documentation is up to date."""
    log_step("Checking documentation")
    
    # Files that must contain the current version
    doc_files = [
        "docs/RELEASE_NOTES.md",
        "docs/user_guide/whats_new.md",
        "docs/user_guide/installation.md",
    ]
    
    all_updated = True
    
    for file_path in doc_files:
        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            log_warning(f"File {file_path} not found, skipping documentation check")
            continue
        
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if version in content and RELEASE_DATE in content:
            log_info(f"File {file_path} contains current version and date")
        elif version in content:
            log_warning(f"File {file_path} contains version {version} but not today's date ({RELEASE_DATE})")
        else:
            log_error(f"File {file_path} does not contain current version {version}")
            all_updated = False
    
    # Check for placeholder text
    placeholder_patterns = [
        r"TODO",
        r"FIXME",
        r"XXX",
        r"\[.*?\]\(#\)",  # Links with # as href
    ]
    
    docs_dir = REPO_ROOT / "docs"
    for pattern in placeholder_patterns:
        grep_cmd = ["grep", "-r", "-l", pattern, "."]
        success, output = run_command(grep_cmd, cwd=docs_dir)
        
        if success and output.strip():
            log_warning(f"Found potential placeholder text ({pattern}) in these files:")
            for line in output.strip().split("\n"):
                log_warning(f"  - {line}")
            all_updated = False
    
    if all_updated:
        log_success("Documentation is up to date")
    else:
        log_error("Documentation needs updating")
    
    return all_updated


def create_release_artifacts(version: str) -> bool:
    """Create release artifacts like checksums and archives."""
    log_step("Creating release artifacts")
    
    artifacts_dir = BUILD_DIR / "release_artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    # Files to include in the checksum file
    checksum_targets = []
    
    # Find all relevant build artifacts
    for item in BUILD_DIR.glob("*"):
        if item.name == "release_artifacts":
            continue
            
        if item.is_dir():
            if item.name == "Scout" and (item / "Scout.exe").exists():
                # Create Windows ZIP archive
                zip_path = artifacts_dir / f"Scout_{version}_Windows_Portable.zip"
                log_info(f"Creating Windows portable ZIP: {zip_path}")
                
                if platform.system() == "Windows":
                    # Use PowerShell for better compression
                    cmd = [
                        "powershell", "-Command",
                        f"Compress-Archive -Path '{item}' -DestinationPath '{zip_path}' -Force"
                    ]
                else:
                    # Use zip command
                    cmd = ["zip", "-r", str(zip_path), str(item)]
                
                success, output = run_command(cmd)
                if success:
                    log_success(f"Created {zip_path}")
                    checksum_targets.append(zip_path)
                else:
                    log_error(f"Failed to create ZIP archive: {output}")
        else:
            # Copy the artifact to the release directory
            dest_path = artifacts_dir / item.name
            log_info(f"Copying {item} to {dest_path}")
            shutil.copy2(item, dest_path)
            checksum_targets.append(dest_path)
    
    # Create checksum file
    checksum_file = artifacts_dir / f"Scout_{version}_SHA256SUMS.txt"
    with open(checksum_file, "w", encoding="utf-8") as f:
        for target in checksum_targets:
            if platform.system() == "Windows":
                cmd = ["powershell", "-Command", f"Get-FileHash '{target}' -Algorithm SHA256 | Select-Object -ExpandProperty Hash"]
            else:
                cmd = ["shasum", "-a", "256", str(target)]
            
            success, output = run_command(cmd)
            if success:
                if platform.system() == "Windows":
                    # Format the output to match the standard checksum format
                    checksum = output.strip()
                    f.write(f"{checksum} *{target.name}\n")
                else:
                    f.write(output)
                log_info(f"Generated checksum for {target.name}")
            else:
                log_error(f"Failed to generate checksum for {target.name}: {output}")
                return False
    
    log_success(f"Created checksum file at {checksum_file}")
    
    # Create a JSON file with release info
    release_info = {
        "version": version,
        "release_date": RELEASE_DATE,
        "artifacts": [path.name for path in checksum_targets],
        "checksum_file": checksum_file.name
    }
    
    release_info_file = artifacts_dir / f"Scout_{version}_release_info.json"
    with open(release_info_file, "w", encoding="utf-8") as f:
        json.dump(release_info, f, indent=2)
    
    log_success(f"Created release info file at {release_info_file}")
    
    log_success("Release artifacts created successfully")
    log_info(f"All release artifacts are available in: {artifacts_dir}")
    
    return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Scout Release Preparation Tool")
    parser.add_argument("--version", default="1.0.0", help="Version to prepare (e.g., 1.0.0)")
    parser.add_argument("--platforms", default="windows,macos,linux", help="Platforms to build for (comma-separated)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-check", action="store_true", help="Skip checking version numbers")
    parser.add_argument("--skip-docs", action="store_true", help="Skip documentation verification")
    parser.add_argument("--build-only", action="store_true", help="Only build executables")
    
    args = parser.parse_args()
    
    # Extract parameters
    version = args.version
    platforms = args.platforms.split(",")
    
    # Show script header
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("=" * 80)
    print(f"Scout Release Preparation Script - v{version}")
    print(f"Date: {RELEASE_DATE}")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Build-only mode skips checks and tests
    if args.build_only:
        args.skip_tests = True
        args.skip_check = True
        args.skip_docs = True
    
    # Check version numbers in files
    if not args.skip_check:
        if not check_version_in_files(version):
            if input("Continue anyway? (y/n): ").lower() != "y":
                return 1
    
    # Check documentation
    if not args.skip_docs:
        if not check_documentation(version):
            if input("Continue anyway? (y/n): ").lower() != "y":
                return 1
    
    # Run tests
    if not args.skip_tests:
        if not run_linting():
            if input("Linting failed. Continue anyway? (y/n): ").lower() != "y":
                return 1
        
        if not run_tests("unit"):
            if input("Unit tests failed. Continue anyway? (y/n): ").lower() != "y":
                return 1
        
        if not run_tests("integration"):
            if input("Integration tests failed. Continue anyway? (y/n): ").lower() != "y":
                return 1
    
    # Build for each platform
    build_results = {}
    for platform_name in platforms:
        platform_name = platform_name.strip().lower()
        if not platform_name:
            continue
            
        result = build_platform(platform_name, version)
        build_results[platform_name] = result
        
        if not result:
            if input(f"Build for {platform_name} failed. Continue with other platforms? (y/n): ").lower() != "y":
                return 1
    
    # Create release artifacts
    if any(build_results.values()):
        create_release_artifacts(version)
    
    # Show summary
    log_step("Release Preparation Summary")
    
    print(f"{Colors.BOLD}Version:{Colors.ENDC} {version}")
    print(f"{Colors.BOLD}Date:{Colors.ENDC} {RELEASE_DATE}")
    print(f"{Colors.BOLD}Platforms:{Colors.ENDC}")
    
    for platform_name, result in build_results.items():
        status = f"{Colors.GREEN}SUCCESS{Colors.ENDC}" if result else f"{Colors.RED}FAILED{Colors.ENDC}"
        print(f"  - {platform_name}: {status}")
    
    print("\nNext steps:")
    print("1. Review and finalize release notes")
    print("2. Create a GitHub release with the generated artifacts")
    print("3. Test the installers on clean systems")
    print("4. Announce the release")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 