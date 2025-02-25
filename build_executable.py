#!/usr/bin/env python3
"""
Scout Application Build Script

This script creates a standalone executable for the Scout application using PyInstaller.
It handles dependency collection, resource bundling, and configuration for the build process.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# Script configuration
APP_NAME = "Scout"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "main.py"
ICON_PATH = "resources/icons/scout.ico"
OUTPUT_DIR = "dist"

# PyInstaller command template
PYINSTALLER_CMD = [
    "pyinstaller",
    "--name={app_name}",
    "--icon={icon_path}",
    "--windowed",  # Don't open a console window
    "--noconfirm",  # Overwrite existing files
    "--clean",  # Clean PyInstaller cache before building
    "--add-data={translations_dir}{sep}translations",  # Include translations
    "--add-data={resources_dir}{sep}resources",  # Include resources
    "{main_script}"
]

# Files and directories to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dylib",
    "*.spec",
    "dist",
    "build",
    ".git",
    ".github",
    ".vscode",
    ".idea",
    "venv",
    "env",
    "docs",
    "tests",
]

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Build Scout application executable")
    parser.add_argument("--debug", action="store_true", help="Build with debug information")
    parser.add_argument("--onefile", action="store_true", help="Create a single file executable")
    parser.add_argument("--output-dir", type=str, default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--version", type=str, default=APP_VERSION, help="Application version")
    parser.add_argument("--tesseract", type=str, help="Path to Tesseract OCR executable")
    return parser.parse_args()

def prepare_build_environment():
    """Prepare the build environment."""
    print("Preparing build environment...")
    
    # Ensure output directory exists
    output_dir = Path(OUTPUT_DIR)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for required files
    main_script_path = Path(MAIN_SCRIPT)
    if not main_script_path.exists():
        print(f"Error: Main script '{MAIN_SCRIPT}' not found.")
        sys.exit(1)
    
    icon_path = Path(ICON_PATH)
    if not icon_path.exists():
        print(f"Warning: Icon file '{ICON_PATH}' not found. Using default icon.")
    
    print("Build environment prepared.")

def build_executable(args):
    """Build the executable using PyInstaller."""
    print(f"Building {APP_NAME} v{args.version} executable...")
    
    # Determine platform-specific separator
    sep = ";" if sys.platform == "win32" else ":"
    
    # Prepare PyInstaller command
    cmd = [
        arg.format(
            app_name=APP_NAME,
            icon_path=ICON_PATH if Path(ICON_PATH).exists() else "",
            translations_dir="scout/translations",
            resources_dir="resources",
            main_script=MAIN_SCRIPT,
            sep=sep
        )
        for arg in PYINSTALLER_CMD
    ]
    
    # Add command-line argument modifications
    if args.debug:
        cmd.append("--debug=all")
    
    if args.onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")
    
    # Add Tesseract path if provided
    if args.tesseract:
        if Path(args.tesseract).exists():
            cmd.append(f"--add-binary={args.tesseract}{sep}.")
            print(f"Including Tesseract OCR from: {args.tesseract}")
        else:
            print(f"Warning: Specified Tesseract path '{args.tesseract}' not found.")
    
    # Set output directory
    cmd.append(f"--distpath={args.output_dir}")
    
    # Execute PyInstaller
    print("Running PyInstaller with the following command:")
    print(" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    
    if result.returncode != 0:
        print(f"Error: PyInstaller failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    
    print(f"Build completed successfully. Executable saved to {args.output_dir}")

def copy_additional_files(args):
    """Copy additional files needed for the application."""
    print("Copying additional files...")
    
    # Determine the executable directory
    exe_dir = Path(args.output_dir) / APP_NAME
    if args.onefile:
        exe_dir = Path(args.output_dir)
    
    # Copy README and LICENSE
    for file in ["README.md", "LICENSE"]:
        if Path(file).exists():
            shutil.copy(file, exe_dir / file)
            print(f"Copied {file}")
    
    # Create an empty templates directory
    templates_dir = exe_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    print("Created templates directory")
    
    # Create logs directory
    logs_dir = exe_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    print("Created logs directory")
    
    print("Additional files copied.")

def main():
    """Main build script function."""
    args = parse_arguments()
    
    # Check if PyInstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: PyInstaller is not installed or not found in PATH.")
        print("Install it using: pip install pyinstaller")
        sys.exit(1)
    
    prepare_build_environment()
    build_executable(args)
    copy_additional_files(args)
    
    print(f"\n{APP_NAME} v{args.version} build completed successfully!")
    print(f"Executable is located in: {Path(args.output_dir).absolute()}")

if __name__ == "__main__":
    main() 