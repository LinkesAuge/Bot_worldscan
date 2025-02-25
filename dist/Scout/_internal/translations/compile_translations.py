"""
Compile Translations Script

This script compiles .ts translation files to .qm format for use in the application.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def find_lrelease():
    """Find lrelease executable in the system."""
    # Try common paths for lrelease
    common_paths = [
        "lrelease",  # If in PATH
        "lrelease6",  # If in PATH (Qt6 specific)
        "lrelease-qt6",  # Debian/Ubuntu naming
        r"C:\Qt\6.5.0\msvc2019_64\bin\lrelease.exe",  # Common Windows path
        r"C:\Qt\Qt6.5.0\6.5.0\msvc2019_64\bin\lrelease.exe",  # Common Windows path
        "/usr/bin/lrelease",  # Common Linux path
        "/usr/bin/lrelease-qt6",  # Common Linux path
        "/usr/local/bin/lrelease",  # Common macOS path
    ]
    
    # Try to find lrelease
    for path in common_paths:
        try:
            # Check if the command is available
            result = subprocess.run([path, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Found lrelease at: {path}")
                return path
        except FileNotFoundError:
            continue
    
    logger.error("Could not find lrelease. Please install Qt Linguist tools.")
    return None

def compile_translation(ts_file: Path, lrelease_path: str) -> bool:
    """
    Compile a .ts file to .qm format.
    
    Args:
        ts_file: Path to .ts file
        lrelease_path: Path to lrelease executable
        
    Returns:
        True if compilation was successful, False otherwise
    """
    if not ts_file.exists():
        logger.error(f"Translation file does not exist: {ts_file}")
        return False
    
    qm_file = ts_file.with_suffix(".qm")
    
    try:
        # Run lrelease
        result = subprocess.run(
            [lrelease_path, str(ts_file), "-qm", str(qm_file)],
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Compiled {ts_file} to {qm_file}")
            return True
        else:
            logger.error(f"Failed to compile {ts_file}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error compiling {ts_file}: {str(e)}")
        return False

def compile_all_translations():
    """Compile all translation files in the translations directory."""
    # Find lrelease executable
    lrelease_path = find_lrelease()
    if not lrelease_path:
        sys.exit(1)
    
    # Get translations directory
    script_dir = Path(__file__).parent
    ts_files = list(script_dir.glob("*.ts"))
    
    if not ts_files:
        logger.warning("No translation files found in the translations directory.")
        return
    
    logger.info(f"Found {len(ts_files)} translation files.")
    
    # Compile each file
    success_count = 0
    for ts_file in ts_files:
        if compile_translation(ts_file, lrelease_path):
            success_count += 1
    
    logger.info(f"Compiled {success_count} of {len(ts_files)} translation files successfully.")

if __name__ == "__main__":
    compile_all_translations() 