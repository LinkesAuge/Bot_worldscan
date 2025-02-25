#!/usr/bin/env python3
"""
Scout Linux Build Script

This script creates Linux packages (AppImage and Debian) for the Scout application.
It handles dependency collection, resource bundling, and package creation.
"""

import os
import sys
import shutil
import subprocess
import argparse
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

# Script configuration
APP_NAME = "Scout"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "main.py"
ICON_PATH = "resources/icons/scout.png"  # Linux uses PNG icons
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

# Desktop Entry file template
DESKTOP_ENTRY_TEMPLATE = """[Desktop Entry]
Name=Scout
Comment=Automation tool for Total Battle game
Exec={executable_path}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Utility;Game;
MimeType=application/x-scout;
Keywords=game;automation;scout;
"""

# Debian control file template
CONTROL_TEMPLATE = """Package: scout
Version: {version}
Architecture: amd64
Maintainer: ScoutTeam <info@scoutteam.com>
Installed-Size: {installed_size}
Depends: {dependencies}
Section: utils
Priority: optional
Homepage: https://scout-app.com
Description: Automation tool for Total Battle game
 Scout provides automation capabilities for the Total Battle game,
 including window detection, OCR recognition, and scripted actions.
 .
 Features:
  * Window detection and tracking
  * Template matching and OCR
  * Automation scripting
  * Game state monitoring
"""

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Build Scout application for Linux")
    parser.add_argument("--debug", action="store_true", help="Build with debug information")
    parser.add_argument("--output-dir", type=str, default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--version", type=str, default=APP_VERSION, help="Application version")
    parser.add_argument("--skip-appimage", action="store_true", help="Skip AppImage creation")
    parser.add_argument("--skip-deb", action="store_true", help="Skip Debian package creation")
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
    
    # Check for icon file
    icon_path = Path(ICON_PATH)
    if not icon_path.exists():
        print(f"Warning: Icon file '{ICON_PATH}' not found. Using default PyInstaller icon.")
    
    print("Build environment prepared.")

def check_linux_requirements():
    """Check if running on Linux with required tools."""
    if not sys.platform.startswith('linux'):
        print("Error: This script must be run on Linux.")
        print("You're currently running on:", sys.platform)
        sys.exit(1)
    
    # Check for required tools
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: PyInstaller is not installed or not found in PATH.")
        print("Install it using: pip install pyinstaller")
        sys.exit(1)
    
    if not Path("/usr/bin/dpkg-deb").exists() and not Path("/usr/bin/dpkg").exists():
        print("Warning: dpkg-deb not found. Debian package creation will be skipped.")
    
    try:
        appimagetool_path = shutil.which("appimagetool")
        if not appimagetool_path:
            print("Warning: appimagetool not found. AppImage creation will be skipped.")
            print("You can install it from: https://github.com/AppImage/AppImageKit/releases")
    except Exception:
        print("Warning: Unable to check for appimagetool. AppImage creation may fail.")
    
    print("Linux requirements checked.")

def build_application(args):
    """Build the Linux application using PyInstaller."""
    print(f"Building {APP_NAME} v{args.version} for Linux...")
    
    # Determine platform-specific separator
    sep = ":" if sys.platform != "win32" else ";"
    
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
    
    print(f"Build completed successfully. Application saved to {args.output_dir}/{APP_NAME}")

def copy_additional_files(args):
    """Copy additional files needed for the application."""
    print("Copying additional files...")
    
    # Directory where the PyInstaller output is located
    app_dir = Path(args.output_dir) / APP_NAME
    
    # Copy LICENSE and README
    for file in ["LICENSE", "README.md"]:
        if Path(file).exists():
            shutil.copy(file, app_dir / file)
            print(f"Copied {file}")
    
    # Create empty templates directory for user templates
    templates_dir = app_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    print("Created templates directory")
    
    # Create logs directory for application logs
    logs_dir = app_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    print("Created logs directory")
    
    # Create icon directory and copy the icon
    icon_path = Path(ICON_PATH)
    if icon_path.exists():
        icon_dir = app_dir / "icons"
        icon_dir.mkdir(exist_ok=True)
        shutil.copy(icon_path, icon_dir / icon_path.name)
        print(f"Copied icon to {icon_dir}")
    
    print("Additional files copied.")

def create_desktop_entry(app_dir, executable_path, icon_path):
    """Create a desktop entry file for the application."""
    print("Creating desktop entry file...")
    
    # Create desktop entry file
    desktop_entry_path = app_dir / f"{APP_NAME.lower()}.desktop"
    
    # Fill in the template
    desktop_entry_content = DESKTOP_ENTRY_TEMPLATE.format(
        executable_path=executable_path,
        icon_path=icon_path
    )
    
    # Write the desktop entry file
    with open(desktop_entry_path, 'w') as f:
        f.write(desktop_entry_content)
    
    # Make it executable
    os.chmod(desktop_entry_path, 0o755)
    
    print(f"Desktop entry created at {desktop_entry_path}")
    return desktop_entry_path

def create_appimage(args):
    """Create an AppImage package."""
    if args.skip_appimage:
        print("Skipping AppImage creation as requested.")
        return
    
    print("Creating AppImage...")
    
    # Check if appimagetool is available
    appimagetool_path = shutil.which("appimagetool")
    if not appimagetool_path:
        print("Error: appimagetool not found. Cannot create AppImage.")
        print("You can install it from: https://github.com/AppImage/AppImageKit/releases")
        return
    
    # Directory where the PyInstaller output is located
    app_dir = Path(args.output_dir) / APP_NAME
    
    # Create AppDir structure
    appdir = Path(args.output_dir) / "AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    appdir.mkdir()
    
    # Copy application files to AppDir
    usr_dir = appdir / "usr"
    bin_dir = usr_dir / "bin"
    share_dir = usr_dir / "share"
    applications_dir = share_dir / "applications"
    icons_dir = share_dir / "icons" / "hicolor" / "256x256" / "apps"
    
    # Create directory structure
    bin_dir.mkdir(parents=True)
    applications_dir.mkdir(parents=True)
    icons_dir.mkdir(parents=True)
    
    # Copy the application
    for item in app_dir.iterdir():
        if item.is_dir():
            shutil.copytree(item, bin_dir / item.name)
        else:
            shutil.copy(item, bin_dir)
    
    # Create shell script launcher
    launcher_path = bin_dir / f"{APP_NAME.lower()}"
    with open(launcher_path, 'w') as f:
        f.write(f"""#!/bin/bash
# Launch the Scout application
cd "$(dirname "$0")"
exec ./{APP_NAME} "$@"
""")
    os.chmod(launcher_path, 0o755)
    
    # Copy icon
    icon_source = Path(ICON_PATH)
    if icon_source.exists():
        shutil.copy(icon_source, icons_dir / f"{APP_NAME.lower()}.png")
    
    # Create desktop entry
    desktop_entry_path = applications_dir / f"{APP_NAME.lower()}.desktop"
    with open(desktop_entry_path, 'w') as f:
        f.write(DESKTOP_ENTRY_TEMPLATE.format(
            executable_path=f"usr/bin/{APP_NAME.lower()}",
            icon_path=APP_NAME.lower()
        ))
    
    # Create AppRun file
    apprun_path = appdir / "AppRun"
    with open(apprun_path, 'w') as f:
        f.write(f"""#!/bin/bash
# AppRun for Scout
cd "$(dirname "$0")"
exec usr/bin/{APP_NAME.lower()} "$@"
""")
    os.chmod(apprun_path, 0o755)
    
    # Create AppImage
    appimage_name = f"{APP_NAME}-{args.version}-x86_64.AppImage"
    appimage_path = Path(args.output_dir) / appimage_name
    
    print("Running appimagetool...")
    cmd = [appimagetool_path, str(appdir), str(appimage_path)]
    result = subprocess.run(cmd, check=False)
    
    if result.returncode != 0:
        print(f"Error: AppImage creation failed with exit code {result.returncode}")
        return False
    
    # Clean up AppDir
    shutil.rmtree(appdir)
    
    print(f"AppImage created successfully: {appimage_path}")
    return True

def create_debian_package(args):
    """Create a Debian package."""
    if args.skip_deb:
        print("Skipping Debian package creation as requested.")
        return
    
    # Check if dpkg-deb is available
    dpkg_deb_path = shutil.which("dpkg-deb") or shutil.which("dpkg")
    if not dpkg_deb_path:
        print("Error: dpkg-deb not found. Cannot create Debian package.")
        return
    
    print("Creating Debian package...")
    
    # Directory where the PyInstaller output is located
    app_dir = Path(args.output_dir) / APP_NAME
    
    # Create temporary directory for package building
    with tempfile.TemporaryDirectory() as temp_dir:
        pkg_root = Path(temp_dir)
        
        # Create package directory structure
        opt_dir = pkg_root / "opt" / APP_NAME.lower()
        bin_dir = pkg_root / "usr" / "bin"
        applications_dir = pkg_root / "usr" / "share" / "applications"
        icons_dir = pkg_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        debian_dir = pkg_root / "DEBIAN"
        
        # Create directories
        opt_dir.mkdir(parents=True)
        bin_dir.mkdir(parents=True)
        applications_dir.mkdir(parents=True)
        icons_dir.mkdir(parents=True)
        debian_dir.mkdir(parents=True)
        
        # Copy application to opt directory
        for item in app_dir.iterdir():
            if item.is_dir():
                shutil.copytree(item, opt_dir / item.name)
            else:
                shutil.copy(item, opt_dir)
        
        # Create launcher script in bin
        launcher_path = bin_dir / APP_NAME.lower()
        with open(launcher_path, 'w') as f:
            f.write(f"""#!/bin/bash
# Launch the Scout application
cd /opt/{APP_NAME.lower()}
exec ./{APP_NAME} "$@"
""")
        os.chmod(launcher_path, 0o755)
        
        # Copy icon
        icon_source = Path(ICON_PATH)
        if icon_source.exists():
            shutil.copy(icon_source, icons_dir / f"{APP_NAME.lower()}.png")
        
        # Create desktop entry
        desktop_entry_path = applications_dir / f"{APP_NAME.lower()}.desktop"
        with open(desktop_entry_path, 'w') as f:
            f.write(DESKTOP_ENTRY_TEMPLATE.format(
                executable_path=f"/usr/bin/{APP_NAME.lower()}",
                icon_path=APP_NAME.lower()
            ))
        
        # Calculate installed size (in KB)
        du_output = subprocess.check_output(['du', '-sk', str(opt_dir)]).decode('utf-8')
        installed_size = du_output.split()[0]
        
        # Determine dependencies
        dependencies = "libc6, python3, libpython3.9, python3-tk, tesseract-ocr"
        
        # Create control file
        control_path = debian_dir / "control"
        with open(control_path, 'w') as f:
            f.write(CONTROL_TEMPLATE.format(
                version=args.version,
                installed_size=installed_size,
                dependencies=dependencies
            ))
        
        # Create package
        deb_name = f"{APP_NAME.lower()}_{args.version}_amd64.deb"
        deb_path = Path(args.output_dir) / deb_name
        
        print("Building Debian package...")
        cmd = [dpkg_deb_path, "--build", str(pkg_root), str(deb_path)]
        result = subprocess.run(cmd, check=False)
        
        if result.returncode != 0:
            print(f"Error: Debian package creation failed with exit code {result.returncode}")
            return False
    
    print(f"Debian package created successfully: {deb_path}")
    return True

def main():
    """Main build script function."""
    args = parse_arguments()
    
    # Check if running on Linux
    check_linux_requirements()
    
    # Prepare environment
    prepare_build_environment()
    
    # Build the application
    build_application(args)
    
    # Copy additional files
    copy_additional_files(args)
    
    # Create AppImage
    create_appimage(args)
    
    # Create Debian package
    create_debian_package(args)
    
    print(f"\n{APP_NAME} v{args.version} Linux builds completed successfully!")
    
    # Print locations of created packages
    if not args.skip_appimage:
        appimage_path = Path(args.output_dir) / f"{APP_NAME}-{args.version}-x86_64.AppImage"
        if appimage_path.exists():
            print(f"AppImage: {appimage_path.absolute()}")
    
    if not args.skip_deb:
        deb_path = Path(args.output_dir) / f"{APP_NAME.lower()}_{args.version}_amd64.deb"
        if deb_path.exists():
            print(f"Debian package: {deb_path.absolute()}")

if __name__ == "__main__":
    main() 