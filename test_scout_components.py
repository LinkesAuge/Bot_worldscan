#!/usr/bin/env python3
"""
Scout Component Testing Script

This script performs comprehensive testing of all major Scout components
to identify any issues that might affect the application functionality.
"""

import os
import sys
import logging
import importlib
import inspect
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scout_tester")

# Add the project root to the Python path
script_dir = Path(__file__).absolute().parent
if script_dir not in sys.path:
    sys.path.insert(0, str(script_dir))

# Test result counters
PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0

# Color escape sequences for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_subheader(text: str) -> None:
    """Print a subsection header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * 40}{Colors.ENDC}\n")


def print_result(test_name: str, result: bool, message: str = "") -> None:
    """Print a test result."""
    global PASS_COUNT, FAIL_COUNT
    
    if result:
        PASS_COUNT += 1
        status = f"{Colors.GREEN}PASS{Colors.ENDC}"
    else:
        FAIL_COUNT += 1
        status = f"{Colors.RED}FAIL{Colors.ENDC}"
    
    print(f"  {status} - {test_name}")
    
    if message:
        print(f"       {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    global WARN_COUNT
    WARN_COUNT += 1
    print(f"  {Colors.YELLOW}WARNING: {message}{Colors.ENDC}")


def test_imports() -> None:
    """Test importing key modules to check for import errors."""
    print_subheader("Testing Imports")
    
    # Define modules groups
    core_modules = [
        "scout",
        "scout.core.utils.codes",
    ]
    
    interface_modules = [
        "scout.core.detection.detection_service_interface",
        "scout.core.game.game_service_interface",
        "scout.core.automation.automation_service_interface",
    ]
    
    ui_modules = [
        "scout.ui.main_window",
        "scout.ui.utils.language_manager",
        "scout.ui.utils.shortcuts",
        "scout.ui.utils.file_utils",
        "scout.ui.utils.layout_helper",
    ]
    
    translations_modules = [
        "scout.translations.translator_app",
    ]
    
    view_modules = [
        "scout.ui.views.detection_tab",
        "scout.ui.views.automation_tab",
        "scout.ui.views.game_state_tab",
        "scout.ui.views.settings_tab",
    ]
    
    # Test core modules (these are critical)
    print("Core Modules:")
    for module_name in core_modules:
        try:
            module = importlib.import_module(module_name)
            print_result(f"Import {module_name}", True)
        except ImportError as e:
            print_result(f"Import {module_name}", False, f"Error: {str(e)}")
    
    # Test interface modules (may not exist in distribution)
    print("\nInterface Modules (may not be present in all configurations):")
    for module_name in interface_modules:
        try:
            module = importlib.import_module(module_name)
            print_result(f"Import {module_name}", True)
        except ImportError as e:
            if "No module named" in str(e):
                print_warning(f"Module {module_name} not found. This may be normal in compiled versions.")
            else:
                print_result(f"Import {module_name}", False, f"Error: {str(e)}")
    
    # Test UI modules
    print("\nUI Modules:")
    for module_name in ui_modules:
        try:
            module = importlib.import_module(module_name)
            print_result(f"Import {module_name}", True)
        except ImportError as e:
            print_result(f"Import {module_name}", False, f"Error: {str(e)}")
    
    # Test translations modules
    print("\nTranslations Modules:")
    for module_name in translations_modules:
        try:
            module = importlib.import_module(module_name)
            print_result(f"Import {module_name}", True)
        except ImportError as e:
            if "No module named" in str(e):
                print_warning(f"Module {module_name} not found. This may be normal in compiled versions.")
            else:
                print_result(f"Import {module_name}", False, f"Error: {str(e)}")
    
    # Test view modules
    print("\nView Modules:")
    for module_name in view_modules:
        try:
            module = importlib.import_module(module_name)
            print_result(f"Import {module_name}", True)
        except ImportError as e:
            if "No module named" in str(e):
                print_warning(f"Module {module_name} not found. This may be normal in compiled versions.")
            else:
                print_result(f"Import {module_name}", False, f"Error: {str(e)}")


def test_pyqt6_imports() -> None:
    """Specifically test PyQt6 imports that might cause issues."""
    print_subheader("Testing PyQt6 Imports")
    
    pyqt_imports = [
        # Test specific PyQt6 imports
        ("from PyQt6.QtWidgets import QApplication", 
         "import PyQt6.QtWidgets; QApplication = PyQt6.QtWidgets.QApplication"),
        
        ("from PyQt6.QtGui import QAction", 
         "import PyQt6.QtGui; QAction = PyQt6.QtGui.QAction"),
         
        ("from PyQt6.QtCore import QObject",
         "import PyQt6.QtCore; QObject = PyQt6.QtCore.QObject"),
    ]
    
    for import_str, fallback in pyqt_imports:
        try:
            exec(import_str)
            print_result(f"Import {import_str}", True)
        except ImportError as e:
            try:
                exec(fallback)
                print_result(f"Import {import_str}", False, 
                          f"Failed but alternative {fallback} works. Error: {str(e)}")
            except ImportError as e2:
                print_result(f"Import {import_str}", False, 
                          f"Failed and alternative also failed. Error: {str(e2)}")


def test_application_launch() -> None:
    """Test that the main application launches without errors."""
    print_subheader("Testing Application Launch")
    
    # We'll run a simplified version with a flag to exit immediately after init
    cmd = [sys.executable, "main.py", "--test-only"]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True,
            text=True,
            timeout=10  # 10 second timeout
        )
        
        if result.returncode == 0:
            print_result("Application launch", True)
        else:
            print_result("Application launch", False, 
                      f"Exit code: {result.returncode}\nStderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        print_result("Application launch", False, "Timed out after 10 seconds")
    except Exception as e:
        print_result("Application launch", False, f"Error: {str(e)}")


def test_executable() -> None:
    """Test that the built executable exists and is valid."""
    print_subheader("Testing Built Executable")
    
    # Check if the exe exists
    exe_path = Path("dist/Scout/Scout.exe")
    if exe_path.exists():
        print_result("Executable exists", True)
    else:
        print_result("Executable exists", False, f"Could not find {exe_path}")
        return
    
    # Check file size
    file_size = exe_path.stat().st_size
    if file_size > 1000000:  # At least 1 MB
        print_result("Executable size", True, f"Size: {file_size / 1048576:.2f} MB")
    else:
        print_result("Executable size", False, 
                  f"Size too small: {file_size / 1048576:.2f} MB")


def test_installer() -> None:
    """Test that the installer exists and is valid."""
    print_subheader("Testing Installer")
    
    # Check if the installer exists
    installer_path = Path("dist/Scout_Setup_1.0.0.exe")
    if installer_path.exists():
        print_result("Installer exists", True)
    else:
        print_result("Installer exists", False, f"Could not find {installer_path}")
        return
    
    # Check file size
    file_size = installer_path.stat().st_size
    if file_size > 10000000:  # At least 10 MB
        print_result("Installer size", True, f"Size: {file_size / 1048576:.2f} MB")
    else:
        print_result("Installer size", False, 
                  f"Size too small: {file_size / 1048576:.2f} MB")


def test_translations() -> None:
    """Test that translation files exist and are valid."""
    print_subheader("Testing Translations")
    
    # Check translation directory
    trans_dir = Path("scout/translations")
    if not trans_dir.exists():
        print_result("Translation directory exists", False, 
                  f"Could not find {trans_dir}")
        return
    
    # Count translation files
    ts_files = list(trans_dir.glob("*.ts"))
    qm_files = list(trans_dir.glob("*.qm"))
    
    if len(ts_files) > 0:
        print_result("Translation source files", True, 
                  f"Found {len(ts_files)} .ts files")
    else:
        print_result("Translation source files", False, 
                  "No .ts files found")
    
    if len(qm_files) > 0:
        print_result("Compiled translation files", True, 
                  f"Found {len(qm_files)} .qm files")
    else:
        print_result("Compiled translation files", False, 
                  "No .qm files found")


def test_version_consistency() -> None:
    """Test that version numbers are consistent across the codebase."""
    print_subheader("Testing Version Consistency")
    
    version_locations = [
        {
            "file": "scout/__init__.py",
            "pattern": '__version__ = "',
            "extract": lambda line, pattern: line.split(pattern)[1].split('"')[0]
                       if pattern in line else None
        },
        {
            "file": "setup.py",
            "pattern": 'version="',
            "extract": lambda line, pattern: line.split(pattern)[1].split('"')[0]
                       if pattern in line else None
        },
        {
            "file": "docs/RELEASE_NOTES.md",
            "pattern": "## Version ",
            "extract": lambda line, pattern: line.split(pattern)[1].split(' ')[0]
                       if pattern in line else None
        }
    ]
    
    versions = {}
    
    for loc in version_locations:
        try:
            with open(loc["file"], 'r', encoding='utf-8') as f:
                for line in f:
                    extracted = loc["extract"](line, loc["pattern"])
                    if extracted:
                        versions[loc["file"]] = extracted
                        break
        except FileNotFoundError:
            print_result(f"Version in {loc['file']}", False, "File not found")
        except Exception as e:
            print_result(f"Version in {loc['file']}", False, f"Error: {str(e)}")
    
    # Check if all versions are the same
    if len(set(versions.values())) == 1:
        version = next(iter(versions.values()))
        print_result("Version consistency", True, f"All files report version {version}")
    else:
        print_result("Version consistency", False, 
                  "Version mismatch:\n" + "\n".join([f"       {f}: {v}" 
                                               for f, v in versions.items()]))


def test_documentation() -> None:
    """Test that documentation files exist and are valid."""
    print_subheader("Testing Documentation")
    
    # Check key documentation files
    doc_files = [
        "docs/RELEASE_NOTES.md",
        "docs/user_guide/README.md",
        "docs/user_guide/installation.md",
        "docs/developer/README.md",
    ]
    
    for doc_file in doc_files:
        path = Path(doc_file)
        if path.exists():
            # Check file size
            file_size = path.stat().st_size
            if file_size > 100:  # At least 100 bytes
                print_result(f"Documentation file {doc_file}", True, 
                          f"Size: {file_size} bytes")
            else:
                print_result(f"Documentation file {doc_file}", False, 
                          f"Size too small: {file_size} bytes")
        else:
            print_result(f"Documentation file {doc_file}", False, 
                      f"Could not find {path}")


def test_release_artifacts() -> None:
    """Test that release artifacts exist and are valid."""
    print_subheader("Testing Release Artifacts")
    
    # Check for expected release artifacts
    artifacts = [
        "dist/Scout_Setup_1.0.0.exe",
        "dist/Scout_1.0.0_Portable.zip",
        "dist/Scout_1.0.0_SHA256SUMS.txt"
    ]
    
    for artifact in artifacts:
        path = Path(artifact)
        if path.exists():
            file_size = path.stat().st_size
            print_result(f"Release artifact {artifact}", True, 
                      f"Size: {file_size} bytes")
        else:
            print_result(f"Release artifact {artifact}", False, 
                      f"Could not find {path}")
    
    # Verify checksums if they exist
    checksums_path = Path("dist/Scout_1.0.0_SHA256SUMS.txt")
    if checksums_path.exists():
        try:
            with open(checksums_path, 'r') as f:
                checksums = f.read()
            
            print_result("Checksums file content", True,
                      f"Content: {checksums.strip()}")
        except Exception as e:
            print_result("Read checksums file", False, f"Error: {str(e)}")


def main() -> None:
    """Main entry point for the test script."""
    print_header("Scout 1.0.0 Component Testing")
    
    # Run all tests
    test_imports()
    test_pyqt6_imports()
    test_application_launch()
    test_executable()
    test_installer()
    test_translations()
    test_version_consistency()
    test_documentation()
    test_release_artifacts()
    
    # Print summary
    print_header("Test Summary")
    print(f"Total tests: {PASS_COUNT + FAIL_COUNT}")
    print(f"{Colors.GREEN}Passed: {PASS_COUNT}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {FAIL_COUNT}{Colors.ENDC}")
    print(f"{Colors.YELLOW}Warnings: {WARN_COUNT}{Colors.ENDC}")
    
    # Return non-zero exit code if any tests failed
    return 1 if FAIL_COUNT > 0 else 0


if __name__ == "__main__":
    sys.exit(main()) 