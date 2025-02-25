"""
Update Checker

This module provides functionality to check for Scout application updates
and download newer versions when available.
"""

import os
import sys
import json
import tempfile
import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from urllib.request import urlopen, Request
from urllib.error import URLError

# Set up logging
logger = logging.getLogger(__name__)

# Update configuration
UPDATE_URL = "https://api.scout-app.com/updates"
CURRENT_VERSION = "1.0.0"  # This should match the application version
UPDATE_CHECK_TIMEOUT = 5  # Timeout in seconds for update check requests

class UpdateChecker:
    """
    Checks for application updates and provides methods for downloading
    and installing new versions.
    """
    
    def __init__(self, current_version: str = CURRENT_VERSION, update_url: str = UPDATE_URL):
        """
        Initialize the update checker.
        
        Args:
            current_version: The current application version
            update_url: The URL to check for updates
        """
        self.current_version = current_version
        self.update_url = update_url
        self.latest_version = None
        self.download_url = None
        self.update_info = None
        self.changelog = None
    
    def check_for_updates(self) -> bool:
        """
        Check if updates are available.
        
        Returns:
            True if an update is available, False otherwise
        """
        try:
            # Prepare the request with system information
            system_info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
                "current_version": self.current_version
            }
            
            # Make the request
            headers = {
                "User-Agent": f"Scout/{self.current_version}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            data = json.dumps(system_info).encode('utf-8')
            request = Request(self.update_url, data=data, headers=headers)
            
            # Send the request and parse the response
            with urlopen(request, timeout=UPDATE_CHECK_TIMEOUT) as response:
                update_data = json.loads(response.read().decode('utf-8'))
                
                # Extract update information
                self.latest_version = update_data.get("latest_version")
                self.download_url = update_data.get("download_url")
                self.update_info = update_data.get("update_info")
                self.changelog = update_data.get("changelog")
                
                # Check if update is available
                if self.latest_version and self._compare_versions(self.current_version, self.latest_version) < 0:
                    logger.info(f"Update available: {self.latest_version}")
                    return True
                else:
                    logger.info(f"No update available. Current version: {self.current_version}")
                    return False
        
        except URLError as e:
            logger.error(f"Error checking for updates: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking for updates: {e}")
            return False
    
    def download_update(self, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Download the latest update.
        
        Args:
            output_dir: Directory to save the downloaded file.
                If None, a temporary directory will be used.
        
        Returns:
            Path to the downloaded file if successful, None otherwise
        """
        if not self.download_url:
            logger.error("No download URL available. Check for updates first.")
            return None
        
        try:
            # Create output directory if it doesn't exist
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                file_path = os.path.join(output_dir, f"Scout_Setup_{self.latest_version}.exe")
            else:
                # Use a temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".exe")
                file_path = temp_file.name
                temp_file.close()
            
            logger.info(f"Downloading update from {self.download_url} to {file_path}")
            
            # Download the file
            with urlopen(self.download_url, timeout=60) as response, open(file_path, 'wb') as out_file:
                # Get content length for progress tracking
                content_length = response.getheader('Content-Length')
                total_size = int(content_length) if content_length else None
                downloaded = 0
                
                # Download in chunks
                chunk_size = 8192  # 8KB chunks
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Log progress
                    if total_size:
                        progress = downloaded / total_size * 100
                        logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"Update downloaded successfully to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            return None
    
    def install_update(self, installer_path: str, silent: bool = False) -> bool:
        """
        Install the downloaded update.
        
        Args:
            installer_path: Path to the downloaded installer
            silent: Whether to install silently (no UI)
        
        Returns:
            True if installation was initiated successfully, False otherwise
        """
        if not os.path.exists(installer_path):
            logger.error(f"Installer not found at {installer_path}")
            return False
        
        try:
            # Prepare the installation command
            install_args = [installer_path]
            if silent:
                install_args.append("/S")  # Silent installation
            
            logger.info(f"Starting installer: {' '.join(install_args)}")
            
            # Start the installer process
            if sys.platform == 'win32':
                # On Windows, use CreateProcess to avoid UAC issues
                # The installer may require elevation, so we need to run it detached
                from subprocess import CREATE_NEW_PROCESS_GROUP, DETACHED_PROCESS
                subprocess.Popen(
                    install_args,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    close_fds=True
                )
            else:
                # On other platforms, just use Popen
                subprocess.Popen(install_args)
            
            logger.info("Installer launched successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error installing update: {e}")
            return False
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
        
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad with zeros if necessary
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)
        
        # Compare part by part
        for i in range(len(v1_parts)):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        
        # Versions are equal
        return 0
    
    def get_update_info(self) -> Dict[str, Any]:
        """
        Get information about the latest update.
        
        Returns:
            Dict containing update information
        """
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.latest_version is not None and self._compare_versions(self.current_version, self.latest_version) < 0,
            "download_url": self.download_url,
            "update_info": self.update_info,
            "changelog": self.changelog
        }

# Singleton instance
_update_checker = None

def get_update_checker() -> UpdateChecker:
    """
    Get the singleton update checker instance.
    
    Returns:
        UpdateChecker instance
    """
    global _update_checker
    if _update_checker is None:
        _update_checker = UpdateChecker()
    return _update_checker 