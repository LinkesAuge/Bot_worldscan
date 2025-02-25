#!/usr/bin/env python3
"""
Scout macOS Build Script

This script creates a standalone macOS application bundle (.app) and disk image (.dmg)
for the Scout application. It handles dependency collection, resource bundling, and
DMG creation.
"""

import os
import sys
import shutil
import subprocess
import argparse
import plistlib
from pathlib import Path
from typing import Dict, List, Any, Optional

# Script configuration
APP_NAME = "Scout"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "main.py"
ICON_PATH = "resources/icons/scout.icns"  # Note: macOS uses .icns format
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
    "--target-architecture=universal2",  # Build for both Intel and Apple Silicon
    "--osx-bundle-identifier=com.scoutteam.scout",  # Bundle identifier
    "{main_script}"
]

# Info.plist template
INFO_PLIST_TEMPLATE = {
    "CFBundleName": APP_NAME,
    "CFBundleDisplayName": APP_NAME,
    "CFBundleIdentifier": "com.scoutteam.scout",
    "CFBundleVersion": APP_VERSION,
    "CFBundleShortVersionString": APP_VERSION,
    "CFBundleExecutable": APP_NAME,
    "CFBundleIconFile": os.path.basename(ICON_PATH),
    "CFBundlePackageType": "APPL",
    "CFBundleInfoDictionaryVersion": "6.0",
    "CFBundleSupportedPlatforms": ["MacOSX"],
    "LSMinimumSystemVersion": "10.13.0",  # High Sierra minimum
    "NSHighResolutionCapable": True,
    "NSRequiresAquaSystemAppearance": False,  # Support dark mode
    "NSHumanReadableCopyright": "Copyright © 2025 ScoutTeam",
    "CFBundleDocumentTypes": [
        {
            "CFBundleTypeExtensions": ["scout"],
            "CFBundleTypeName": "Scout Document",
            "CFBundleTypeRole": "Editor",
            "LSHandlerRank": "Owner",
        }
    ],
}

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Build Scout application for macOS")
    parser.add_argument("--debug", action="store_true", help="Build with debug information")
    parser.add_argument("--skip-dmg", action="store_true", help="Skip DMG creation")
    parser.add_argument("--output-dir", type=str, default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--version", type=str, default=APP_VERSION, help="Application version")
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
    
    # Check for icon file (.icns format for macOS)
    icon_path = Path(ICON_PATH)
    if not icon_path.exists():
        print(f"Warning: Icon file '{ICON_PATH}' not found.")
        print("To create an .icns file, you'll need to use the macOS iconutil tool.")
        print("See the create_icns.sh script in the tools directory.")
    
    print("Build environment prepared.")

def check_macos_requirements():
    """Check if running on macOS with required tools."""
    if sys.platform != 'darwin':
        print("Error: This script must be run on macOS.")
        print("You're currently running on:", sys.platform)
        sys.exit(1)
    
    # Check for required tools
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: PyInstaller is not installed or not found in PATH.")
        print("Install it using: pip install pyinstaller")
        sys.exit(1)
    
    try:
        subprocess.run(["hdiutil", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: hdiutil command not found. This script requires macOS.")
        sys.exit(1)
    
    print("All required macOS tools are available.")

def create_icns_file():
    """Create .icns file from a PNG or other image format if it doesn't exist."""
    # This function is a placeholder - .icns creation requires macOS tools
    # Normally, we would have a shell script to create the .icns file using:
    # 1. Create .iconset directory with various icon sizes
    # 2. Use iconutil to convert iconset to icns
    
    icns_path = Path(ICON_PATH)
    if icns_path.exists():
        print(f"Icon file {ICON_PATH} already exists. Using existing file.")
        return
    
    print(f"Icon file {ICON_PATH} does not exist.")
    print("On macOS, you can create an .icns file with the following steps:")
    print("1. Create an iconset directory with properly sized PNG files")
    print("2. Run: iconutil -c icns <iconset_directory> -o scout.icns")
    
    # For now, we'll just show a warning since we can't create the file in our environment

def build_application(args):
    """Build the macOS application bundle using PyInstaller."""
    print(f"Building {APP_NAME} v{args.version} for macOS...")
    
    # Determine platform-specific separator
    sep = ":" # macOS uses colon
    
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
    
    # Set output directory
    cmd.append(f"--distpath={args.output_dir}")
    
    # Execute PyInstaller
    print("Running PyInstaller with the following command:")
    print(" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    
    if result.returncode != 0:
        print(f"Error: PyInstaller failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    
    print(f"Build completed successfully. Application bundle saved to {args.output_dir}/{APP_NAME}.app")

def update_info_plist(args):
    """Update the Info.plist file in the application bundle."""
    print("Updating Info.plist...")
    
    app_path = Path(args.output_dir) / f"{APP_NAME}.app"
    plist_path = app_path / "Contents" / "Info.plist"
    
    if not plist_path.exists():
        print(f"Error: Info.plist not found at {plist_path}")
        return False
    
    # Create a copy of the template and update with any arguments
    plist_data = INFO_PLIST_TEMPLATE.copy()
    plist_data["CFBundleVersion"] = args.version
    plist_data["CFBundleShortVersionString"] = args.version
    
    # Write the updated plist
    with open(plist_path, 'wb') as fp:
        plistlib.dump(plist_data, fp)
    
    print("Info.plist updated successfully.")
    return True

def copy_additional_files(args):
    """Copy additional files needed for the application."""
    print("Copying additional files...")
    
    app_path = Path(args.output_dir) / f"{APP_NAME}.app"
    resources_path = app_path / "Contents" / "Resources"
    
    # Copy LICENSE and README
    for file in ["LICENSE", "README.md"]:
        if Path(file).exists():
            shutil.copy(file, resources_path / file)
            print(f"Copied {file} to Resources")
    
    # Create empty templates directory for user templates
    templates_dir = resources_path / "templates"
    templates_dir.mkdir(exist_ok=True)
    print("Created templates directory")
    
    # Create logs directory for application logs
    logs_dir = resources_path / "logs"
    logs_dir.mkdir(exist_ok=True)
    print("Created logs directory")
    
    print("Additional files copied.")

def create_dmg(args):
    """Create a DMG disk image for the application."""
    if args.skip_dmg:
        print("Skipping DMG creation as requested.")
        return
    
    print("Creating DMG disk image...")
    
    app_path = Path(args.output_dir) / f"{APP_NAME}.app"
    dmg_path = Path(args.output_dir) / f"{APP_NAME}_{args.version}.dmg"
    
    # Remove existing DMG if it exists
    if dmg_path.exists():
        os.remove(dmg_path)
    
    # Create temporary DMG directory
    dmg_dir = Path(args.output_dir) / "dmg_temp"
    if dmg_dir.exists():
        shutil.rmtree(dmg_dir)
    dmg_dir.mkdir()
    
    # Copy application to DMG directory
    shutil.copytree(app_path, dmg_dir / f"{APP_NAME}.app")
    
    # Create symbolic link to Applications folder
    os.symlink("/Applications", dmg_dir / "Applications")
    
    # Create DMG from the directory
    cmd = [
        "hdiutil", "create",
        "-volname", APP_NAME,
        "-srcfolder", str(dmg_dir),
        "-ov", "-format", "UDZO",
        str(dmg_path)
    ]
    
    print("Running command:", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    
    if result.returncode != 0:
        print(f"Error: DMG creation failed with exit code {result.returncode}")
        return False
    
    # Clean up temporary directory
    shutil.rmtree(dmg_dir)
    
    print(f"DMG created successfully: {dmg_path}")
    return True

def main():
    """Main build script function."""
    args = parse_arguments()
    
    # Check if running on macOS
    check_macos_requirements()
    
    # Prepare environment
    prepare_build_environment()
    
    # Check for icon file
    create_icns_file()
    
    # Build the application
    build_application(args)
    
    # Update Info.plist
    update_info_plist(args)
    
    # Copy additional files
    copy_additional_files(args)
    
    # Create DMG
    create_dmg(args)
    
    print(f"\n{APP_NAME} v{args.version} macOS build completed successfully!")
    print(f"Application bundle is located in: {Path(args.output_dir).absolute() / f'{APP_NAME}.app'}")
    
    if not args.skip_dmg:
        print(f"DMG installer is located in: {Path(args.output_dir).absolute() / f'{APP_NAME}_{args.version}.dmg'}")

if __name__ == "__main__":
    main() 