# -*- mode: python ; coding: utf-8 -*-
"""
Scout Application PyInstaller Specification

This spec file provides detailed configuration for building the Scout executable.
It specifies dependencies, data files, and build settings.
"""

import os
import sys
from pathlib import Path

# Configuration
APP_NAME = "Scout"
MAIN_SCRIPT = "main.py"
VERSION = "1.0.0"
ICON_PATH = "resources/icons/scout.ico"

# Determine platform-specific settings
is_windows = sys.platform.startswith('win')
is_mac = sys.platform.startswith('darwin')
is_linux = sys.platform.startswith('linux')

# Find the project root directory (where this spec file is located)
project_root = os.path.abspath(SPECPATH)

# Path to the main script
main_script_path = os.path.join(project_root, MAIN_SCRIPT)

# A list of hidden imports that PyInstaller might miss
hidden_imports = [
    'PyQt6.sip',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'numpy',
    'cv2',
    'pytesseract',
]

# A list of binary dependencies to include
binaries = []

# A list of data files to include
datas = [
    # Include translation files
    (os.path.join(project_root, 'scout', 'translations'), 'scout/translations'),
    # Include resources
    (os.path.join(project_root, 'resources'), 'resources'),
    # Include README and LICENSE
    (os.path.join(project_root, 'README.md'), '.'),
    (os.path.join(project_root, 'LICENSE'), '.'),
]

# A list of runtime hooks
runtime_hooks = []

# A list of modules to exclude
excludes = [
    'tkinter',
    'matplotlib',
    'PySide2',
    'PyQt5',
    'IPython',
    'jupyter',
]

# Configure the Analysis block
a = Analysis(
    [main_script_path],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=runtime_hooks,
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Configure the PYZ block (compressed Python modules)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# Configure the EXE block (executable)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # This creates a folder with the exe and dependencies
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX for compression if available
    console=False,  # Don't show a console window
    icon=ICON_PATH if os.path.exists(os.path.join(project_root, ICON_PATH)) else None,
    version='file_version_info.txt' if is_windows and os.path.exists('file_version_info.txt') else None,
)

# Configure the COLLECT block (collects all files into a directory)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

# If we're on macOS, create an app bundle
if is_mac:
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=ICON_PATH if os.path.exists(os.path.join(project_root, ICON_PATH)) else None,
        bundle_identifier=f'com.scoutapp.{APP_NAME.lower()}',
        info_plist={
            'CFBundleShortVersionString': VERSION,
            'CFBundleVersion': VERSION,
            'NSHighResolutionCapable': True,
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
        },
    ) 